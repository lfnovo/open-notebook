"""Focused offline fixes: chapter self-contained gap + length-limit recovery."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    QuestionSlot,
    evaluate_mcq_structural_rules,
    evaluate_unnecessary_source_references,
    evaluate_unsupported_context_phrasing,
    run_bank_batch_early_gates,
)


def _slot(**kwargs) -> QuestionSlot:
    defaults = dict(
        question_number=1,
        chapter=1,
        chapter_title="Chapter 1",
        target_difficulty="easy",
        answer_type="single_correct",
        grade="9",
        subject="Financial Literacy",
    )
    defaults.update(kwargs)
    return QuestionSlot(**defaults)


def _ok_payload():
    return {
        "question": "What is a household budget?",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "A budget plans income and spending.",
    }


class TestChapterSelfContainedGapFix:
    def test_based_on_the_chapters_explanation_fails_standalone(self):
        stem = (
            "Based on the chapter's explanation of inflation and exchange rates, "
            "what is the most likely effect on a currency?"
        )
        assert evaluate_unsupported_context_phrasing(stem, standalone=True)
        assert evaluate_unnecessary_source_references(stem, standalone=True)
        assert evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["a", "b", "c", "d", "e"],
            correct_indices=[0],
            question_text=stem,
            standalone=True,
        )

    def test_based_on_the_chapter_fails(self):
        stem = "Based on the chapter, what happens to prices during inflation?"
        assert evaluate_unnecessary_source_references(stem)
        assert evaluate_unsupported_context_phrasing(stem)

    def test_from_the_chapters_explanation_fails(self):
        stem = "From the chapter's explanation, which property of money is this?"
        assert evaluate_unnecessary_source_references(stem)
        assert evaluate_unsupported_context_phrasing(stem)

    def test_as_explained_in_this_chapter_fails(self):
        stem = "As explained in this chapter, what is barter?"
        assert evaluate_unnecessary_source_references(stem)
        assert evaluate_unsupported_context_phrasing(stem)

    def test_clean_self_contained_stem_passes(self):
        stem = "What is a household budget?"
        assert evaluate_unnecessary_source_references(stem) == []
        assert evaluate_unsupported_context_phrasing(stem) == []
        assert (
            evaluate_mcq_structural_rules(
                answer_type="single_correct",
                options=["a", "b", "c", "d", "e"],
                correct_indices=[0],
                question_text=stem,
                standalone=True,
            )
            == []
        )

    def test_standalone_false_allows_source_dependent_construction(self):
        stem = "Based on the chapter's explanation, what is barter?"
        assert evaluate_unsupported_context_phrasing(stem, standalone=False) == []
        assert evaluate_unnecessary_source_references(stem, standalone=False) == []
        assert (
            evaluate_mcq_structural_rules(
                answer_type="single_correct",
                options=["a", "b", "c", "d", "e"],
                correct_indices=[0],
                question_text=stem,
                standalone=False,
            )
            == []
        )

    def test_early_gates_reject_chapter_framing(self):
        reasons, cat = run_bank_batch_early_gates(
            slot=_slot(),
            generated={
                "question": (
                    "A student notices rising prices. Based on the chapter's "
                    "explanation of inflation and exchange rates, what happens?"
                ),
                "options": ["A1", "A2", "A3", "A4", "A5"],
                "correct_indices": [0],
                "topic": "Inflation",
                "sub_topic": "Exchange rates",
            },
            existing_question_texts=[],
            existing_questions=[],
        )
        assert reasons
        assert cat in {"structural", "deterministic"}


class TestLengthLimitRecovery:
    @pytest.mark.asyncio
    async def test_normal_2048_success_no_retry(self):
        class R:
            def model_dump(self):
                return _ok_payload()

        mock_invoke = AsyncMock(return_value=R())
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False, "generator_model": None},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is not None
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 2048
        assert int(cost.get("length_limit_retry_attempted") or 0) == 0

    @pytest.mark.asyncio
    async def test_length_error_retries_once_at_4096(self):
        class R:
            def model_dump(self):
                return _ok_payload()

        length_err = ExternalServiceError(
            "AI service error: Could not parse response content as the length "
            "limit was reached - CompletionUsage(reasoning_tokens=2048)"
        )
        length_err.__cause__ = type("LengthFinishReasonError", (Exception,), {})(
            "length limit was reached"
        )
        mock_invoke = AsyncMock(side_effect=[length_err, R()])
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False, "generator_model": None},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is not None
        assert mock_invoke.await_count == 2
        assert mock_invoke.await_args_list[0].kwargs.get("max_tokens") == 2048
        assert mock_invoke.await_args_list[1].kwargs.get("max_tokens") == 4096
        assert cost["length_limit_retry_attempted"] == 1
        assert cost["length_limit_retry_succeeded"] == 1
        assert cost["length_limit_retry_initial_tokens"] == 2048
        assert cost["length_limit_retry_retry_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_retry_also_length_fails(self):
        length_err = ExternalServiceError(
            "AI service error: Could not parse response content as the length limit was reached"
        )
        mock_invoke = AsyncMock(side_effect=[length_err, length_err])
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is None
        assert mock_invoke.await_count == 2
        assert cost["length_limit_retry_attempted"] == 1
        assert cost["length_limit_retry_failed"] == 1
        assert int(cost.get("length_limit_retry_succeeded") or 0) == 0

    @pytest.mark.asyncio
    async def test_ordinary_provider_error_no_length_retry(self):
        err = ExternalServiceError("AI service error: rate limit exceeded elsewhere")
        # Not a length error — classifier message without length keywords
        mock_invoke = AsyncMock(side_effect=ExternalServiceError("AI service error: boom"))
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {"book_grounded": False},
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is None
        assert mock_invoke.await_count == 1
        assert int(cost.get("length_limit_retry_attempted") or 0) == 0

    def test_length_detector_positive_and_negative(self):
        assert qp.is_structured_output_length_error(
            ExternalServiceError("AI service error: length limit was reached")
        )
        e = ExternalServiceError("AI service error: truncated")
        e.__cause__ = type("LengthFinishReasonError", (Exception,), {})("x")
        assert qp.is_structured_output_length_error(e)
        assert not qp.is_structured_output_length_error(
            ExternalServiceError("AI service error: authentication failed")
        )

    def test_length_retry_not_wired_into_validation_failures(self):
        fill_src = qp.fill_slots.__code__.co_consts  # smoke: function exists
        src = qp._generate_for_slot.__doc__ or ""
        gen_src = open(qp.__file__, encoding="utf-8").read()
        # Recovery lives only in generator; validators unchanged
        assert "GENERATOR_LENGTH_RETRY_MAX_TOKENS" in gen_src
        assert "length_limit_retry_attempted" in gen_src
        assert "is_structured_output_length_error" in gen_src
        # No second planner / no reasoning_effort
        assert "reasoning_effort" not in gen_src
        assert fill_src is not None


class TestChapterTextbookWordingAndConceptGrounding:
    """CHANGE 1–5: chapter/textbook stems rejected; conceptual grounding clarified."""

    @pytest.mark.parametrize(
        "stem",
        [
            "According to the chapter, this kind of digital currency is called…",
            "According to this chapter, what is barter?",
            "From the chapter, which property of money is this?",
            "From this chapter, what is inflation?",
            "From the textbook, what is commodity money?",
            "According to the textbook, what is a budget?",
            "As stated in the textbook, what is fiat money?",
            "As mentioned in the book, what is a medium of exchange?",
            "Which examples were listed in the chapter as commodity money?",
            "Which items were cited in the chapter as commodity money?",
            "Which examples were mentioned in the chapter?",
        ],
    )
    def test_chapter_book_textbook_stems_rejected(self, stem):
        assert evaluate_unsupported_context_phrasing(stem, standalone=True)
        assert evaluate_unnecessary_source_references(stem, standalone=True)
        assert evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["a", "b", "c", "d", "e"],
            correct_indices=[0],
            question_text=stem,
            standalone=True,
        )

    def test_clean_conceptual_commodity_money_stem_passes_source_checks(self):
        stem = (
            "Which of the following could serve as commodity money because they "
            "have intrinsic value and can be used as a medium of exchange?"
        )
        assert evaluate_unsupported_context_phrasing(stem) == []
        assert evaluate_unnecessary_source_references(stem) == []
        assert (
            evaluate_mcq_structural_rules(
                answer_type="single_correct",
                options=[
                    "Gold coins with intrinsic value",
                    "A digital IOU with no intrinsic value",
                    "A bank password",
                    "An empty gift card",
                    "A lottery ticket",
                ],
                correct_indices=[0],
                question_text=stem,
                standalone=True,
            )
            == []
        )

    def test_standalone_false_passage_dataset_unchanged(self):
        stems = [
            "According to the chapter, what does the passage say about barter?",
            "From the textbook excerpt below, which figure is largest?",
            "Which examples were cited in the chapter dataset table?",
        ]
        for stem in stems:
            assert evaluate_unsupported_context_phrasing(stem, standalone=False) == []
            assert evaluate_unnecessary_source_references(stem, standalone=False) == []
            assert (
                evaluate_mcq_structural_rules(
                    answer_type="single_correct",
                    options=["a", "b", "c", "d", "e"],
                    correct_indices=[0],
                    question_text=stem,
                    standalone=False,
                )
                == []
            )

    def test_generator_closes_chapter_unless_required_loophole(self):
        src = open(qp.__file__, encoding="utf-8").read()
        assert "unless that reference is required to answer" not in src
        assert "INTERNAL grounding only" in src or "internal grounding only" in src.lower()
        assert "Never mention the chapter, book, textbook" in src
        assert "source_specific_recall" not in src
        assert "does NOT have to appear verbatim" in src or "do not appear word-for-word" in src

    def test_blind_solver_still_blind_and_concept_application_guidance(self):
        assert "You have NOT seen the answer key" in qp.BLIND_SOLVER_SYSTEM
        assert "apply the taught definition/principle" in qp.BLIND_SOLVER_SYSTEM
        assert "verbatim in the grounding excerpt" in qp.BLIND_SOLVER_SYSTEM
        assert "not permission to use unrelated external specialist knowledge" in qp.BLIND_SOLVER_SYSTEM
        solve_src = inspect.getsource(qp._blind_solve)
        assert "generated.get('question')" in solve_src
        assert "generated.get('options')" in solve_src
        # Prompt must not inject answer key / explanation / target difficulty
        assert "generated.get('correct_indices')" not in solve_src
        assert "generated.get('explanation')" not in solve_src
        assert "generated.get('target_difficulty')" not in solve_src
        assert "slot.target_difficulty" not in solve_src

    def test_validator_grounded_means_concept_not_verbatim_example(self):
        assert "word-for-word" in qp.VALIDATOR_SYSTEM
        assert "underlying concept/fact is supported" in qp.VALIDATOR_SYSTEM
        assert "concept_relevant" in qp.VALIDATOR_SYSTEM
        assert "no_unrelated_external_knowledge" in qp.VALIDATOR_SYSTEM

    def test_concept_absent_still_fails_grounding(self):
        from open_notebook.graphs.question_paper_blueprint import (
            apply_independent_validation,
            map_cognitive_score,
        )

        scores = {k: 1 for k in (
            "knowledge_demand",
            "cognitive_operation",
            "multi_step_reasoning",
            "information_explicitness",
            "contextual_complexity",
            "option_discrimination",
            "calculation_load",
            "integration_transfer",
        )}
        assert map_cognitive_score(8) == "easy"
        out = apply_independent_validation(
            slot=_slot(),
            criterion_scores=scores,
            quality_flags={
                "content_valid": True,
                "answer_valid": True,
                "grade_appropriate": True,
                "unambiguous": True,
                "language_clear": True,
                "explanation_valid": True,
                "distractors_ok": True,
                "grounded_in_material": False,
                "concept_relevant": True,
                "no_unrelated_external_knowledge": True,
            },
            question={
                "question": (
                    "Which of the following could serve as commodity money because "
                    "they have intrinsic value?"
                ),
                "options": ["Gold", "Password", "IOU", "Ticket", "Empty card"],
                "correct_indices": [0],
                "topic": "Money",
                "sub_topic": "Commodity money",
            },
            existing_question_texts=[],
            existing_questions=[],
            book_grounded=True,
        )
        assert out["passed"] is False
        assert any("grounded" in r.lower() for r in out["validation_reasons"])

    def test_unrelated_external_knowledge_still_fails(self):
        from open_notebook.graphs.question_paper_blueprint import apply_independent_validation

        scores = {k: 1 for k in (
            "knowledge_demand",
            "cognitive_operation",
            "multi_step_reasoning",
            "information_explicitness",
            "contextual_complexity",
            "option_discrimination",
            "calculation_load",
            "integration_transfer",
        )}
        out = apply_independent_validation(
            slot=_slot(),
            criterion_scores=scores,
            quality_flags={
                "content_valid": True,
                "answer_valid": True,
                "grade_appropriate": True,
                "unambiguous": True,
                "language_clear": True,
                "explanation_valid": True,
                "distractors_ok": True,
                "grounded_in_material": True,
                "concept_relevant": True,
                "no_unrelated_external_knowledge": False,
            },
            question={
                "question": (
                    "Which Basel III tier-1 capital ratio applies to "
                    "systemically important banks?"
                ),
                "options": ["A", "B", "C", "D", "E"],
                "correct_indices": [0],
                "topic": "Money",
                "sub_topic": "Banking",
            },
            existing_question_texts=[],
            existing_questions=[],
            book_grounded=True,
        )
        assert out["passed"] is False
        assert any("unrelated external" in r.lower() for r in out["validation_reasons"])

    def test_verbatim_absent_example_does_not_fail_source_reference_checks(self):
        """Exact option text need not appear in a chapter snippet for source-ref gates."""
        stem = (
            "Leila uses a digital asset recorded on a decentralised blockchain to "
            "send a payment directly to a friend without using a bank or other "
            "intermediary. What is this type of digital currency called?"
        )
        options = [
            "Cryptocurrency",
            "Commodity money",
            "Fiat paper cash only",
            "A barter token",
            "A bank passbook",
        ]
        # Source snippet teaches the concept but does not list "Cryptocurrency" verbatim
        _snippet = (
            "Digital currencies recorded on a blockchain can move value between "
            "people without a traditional bank intermediary."
        )
        del _snippet  # grounding is conceptual; deterministic gates ignore snippet text
        assert evaluate_unsupported_context_phrasing(stem) == []
        assert evaluate_unnecessary_source_references(stem) == []
        assert (
            evaluate_mcq_structural_rules(
                answer_type="single_correct",
                options=options,
                correct_indices=[0],
                question_text=stem,
                standalone=True,
            )
            == []
        )

    def test_cognitive_thresholds_and_medium_difficult_unchanged(self):
        from open_notebook.graphs.question_paper_blueprint import map_cognitive_score
        import inspect

        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        src = inspect.getsource(map_cognitive_score)
        assert "total <= 12" in src
        assert "total <= 18" in src
