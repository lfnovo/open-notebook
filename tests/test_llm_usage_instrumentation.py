"""Offline tests for LLM provider-usage instrumentation (no live API)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.ai.llm_usage import (
    LLM_STAGE_BLIND_SOLVER,
    LLM_STAGE_CORE_GENERATION,
    LLM_STAGE_LENGTH_RECOVERY,
    LLMUsageRecord,
    build_prompt_composition,
    extract_usage_from_message,
    finalize_llm_usage_diagnostics,
    normalize_provider_usage,
    record_llm_stage_usage,
    tag_last_llm_call,
    tag_recent_llm_calls,
)
from open_notebook.graphs.question_paper_blueprint import (
    empty_bank_cost_diagnostics,
    finalize_bank_cost_diagnostics,
)


def test_normalize_openai_usage_with_cached_and_reasoning():
    usage = normalize_provider_usage(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 1200,
                "completion_tokens": 180,
                "total_tokens": 1380,
                "prompt_tokens_details": {"cached_tokens": 900},
                "completion_tokens_details": {"reasoning_tokens": 64},
            },
            "finish_reason": "stop",
            "model_name": "gpt-5-mini",
        }
    )
    assert usage.input_tokens == 1200
    assert usage.output_tokens == 180
    assert usage.total_tokens == 1380
    assert usage.cached_input_tokens == 900
    assert usage.reasoning_tokens == 64
    assert usage.finish_reason == "stop"
    assert usage.model == "gpt-5-mini"


def test_extract_usage_from_langchain_aimessage_shape():
    msg = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 500,
                "completion_tokens": 50,
                "total_tokens": 550,
            },
            "finish_reason": "stop",
        },
        usage_metadata={},
    )
    usage = extract_usage_from_message(msg)
    assert usage.input_tokens == 500
    assert usage.output_tokens == 50


def test_build_prompt_composition_grounding_pct():
    comp = build_prompt_composition(
        system_prompt="system rules " * 20,
        user_prompt="user slot metadata " * 10 + "chapter text " * 50,
        grounding_text="chapter text " * 50,
        static_system_instructions="system rules " * 20,
    )
    assert comp["grounding_chars"] > 0
    assert comp["grounding_tokens_est"] > 0
    assert 0 < comp["grounding_pct_of_input_est"] <= 100


def test_record_and_finalize_batch_diagnostics():
    diag = empty_bank_cost_diagnostics()
    usage = LLMUsageRecord(
        input_tokens=1000,
        output_tokens=100,
        total_tokens=1100,
        cached_input_tokens=400,
        reasoning_tokens=0,
        finish_reason="stop",
        model="gpt-5-mini",
    )
    comp = build_prompt_composition(
        system_prompt="x" * 400,
        user_prompt="y" * 800,
        grounding_text="z" * 600,
    )
    record_llm_stage_usage(
        diag,
        LLM_STAGE_CORE_GENERATION,
        usage,
        elapsed_ms=1234.5,
        prompt_composition=comp,
    )
    tag_last_llm_call(diag, outcome="core_produced")

    out = finalize_bank_cost_diagnostics(diag, accepted_count=1, processing_time_seconds=10.0)
    assert out["llm_usage_by_stage"][LLM_STAGE_CORE_GENERATION]["calls"] == 1
    assert out["llm_usage_by_stage"][LLM_STAGE_CORE_GENERATION]["input_tokens"] == 1000
    assert out["llm_usage_by_stage"][LLM_STAGE_CORE_GENERATION]["cached_input_tokens"] == 400
    assert out["stage_usage_table"]
    assert out["batch_efficiency"]["tokens_per_accepted_question"] == 1100.0
    assert out["batch_efficiency"]["llm_calls_per_accepted_question"] == 1.0
    assert out["llm_usage_totals"]["total_tokens"] == 1100


def test_wasted_tokens_from_outcome_tags():
    diag = empty_bank_cost_diagnostics()
    for stage, outcome, total in (
        (LLM_STAGE_CORE_GENERATION, "length_recovery_discarded", 800),
        (LLM_STAGE_LENGTH_RECOVERY, "core_produced", 900),
        (LLM_STAGE_BLIND_SOLVER, "core_rejected_before_explanation", 200),
    ):
        record_llm_stage_usage(
            diag,
            stage,
            LLMUsageRecord(total_tokens=total),
            elapsed_ms=1.0,
        )
        tag_last_llm_call(diag, outcome=outcome)

    finalize_llm_usage_diagnostics(diag, accepted_count=0)
    wasted = diag["wasted_tokens"]
    assert wasted["length_recovery_first_attempts"] == 800
    assert wasted["cores_rejected_before_explanation"] == 200


def test_tag_recent_llm_calls():
    diag = empty_bank_cost_diagnostics()
    for i in range(3):
        record_llm_stage_usage(
            diag,
            LLM_STAGE_CORE_GENERATION,
            LLMUsageRecord(total_tokens=100 + i),
            elapsed_ms=1.0,
        )
    tag_recent_llm_calls(diag, count=2, outcome="core_rejected_before_explanation")
    log = diag["llm_call_log"]
    assert log[0].get("outcome") is None
    assert log[1]["outcome"] == "core_rejected_before_explanation"
    assert log[2]["outcome"] == "core_rejected_before_explanation"


@pytest.mark.asyncio
async def test_invoke_structured_records_provider_usage():
    from open_notebook.graphs import question_paper as qp
    from pydantic import BaseModel

    class _Out(BaseModel):
        value: str

    raw_msg = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 321,
                "completion_tokens": 12,
                "total_tokens": 333,
                "prompt_tokens_details": {"cached_tokens": 100},
            },
            "finish_reason": "stop",
            "model_name": "mock-model",
        },
        usage_metadata={},
    )
    fake_model = SimpleNamespace(model_name="mock-model")

    async def _fake_provision(*_a, **_k):
        return fake_model

    fake_model.with_structured_output = lambda schema, include_raw=True: SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={"parsed": _Out(value="ok"), "raw": raw_msg},
        )
    )

    diag = empty_bank_cost_diagnostics()
    with patch.object(qp, "provision_langchain_model", side_effect=_fake_provision):
        result = await qp._invoke_structured(
            "system",
            "user",
            "model:test",
            _Out,
            llm_stage=LLM_STAGE_CORE_GENERATION,
            cost_diagnostics=diag,
            prompt_composition=build_prompt_composition(
                system_prompt="system",
                user_prompt="user",
                grounding_text="ground",
            ),
        )

    assert result.value == "ok"
    bucket = diag["llm_usage_by_stage"][LLM_STAGE_CORE_GENERATION]
    assert bucket["calls"] == 1
    assert bucket["input_tokens"] == 321
    assert bucket["cached_input_tokens"] == 100
    assert bucket["grounding_chars"] == len("ground")
