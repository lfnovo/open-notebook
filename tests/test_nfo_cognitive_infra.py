"""Cognitive validator infrastructure handling.

Offline only. Does not change difficulty bands, quality flags, or acceptance
when a real Cognitive result is present. Does not generate questions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    FAILURE_FAMILY_GRADE,
    classify_academic_failure_family,
)
from open_notebook.graphs.question_paper_blueprint import (
    COGNITIVE_CRITERIA,
    VALIDATOR_UNAVAILABLE_KEY,
    QuestionSlot,
    apply_independent_validation,
    map_cognitive_score,
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


def _question():
    return {
        "question": "What is a household budget?",
        "options": ["A", "B", "C", "D", "E"],
        "correct_indices": [0],
        "answer": "A",
        "explanation": "",
        "topic": "Budgeting",
        "sub_topic": "Household budget",
    }


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


def _good_solver():
    return {
        "independently_derived_indices": [0],
        "option_analysis": [
            {"option": "A", "defensible": True, "reason": ""},
            {"option": "B", "defensible": False, "reason": ""},
            {"option": "C", "defensible": False, "reason": ""},
            {"option": "D", "defensible": False, "reason": ""},
            {"option": "E", "defensible": False, "reason": ""},
        ],
        "information_sufficient": True,
        "arithmetic_consistent": True,
        "no_unsupported_claims": True,
        "terminology_grounded": True,
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


def _cog_dump():
    flags = _good_flags()
    flags["criterion_scores"] = _medium_scores()
    flags.pop("explanation_valid", None)
    return flags


class _CogResult:
    def model_dump(self):
        return _cog_dump()


class TestDifficultyBandsUnchanged:
    def test_easy_medium_difficult_bounds(self):
        assert map_cognitive_score(8) == "easy"
        assert map_cognitive_score(12) == "easy"
        assert map_cognitive_score(13) == "medium"
        assert map_cognitive_score(18) == "medium"
        assert map_cognitive_score(19) == "difficult"
        assert map_cognitive_score(24) == "difficult"


class TestApplyIndependentValidationInfra:
    def test_unavailable_is_fail_closed_without_fake_grade_or_grounding(self):
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores={},
            quality_flags={
                VALIDATOR_UNAVAILABLE_KEY: True,
                "reasons": [
                    "validator_unavailable: cognitive validator length limit was reached"
                ],
            },
            question=_question(),
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=_good_solver(),
            require_explanation_valid=False,
        )
        assert result["passed"] is False
        reasons = " | ".join(result["validation_reasons"]).lower()
        assert "validator_unavailable" in reasons
        assert "length limit" in reasons
        assert "not appropriate for the selected grade" not in reasons
        assert "not grounded in the supplied chapter content" not in reasons
        assert "cognitive difficulty mismatch" not in reasons
        assert "content validity failed" not in reasons
        assert result["difficulty_score"] is None
        assert result["validated_cognitive_difficulty"] is None
        assert result["difficulty_scores"] == {}

    def test_unavailable_does_not_accept_even_when_blind_passes(self):
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=_medium_scores(),
            quality_flags={
                VALIDATOR_UNAVAILABLE_KEY: True,
                "reasons": [
                    "validator_unavailable: cognitive validator length limit was reached"
                ],
            },
            question=_question(),
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=_good_solver(),
            require_explanation_valid=False,
        )
        assert result["passed"] is False

    def test_real_quality_flags_still_reject(self):
        flags = _good_flags()
        flags["grade_appropriate"] = False
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=_medium_scores(),
            quality_flags=flags,
            question=_question(),
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=_good_solver(),
            require_explanation_valid=False,
        )
        assert result["passed"] is False
        assert any(
            "not appropriate for the selected grade" in r
            for r in result["validation_reasons"]
        )
        assert result["difficulty_score"] == 16
        assert result["validated_cognitive_difficulty"] == "medium"

    def test_real_medium_pass_unchanged(self):
        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=_medium_scores(),
            quality_flags=_good_flags(),
            question=_question(),
            existing_question_texts=[],
            book_grounded=False,
            blind_solver=_good_solver(),
            require_explanation_valid=False,
        )
        assert result["passed"] is True
        assert result["difficulty_score"] == 16
        assert result["validated_cognitive_difficulty"] == "medium"


class TestIntentRetirementSkipsInfra:
    def test_unavailable_is_not_an_academic_family(self):
        assert (
            classify_academic_failure_family(
                [
                    "validator_unavailable: cognitive validator length limit was reached"
                ]
            )
            is None
        )

    def test_real_grade_family_unchanged(self):
        assert (
            classify_academic_failure_family(
                ["not appropriate for the selected grade"]
            )
            == FAILURE_FAMILY_GRADE
        )


class TestCognitiveLengthRetry:
    def _state(self):
        return {
            "bank_batch_mode": True,
            "book_grounded": True,
            "generator_model": None,
            "reviewer_model": None,
        }

    @pytest.mark.asyncio
    async def test_length_failure_retries_once_at_4096_and_can_succeed(self):
        mock_invoke = AsyncMock(side_effect=[_length_err(), _CogResult()])
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            scores, flags = await qp._validate_cognitive_quality(
                _slot(),
                _question(),
                self._state(),
                "chapter excerpt about budgets and money",
                cost_diagnostics=cost,
            )
        assert mock_invoke.await_count == 2
        assert mock_invoke.await_args_list[0].kwargs.get("max_tokens") == 2048
        assert mock_invoke.await_args_list[1].kwargs.get("max_tokens") == 4096
        assert sum(int(scores[k]) for k in COGNITIVE_CRITERIA) == 16
        assert not flags.get(VALIDATOR_UNAVAILABLE_KEY)
        assert int(cost.get("cognitive_length_retry_attempted") or 0) == 1
        assert int(cost.get("cognitive_length_retry_succeeded") or 0) == 1
        assert int(cost.get("cognitive_length_retry_failed") or 0) == 0

    @pytest.mark.asyncio
    async def test_length_retry_exhausted_is_unavailable_not_fake_easy(self):
        mock_invoke = AsyncMock(side_effect=[_length_err(), _length_err()])
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            scores, flags = await qp._validate_cognitive_quality(
                _slot(),
                _question(),
                self._state(),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert mock_invoke.await_count == 2
        assert scores == {}
        assert flags.get(VALIDATOR_UNAVAILABLE_KEY) is True
        assert "grade_appropriate" not in flags
        assert "grounded_in_material" not in flags
        blob = " ".join(str(r) for r in (flags.get("reasons") or [])).lower()
        assert "validator_unavailable" in blob
        assert "length limit" in blob
        assert int(cost.get("cognitive_length_retry_attempted") or 0) == 1
        assert int(cost.get("cognitive_length_retry_failed") or 0) == 1
        assert int(cost.get("cognitive_length_retry_succeeded") or 0) == 0

        result = apply_independent_validation(
            slot=_slot(),
            criterion_scores=scores,
            quality_flags=flags,
            question=_question(),
            existing_question_texts=[],
            book_grounded=True,
            blind_solver=_good_solver(),
            require_explanation_valid=False,
        )
        assert result["passed"] is False
        reasons = " | ".join(result["validation_reasons"]).lower()
        assert "not appropriate for the selected grade" not in reasons
        assert "cognitive difficulty mismatch" not in reasons
        assert result["difficulty_score"] is None

    @pytest.mark.asyncio
    async def test_non_length_error_does_not_retry(self):
        mock_invoke = AsyncMock(side_effect=RuntimeError("provider timeout"))
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            scores, flags = await qp._validate_cognitive_quality(
                _slot(),
                _question(),
                self._state(),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert mock_invoke.await_count == 1
        assert scores == {}
        assert flags.get(VALIDATOR_UNAVAILABLE_KEY) is True
        assert int(cost.get("cognitive_length_retry_attempted") or 0) == 0
        blob = " ".join(str(r) for r in (flags.get("reasons") or [])).lower()
        assert "validator_unavailable" in blob
        assert "provider timeout" in blob

    @pytest.mark.asyncio
    async def test_final_paper_length_error_does_not_retry(self):
        mock_invoke = AsyncMock(side_effect=_length_err())
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            scores, flags = await qp._validate_cognitive_quality(
                _slot(),
                {**_question(), "explanation": "A budget plans income and spending."},
                {
                    "bank_batch_mode": False,
                    "book_grounded": True,
                    "generator_model": None,
                    "reviewer_model": None,
                },
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 2048
        assert int(cost.get("cognitive_length_retry_attempted") or 0) == 0
        assert scores == {}
        assert flags.get(VALIDATOR_UNAVAILABLE_KEY) is True

    @pytest.mark.asyncio
    async def test_success_on_first_call_does_not_retry(self):
        mock_invoke = AsyncMock(return_value=_CogResult())
        cost = {}
        with patch.object(qp, "_invoke_structured", mock_invoke):
            scores, flags = await qp._validate_cognitive_quality(
                _slot(),
                _question(),
                self._state(),
                "chapter excerpt",
                cost_diagnostics=cost,
            )
        assert mock_invoke.await_count == 1
        assert mock_invoke.await_args.kwargs.get("max_tokens") == 2048
        assert int(cost.get("cognitive_length_retry_attempted") or 0) == 0
        assert not flags.get(VALIDATOR_UNAVAILABLE_KEY)
        assert sum(int(scores[k]) for k in COGNITIVE_CRITERIA) == 16
