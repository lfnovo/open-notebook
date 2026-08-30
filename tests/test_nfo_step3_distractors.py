"""NFO Step 3 — option and distractor quality (offline; no live LLM)."""

import inspect
from unittest.mock import patch

import pytest

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    QuestionSlot,
    apply_independent_validation,
    evaluate_blind_solver,
    evaluate_mcq_structural_rules,
    evaluate_obvious_option_quality,
    evaluate_unnecessary_source_references,
    evaluate_unsupported_context_phrasing,
    map_cognitive_score,
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


def _opts():
    return [
        "A spending and income budget plan",
        "A tax that replaces a budget",
        "Bank interest in a budget",
        "A savings budget goal",
        "Job income without a budget",
    ]


def _question(text="What is a household budget?", **overrides):
    q = {
        "question": text,
        "options": _opts(),
        "correct_indices": [0],
        "explanation": "A budget plans income and spending.",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "answer": "A",
    }
    q.update(overrides)
    return q


def _flags(**overrides):
    flags = {
        "content_valid": True,
        "answer_valid": True,
        "grade_appropriate": True,
        "distractors_ok": True,
        "unambiguous": True,
        "language_clear": True,
        "grounded_in_material": True,
        "explanation_valid": True,
        "concept_relevant": True,
        "no_unrelated_external_knowledge": True,
        "stem_self_contained": True,
        "natural_assessment_wording": True,
        "scenario_focused": True,
        "options_independently_assessable": True,
        "option_style_balanced": True,
        "misconception_based_distractors": True,
        "reasons": [],
    }
    flags.update(overrides)
    return flags


def _scores():
    return {
        "knowledge": 2,
        "reasoning": 1,
        "context": 1,
        "application": 1,
        "interpretation": 1,
        "decision_making": 1,
        "concept_integration": 1,
        "distractor_quality": 2,
    }


def _validate(question, flags=None, slot=None, blind=None):
    return apply_independent_validation(
        slot=slot or _slot(),
        criterion_scores=_scores(),
        quality_flags=flags if flags is not None else _flags(),
        question=question,
        existing_question_texts=[],
        book_grounded=True,
        blind_solver=blind,
    )


def _blind(defensible, derived):
    labels = "ABCDE"
    return {
        "independently_derived_indices": list(derived),
        "option_analysis": [
            {"option": labels[i], "defensible": bool(defensible[i]), "reason": ""}
            for i in range(5)
        ],
        "information_sufficient": True,
        "arithmetic_consistent": True,
        "no_unsupported_claims": True,
        "terminology_grounded": True,
    }


