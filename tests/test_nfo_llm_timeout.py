"""Bank Batch LLM request timeout protection.

Offline only. Does not change validators, thresholds, prompts, or Final Paper
acceptance. Does not generate questions.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_bank_intent import (
    FAILURE_FAMILY_COGNITIVE,
    FAILURE_FAMILY_GRADE,
    FAILURE_FAMILY_GROUNDING,
    classify_academic_failure_family,
)
from open_notebook.graphs.question_paper_blueprint import (
    BANK_BATCH_LLM_TIMEOUT_DEFAULT_SECONDS,
    BANK_BATCH_LLM_TIMEOUT_ENV,
    COGNITIVE_CRITERIA,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    VALIDATOR_UNAVAILABLE_KEY,
    QuestionSlot,
    bank_batch_llm_timeout_seconds,
    empty_bank_cost_diagnostics,
    is_llm_timeout_error,
    map_bank_batch_timeout_stage,
    record_llm_timeout,
)


class _TinyOut(BaseModel):
    value: str = "ok"


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


def _timeout_err(stage: str = "generation") -> ExternalServiceError:
    return ExternalServiceError(
        f"llm_timeout: {stage} exceeded 180s after 180050ms"
    )


def _slow_model(sleep_s: float):
    class _Structured:
        async def ainvoke(self, messages, config=None):
            await asyncio.sleep(sleep_s)
            return _TinyOut()

    class _Model:
        model_name = "mock-timeout"

        def with_structured_output(self, schema, include_raw=True):
            return _Structured()

    return _Model()


class TestTimeoutConfig:
    def test_default_is_180_seconds(self, monkeypatch):
        monkeypatch.delenv(BANK_BATCH_LLM_TIMEOUT_ENV, raising=False)
        assert bank_batch_llm_timeout_seconds() == BANK_BATCH_LLM_TIMEOUT_DEFAULT_SECONDS
        assert BANK_BATCH_LLM_TIMEOUT_DEFAULT_SECONDS == 180.0

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "90")
        assert bank_batch_llm_timeout_seconds() == 90.0

    def test_zero_disables(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "0")
        assert bank_batch_llm_timeout_seconds() is None

    def test_invalid_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "not-a-number")
        assert bank_batch_llm_timeout_seconds() == BANK_BATCH_LLM_TIMEOUT_DEFAULT_SECONDS


class TestTimeoutStageMapping:
    def test_four_buckets(self):
        assert map_bank_batch_timeout_stage("core_generation") == "generation"
        assert map_bank_batch_timeout_stage("length_recovery_generation") == "generation"
        assert map_bank_batch_timeout_stage("intent_planner_catalog") == "generation"
        assert map_bank_batch_timeout_stage("blind_solver") == "blind"
        assert map_bank_batch_timeout_stage("cognitive_quality") == "cognitive"
        assert map_bank_batch_timeout_stage("explanation_generate") == "explanation"
        assert map_bank_batch_timeout_stage("explanation_validate") == "explanation"


class TestTimeoutDiagnostics:
    def test_empty_diagnostics_include_timeout_fields(self):
        d = empty_bank_cost_diagnostics()
        assert d["llm_timeout_count"] == 0
        assert d["timeout_stage"] is None
        assert d["llm_timeout_duration_ms"] is None
        assert d["llm_timeout_events"] == []

    def test_record_count_stage_and_duration(self):
        d = empty_bank_cost_diagnostics()
        record_llm_timeout(
            d, stage="blind", duration_ms=180123.4, limit_seconds=180
        )
        assert d["llm_timeout_count"] == 1
        assert d["timeout_stage"] == "blind"
        assert d["llm_timeout_duration_ms"] == 180123.4
        assert d["llm_timeout_events"][0]["stage"] == "blind"
        assert d["llm_timeout_events"][0]["duration_ms"] == 180123.4
        assert d["llm_timeout_events"][0]["limit_seconds"] == 180.0
        record_llm_timeout(d, stage="cognitive_quality", duration_ms=5000)
        assert d["llm_timeout_count"] == 2
        assert d["timeout_stage"] == "cognitive"


class TestTimeoutIsInfrastructureNotAcademic:
    def test_llm_timeout_is_not_length_error(self):
        err = _timeout_err("cognitive")
        assert is_llm_timeout_error(err) is True
        assert qp.is_structured_output_length_error(err) is False

    def test_classify_family_none_for_timeout(self):
        assert (
            classify_academic_failure_family(
                ["llm_timeout: generation exceeded 180s after 180000ms"]
            )
            is None
        )
        assert (
            classify_academic_failure_family(
                [
                    "validator_unavailable: cognitive validator error: "
                    "llm_timeout: cognitive exceeded 180s after 180000ms"
                ]
            )
            is None
        )
        assert (
            classify_academic_failure_family(
                ["Generation failed; rewrite a complete MCQ with five options A–E."]
            )
            is None
        )

    def test_timeout_is_not_grounding_cognitive_or_grade(self):
        reasons = ["llm_timeout: generation exceeded 180s after 180000ms"]
        family = classify_academic_failure_family(reasons)
        assert family is None
        assert family != FAILURE_FAMILY_GROUNDING
        assert family != FAILURE_FAMILY_COGNITIVE
        assert family != FAILURE_FAMILY_GRADE


class TestInvokeStructuredTimeout:
    @pytest.mark.asyncio
    async def test_bank_batch_wait_for_raises_infra_timeout(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "0.05")
        cost = empty_bank_cost_diagnostics()
        t0 = time.perf_counter()
        with patch.object(
            qp, "provision_langchain_model", AsyncMock(return_value=_slow_model(10.0))
        ):
            with pytest.raises(ExternalServiceError) as ei:
                await qp._invoke_structured(
                    "sys",
                    "user",
                    None,
                    _TinyOut,
                    llm_stage="core_generation",
                    cost_diagnostics=cost,
                    bank_batch_mode=True,
                )
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0
        assert "llm_timeout" in str(ei.value).lower()
        assert "generation" in str(ei.value).lower()
        assert cost["llm_timeout_count"] == 1
        assert cost["timeout_stage"] == "generation"
        assert cost["llm_timeout_duration_ms"] is not None
        assert cost["llm_timeout_duration_ms"] >= 20.0
        assert cost["llm_timeout_events"][0]["stage"] == "generation"

    @pytest.mark.asyncio
    async def test_final_paper_does_not_apply_timeout(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "0.05")
        with patch.object(
            qp, "provision_langchain_model", AsyncMock(return_value=_slow_model(0.2))
        ):
            result = await qp._invoke_structured(
                "sys",
                "user",
                None,
                _TinyOut,
                llm_stage="core_generation",
                cost_diagnostics=empty_bank_cost_diagnostics(),
                bank_batch_mode=False,
            )
        assert result.value == "ok"

    @pytest.mark.asyncio
    async def test_env_zero_disables_even_in_bank_batch(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "0")
        with patch.object(
            qp, "provision_langchain_model", AsyncMock(return_value=_slow_model(0.15))
        ):
            result = await qp._invoke_structured(
                "sys",
                "user",
                None,
                _TinyOut,
                llm_stage="blind_solver",
                cost_diagnostics=empty_bank_cost_diagnostics(),
                bank_batch_mode=True,
            )
        assert result.value == "ok"

    @pytest.mark.asyncio
    async def test_timeout_stage_blind_cognitive_explanation(self, monkeypatch):
        monkeypatch.setenv(BANK_BATCH_LLM_TIMEOUT_ENV, "0.05")
        for llm_stage, bucket in (
            ("blind_solver", "blind"),
            ("cognitive_quality", "cognitive"),
            ("explanation_generate", "explanation"),
        ):
            cost = empty_bank_cost_diagnostics()
            with patch.object(
                qp, "provision_langchain_model", AsyncMock(return_value=_slow_model(10.0))
            ):
                with pytest.raises(ExternalServiceError) as ei:
                    await qp._invoke_structured(
                        "sys",
                        "user",
                        None,
                        _TinyOut,
                        llm_stage=llm_stage,
                        cost_diagnostics=cost,
                        bank_batch_mode=True,
                    )
            assert bucket in str(ei.value)
            assert cost["timeout_stage"] == bucket
            assert cost["llm_timeout_count"] == 1


class TestTimeoutDoesNotAddRetries:
    @pytest.mark.asyncio
    async def test_generation_timeout_does_not_retry(self):
        mock_invoke = AsyncMock(side_effect=_timeout_err("generation"))
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            out = await qp._generate_for_slot(
                _slot(),
                {
                    "book_grounded": False,
                    "generator_model": None,
                    "bank_batch_mode": True,
                },
                "",
                None,
                cost_diagnostics=cost,
            )
        assert out is None
        assert mock_invoke.await_count == 1
        assert int(cost.get("length_limit_retry_attempted") or 0) == 0

    @pytest.mark.asyncio
    async def test_cognitive_timeout_does_not_retry_4096(self):
        mock_invoke = AsyncMock(side_effect=_timeout_err("cognitive"))
        cost = empty_bank_cost_diagnostics()
        with patch.object(qp, "_invoke_structured", mock_invoke):
            scores, flags = await qp._validate_cognitive_quality(
                _slot(),
                _question(),
                {
                    "bank_batch_mode": True,
                    "book_grounded": True,
                    "generator_model": None,
                    "reviewer_model": None,
                },
                "chapter excerpt about budgets",
                cost_diagnostics=cost,
            )
        assert mock_invoke.await_count == 1
        assert scores == {}
        assert flags.get(VALIDATOR_UNAVAILABLE_KEY) is True
        blob = " ".join(str(r) for r in (flags.get("reasons") or [])).lower()
        assert "validator_unavailable" in blob
        assert "llm_timeout" in blob
        assert "grade_appropriate" not in flags
        assert "grounded_in_material" not in flags
        assert int(cost.get("cognitive_length_retry_attempted") or 0) == 0
        family = classify_academic_failure_family(flags.get("reasons") or [])
        assert family is None

    def test_existing_retry_limits_unchanged(self):
        assert MAX_SLOT_ATTEMPTS == 3
        assert MAX_REFILL_ATTEMPTS == 5
        assert qp.COGNITIVE_MAX_TOKENS == 2048
        assert qp.COGNITIVE_LENGTH_RETRY_MAX_TOKENS == 4096
        assert qp.MAX_EXPLANATION_ATTEMPTS == 2
        assert qp.GENERATOR_MAX_TOKENS == 2048
        assert qp.BANK_BATCH_GENERATOR_MAX_TOKENS == 4096


class TestFinalPaperUnchanged:
    def test_coverage_does_not_enable_bank_batch_timeout(self):
        src = inspect.getsource(qp.report_coverage)
        assert "bank_batch_mode=True" not in src
        assert "bank_batch_mode=bool" not in src

    def test_invoke_timeout_is_opt_in(self):
        src = inspect.getsource(qp._invoke_structured)
        assert "asyncio.wait_for" in src
        assert "bank_batch_mode: bool = False" in src
        assert "BANK_BATCH_LLM_TIMEOUT_SECONDS" in src or "bank_batch_llm_timeout_seconds" in src

    def test_bank_batch_callers_pass_mode_final_paper_generation_does_not_force(self):
        gen_src = inspect.getsource(qp._generate_for_slot)
        assert "bank_batch_mode=bank_batch_mode" in gen_src
        assert "allow_length_retry = (not bank_batch_mode)" in gen_src
        cog_src = inspect.getsource(qp._validate_cognitive_quality)
        assert 'bank_batch_mode=bool(state.get("bank_batch_mode"))' in cog_src
        assert "is_structured_output_length_error" in cog_src
        assert "COGNITIVE_LENGTH_RETRY_MAX_TOKENS" in cog_src
        assert "Return structured JSON only" in qp.BLIND_SOLVER_SYSTEM
        assert "already-validated exam question" in qp.EXPLANATION_GENERATOR_SYSTEM
