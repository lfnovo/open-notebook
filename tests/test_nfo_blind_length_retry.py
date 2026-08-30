"""Bank Batch Blind validator length recovery.

Offline only. Does not change Blind independence, Cognitive scoring, thresholds,
acceptance of a real Blind result, grounding, or Final Paper.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    FAILURE_FAMILY_COGNITIVE,
    FAILURE_FAMILY_GRADE,
    FAILURE_FAMILY_GROUNDING,
    classify_academic_failure_family,
)
from open_notebook.graphs.question_paper_blueprint import (
    COGNITIVE_CRITERIA,
    VALIDATOR_UNAVAILABLE_KEY,
    QuestionSlot,
    apply_independent_validation,
    empty_bank_cost_diagnostics,
    evaluate_blind_solver,
)


def _slot(**kwargs) -> QuestionSlot:
    defaults = dict(
        question_number=1,
        chapter=1,
        chapter_title="Chapter 1",
        target_difficulty="medium",
        answer_type="single_correct",
        grade="10",
        subject="Financial Literacy",
    )
    defaults.update(kwargs)
    return QuestionSlot(**defaults)


def _generated() -> dict:
    return {
        "question": "What is a household budget?",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "",
    }


def _length_err() -> ExternalServiceError:
    err = ExternalServiceError(
        "AI service error: Could not parse response content as the length "
        "limit was reached - CompletionUsage(reasoning_tokens=2048)"
    )
    err.__cause__ = type("LengthFinishReasonError", (Exception,), {})(
        "length limit was reached"
    )
    return err


def _timeout_err() -> ExternalServiceError:
    return ExternalServiceError("llm_timeout: blind exceeded 180s after 180000ms")


def _blind_ok() -> qp.BlindSolverOutput:
    return qp.BlindSolverOutput(
        independently_derived_indices=[0],
        option_analysis=[
            qp.OptionDefensibility(option="A", defensible=True),
            qp.OptionDefensibility(option="B", defensible=False),
            qp.OptionDefensibility(option="C", defensible=False),
            qp.OptionDefensibility(option="D", defensible=False),
            qp.OptionDefensibility(option="E", defensible=False),
        ],
        information_sufficient=True,
        arithmetic_consistent=True,
        no_unsupported_claims=True,
        terminology_grounded=True,
    )


def _medium_scores():
    return {k: 2 for k in COGNITIVE_CRITERIA}


def _good_flags():
    return {
        "content_valid": True,
        "answer_valid": True,
        "grade_appropriate": True,
        "distractors_ok": True,
        "unambiguous": True,
        "language_clear": True,
        "grounded_in_material": True,
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


def _solver_payload() -> dict:
    return _blind_ok().model_dump()


class TestBlindLengthRetryBankBatch:
    def _state(self, bank_batch: bool = True):
        return {
            "bank_batch_mode": bank_batch,
            "book_grounded": True,
            "generator_model": None,
            "reviewer_model": None,
        }

    @pytest.mark.asyncio
    async def test_length_retries_once_at_4096_and_uses_real_result(self):
        mock_invoke = AsyncMock(side_effect=[_length_err(), _blind_ok()])
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            result = await qp._blind_solve(
                _slot(),
                _generated(),
                self._state(True),
                "chapter excerpt about budgets",
                cost_diagnostics=cost,
            )
        assert isinstance(result, qp.BlindSolverOutput)
        assert result.independently_derived_indices == [0]
        assert mock_invoke.await_count == 2
        assert mock_invoke.await_args_list[0].kwargs.get("max_tokens") == 2048
        assert mock_invoke.await_args_list[1].kwargs.get("max_tokens") == 4096
        assert int(cost.get("blind_length_retry_attempted") or 0) == 1
        assert int(cost.get("blind_length_retry_success") or 0) == 1
        assert int(cost.get("blind_length_retry_failed") or 0) == 0
        assert int(cost.get("blind_success_count") or 0) == 1
        assert int(cost.get("blind_length_failures") or 0) == 1

    @pytest.mark.asyncio
    async def test_retry_failure_is_unavailable_not_none(self):
        mock_invoke = AsyncMock(side_effect=[_length_err(), _length_err()])
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            result = await qp._blind_solve(
                _slot(),
                _generated(),
                self._state(True),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert isinstance(result, qp.BlindSolverUnavailable)
        assert result is not None
        assert "validator_unavailable" in result.reason
        assert "blind solver" in result.reason.lower()
        assert "length limit" in result.reason.lower()
        assert mock_invoke.await_count == 2
        assert int(cost.get("blind_length_retry_attempted") or 0) == 1
        assert int(cost.get("blind_length_retry_success") or 0) == 0
        assert int(cost.get("blind_length_retry_failed") or 0) == 1

    @pytest.mark.asyncio
    async def test_non_length_error_does_not_retry(self):
        mock_invoke = AsyncMock(side_effect=RuntimeError("provider down"))
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            result = await qp._blind_solve(
                _slot(),
                _generated(),
                self._state(True),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert result is None
        assert mock_invoke.await_count == 1
        assert int(cost.get("blind_length_retry_attempted") or 0) == 0

    @pytest.mark.asyncio
    async def test_timeout_does_not_retry(self):
        mock_invoke = AsyncMock(side_effect=_timeout_err())
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            result = await qp._blind_solve(
                _slot(),
                _generated(),
                self._state(True),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert result is None
        assert mock_invoke.await_count == 1
        assert int(cost.get("blind_length_retry_attempted") or 0) == 0

    @pytest.mark.asyncio
    async def test_first_success_does_not_retry(self):
        mock_invoke = AsyncMock(return_value=_blind_ok())
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            result = await qp._blind_solve(
                _slot(),
                _generated(),
                self._state(True),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert isinstance(result, qp.BlindSolverOutput)
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 2048
        assert int(cost.get("blind_length_retry_attempted") or 0) == 0


class TestFinalPaperBlindUnchanged:
    @pytest.mark.asyncio
    async def test_length_error_does_not_retry_and_returns_none(self):
        mock_invoke = AsyncMock(side_effect=_length_err())
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            result = await qp._blind_solve(
                _slot(),
                {**_generated(), "explanation": "A budget plans income and spending."},
                {
                    "bank_batch_mode": False,
                    "book_grounded": True,
                    "generator_model": None,
                    "reviewer_model": None,
                },
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert result is None
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 2048
        assert int(cost.get("blind_length_retry_attempted") or 0) == 0


class TestBlindUnavailableFailClosed:
    @pytest.mark.asyncio
    async def test_slot_validation_does_not_silently_skip_blind(self):
        unavailable = qp.BlindSolverUnavailable(
            "validator_unavailable: blind solver length limit was reached"
        )

        async def fake_blind(*_a, **_k):
            return unavailable

        async def fake_cog(*_a, **_k):
            return _medium_scores(), _good_flags()

        with patch.object(qp, "_blind_solve", side_effect=fake_blind), patch.object(
            qp, "_validate_cognitive_quality", side_effect=fake_cog
        ):
            result = await qp._validate_slot_independently(
                _slot(),
                _generated(),
                {
                    "bank_batch_mode": True,
                    "book_grounded": True,
                },
                "chapter excerpt about budgets and money",
                [],
            )
        assert result["passed"] is False
        reasons = " | ".join(result["validation_reasons"]).lower()
        assert "validator_unavailable" in reasons
        assert "blind solver" in reasons
        assert "not appropriate for the selected grade" not in reasons
        assert "not grounded in the supplied chapter content" not in reasons
        assert "cognitive difficulty mismatch" not in reasons
        assert result["difficulty_score"] is None

    def test_unavailable_is_not_academic_family(self):
        reasons = [
            "validator_unavailable: blind solver length limit was reached"
        ]
        family = classify_academic_failure_family(reasons)
        assert family is None
        assert family != FAILURE_FAMILY_GROUNDING
        assert family != FAILURE_FAMILY_GRADE
        assert family != FAILURE_FAMILY_COGNITIVE

    def test_apply_validation_fail_closed_without_fake_grade_or_grounding(self):
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=_medium_scores(),
            quality_flags={
                VALIDATOR_UNAVAILABLE_KEY: True,
                "reasons": [
                    "validator_unavailable: blind solver length limit was reached"
                ],
            },
            question=_generated(),
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=None,
            require_explanation_valid=False,
        )
        assert result["passed"] is False
        reasons = " | ".join(result["validation_reasons"]).lower()
        assert "validator_unavailable" in reasons
        assert "not appropriate for the selected grade" not in reasons
        assert "not grounded in the supplied chapter content" not in reasons
        assert "cognitive difficulty mismatch" not in reasons
        assert result["difficulty_score"] is None


class TestIndependenceAndGatesUnchanged:
    def test_evaluate_blind_solver_none_still_fail_open(self):
        assert evaluate_blind_solver(None, [0], "single_correct") == []

    def test_real_blind_result_still_gates(self):
        assert evaluate_blind_solver(_solver_payload(), [0], "single_correct") == []
        errors = evaluate_blind_solver(
            {**_solver_payload(), "independently_derived_indices": [1]},
            [0],
            "single_correct",
        )
        assert any("independent solver disagrees" in e for e in errors)

    def test_blind_still_answer_key_blind_and_starts_at_2048(self):
        src = inspect.getsource(qp._blind_solve)
        assert "_invoke_blind(max_tokens=2048)" in src
        assert "BLIND_LENGTH_RETRY_MAX_TOKENS" in src
        assert "answer key" in qp.BLIND_SOLVER_SYSTEM
        assert "correct_indices" not in qp.BLIND_SOLVER_SYSTEM
        gather = inspect.getsource(qp._validate_slot_independently)
        assert "asyncio.gather" in gather
        assert gather.count("_blind_solve") == 1
        assert "_validate_cognitive_quality" in gather
        assert "BlindSolverUnavailable" in gather

    def test_cognitive_retry_untouched(self):
        src = inspect.getsource(qp._validate_cognitive_quality)
        assert "COGNITIVE_MAX_TOKENS" in src
        assert "COGNITIVE_LENGTH_RETRY_MAX_TOKENS" in src
        assert "blind_length_retry" not in src
        assert qp.COGNITIVE_MAX_TOKENS == 2048
        assert qp.BLIND_MAX_TOKENS == 2048
        assert qp.BLIND_LENGTH_RETRY_MAX_TOKENS == 4096

    def test_diagnostics_shape(self):
        d = empty_bank_cost_diagnostics()
        assert d["blind_length_retry_attempted"] == 0
        assert d["blind_length_retry_success"] == 0
        assert d["blind_length_retry_failed"] == 0
        assert d["blind_length_failures"] == 0