class TestNfoStep3DistractorQuality:
    def test_single_plausible_related_distractors_pass(self):
        result = _validate(_question(), blind=_blind([True, False, False, False, False], [0]))
        assert result["passed"] is True

    def test_single_irrelevant_distractor_fails(self):
        q = _question()
        q["options"] = [
            "A spending and income budget plan",
            "A tax that replaces a budget",
            "Bank interest in a budget",
            "A savings budget goal",
            "The temple priest collects free gifts",
        ]
        result = _validate(q)
        assert result["passed"] is False
        assert any("irrelevant" in r for r in result["validation_reasons"])

    def test_single_absurd_distractor_fails(self):
        q = _question()
        q["options"] = _opts()
        q["options"][4] = "Aliens did it for pizza"
        reasons = evaluate_obvious_option_quality(q)
        assert any("absurd" in r for r in reasons)
        result = _validate(q)
        assert result["passed"] is False

    def test_single_second_defensible_answer_fails(self):
        result = _validate(
            _question(),
            blind=_blind([True, True, False, False, False], [0]),
        )
        assert result["passed"] is False
        assert any("multiple defensible" in r for r in result["validation_reasons"])

    def test_single_correct_stands_out_by_length_fails(self):
        q = _question()
        q["options"] = [
            "A spending and income budget plan that uniquely and exhaustively describes every household cash-flow rule, exception, and reporting period in technical detail",
            "A tax on a budget",
            "Bank interest",
            "A savings goal",
            "Job income",
        ]
        reasons = evaluate_obvious_option_quality(q)
        assert any("answer-style clue" in r for r in reasons)
        result = _validate(q)
        assert result["passed"] is False

    def test_single_misconception_based_distractors_pass(self):
        result = _validate(
            _question(),
            flags=_flags(misconception_based_distractors=True),
            blind=_blind([True, False, False, False, False], [0]),
        )
        assert result["passed"] is True

    def test_multiple_exact_two_answer_set_passes(self):
        q = _question(correct_indices=[0, 2])
        result = _validate(
            q,
            slot=_slot(answer_type="multiple_correct"),
            blind=_blind([True, False, True, False, False], [0, 2]),
        )
        assert result["passed"] is True

    def test_multiple_exact_four_answer_set_passes(self):
        q = _question(correct_indices=[0, 1, 2, 3])
        result = _validate(
            q,
            slot=_slot(answer_type="multiple_correct"),
            blind=_blind([True, True, True, True, False], [0, 1, 2, 3]),
        )
        assert result["passed"] is True

    def test_multiple_extra_defensible_not_keyed_fails(self):
        q = _question(correct_indices=[0, 2])
        result = _validate(
            q,
            slot=_slot(answer_type="multiple_correct"),
            blind=_blind([True, False, True, True, False], [0, 2]),
        )
        assert result["passed"] is False
        assert any("defensible option set" in r for r in result["validation_reasons"])

    def test_multiple_option_reveals_another_fails(self):
        q = _question(correct_indices=[0, 1])
        q["options"] = _opts()
        q["options"][1] = "This follows from A being correct"
        result = _validate(q, slot=_slot(answer_type="multiple_correct"))
        assert result["passed"] is False
        assert any("independently assessable" in r for r in result["validation_reasons"])

    def test_numerical_plausible_error_distractors_pass(self):
        q = _question(
            "If simple interest on $100 at 10% for 1 year is needed, which amount is interest?"
        )
        q["options"] = [
            "$10 interest from 100 times 0.10",
            "$110 interest from adding the rate twice",
            "$1 interest from using 1% by mistake",
            "$20 interest from using two years",
            "$90 interest from subtracting the rate",
        ]
        result = _validate(q, blind=_blind([True, False, False, False, False], [0]))
        assert result["passed"] is True

    def test_numerical_unrelated_numbers_fail_via_quality_flag(self):
        q = _question(
            "If simple interest on $100 at 10% for 1 year is needed, which amount is interest?"
        )
        result = _validate(
            q, flags=_flags(misconception_based_distractors=False, distractors_ok=False)
        )
        assert result["passed"] is False
        assert any(
            "weak misconception" in r or "distractor" in r for r in result["validation_reasons"]
        )

    def test_strong_option_symmetry_passes(self):
        result = _validate(_question(), blind=_blind([True, False, False, False, False], [0]))
        assert result["passed"] is True
        assert evaluate_obvious_option_quality(_question()) == []

    def test_answer_revealing_style_flag_fails(self):
        result = _validate(_question(), flags=_flags(option_style_balanced=False))
        assert result["passed"] is False
        assert any("answer-style clue" in r for r in result["validation_reasons"])

    def test_blind_solver_exact_answer_set_unchanged(self):
        ok = evaluate_blind_solver(
            _blind([True, False, False, False, False], [0]),
            [0],
            "single_correct",
        )
        assert ok == []
        multi_ok = evaluate_blind_solver(
            _blind([True, False, True, False, False], [0, 2]),
            [0, 2],
            "multiple_correct",
        )
        assert multi_ok == []
        extra = evaluate_blind_solver(
            _blind([True, False, True, True, False], [0, 2]),
            [0, 2],
            "multiple_correct",
        )
        assert any("defensible option set" in e for e in extra)
        src = inspect.getsource(evaluate_blind_solver)
        assert "solver_indices != gen_indices" in src

    def test_step1_and_step2_rules_untouched(self):
        assert evaluate_mcq_structural_rules(
            answer_type="single_correct",
            options=["Cash", "Credit", "Barter", "Loan", "Tax"],
            correct_indices=[0],
            question_text="What is cash?",
        ) == []
        assert evaluate_unsupported_context_phrasing("According to the book, what is cash?")
        assert evaluate_unnecessary_source_references("In this chapter, what is cash?")
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5

    def test_no_new_llm_validator_and_no_answer_position_logic(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "NFO_OPTION_DISTRACTOR_RULES" in gen_src
        assert "shuffle" not in gen_src.lower()
        assert "Do not shuffle or balance answer letters" in qp.NFO_OPTION_DISTRACTOR_RULES
        assert "class DistractorValidatorOutput" not in inspect.getsource(qp)
        assert "slot.target_difficulty" not in inspect.getsource(qp._blind_solve)

    def test_early_gates_catch_obvious_style_clue(self):
        q = _question()
        q["options"] = [
            "A spending and income budget plan that uniquely and exhaustively describes every household cash-flow rule, exception, and reporting period in technical detail",
            "A tax on a budget",
            "Bank interest",
            "A savings goal",
            "Job income",
        ]
        reasons, cat = run_bank_batch_early_gates(
            slot=_slot(),
            generated=q,
            existing_question_texts=[],
            existing_questions=[],
        )
        assert cat == "deterministic"
        assert any("answer-style clue" in r for r in reasons)

    @pytest.mark.asyncio
    async def test_generator_receives_option_quality_rules(self):
        captured = {}

        async def fake_invoke(system, user_prompt, *args, **kwargs):
            captured["system"] = system

            class R:
                def model_dump(self):
                    return {
                        "question": "What is a household budget?",
                        "topic": "Budgeting",
                        "sub_topic": "Household budget",
                        "options": _opts(),
                        "correct_indices": [0],
                        "answer": "A",
                        "explanation": "A budget plans income and spending.",
                    }

            return R()

        with patch.object(qp, "_invoke_structured", side_effect=fake_invoke):
            await qp._generate_for_slot(
                _slot(),
                {
                    "bank_batch_mode": True,
                    "book_grounded": True,
                    "language": "en",
                    "book_id": "question_book:o0chwk6eqt9rjcwmluas",
                },
                "A budget is a plan for income and spending.",
                None,
            )
        assert "OPTION AND DISTRACTOR QUALITY" in captured["system"]
        assert "concept → likely student misconception" in captured["system"]
        assert "BANK BATCH DISTRACTOR" in captured["system"]
        assert "OPTION AND DISTRACTOR QUALITY" not in qp.GENERATOR_SYSTEM
