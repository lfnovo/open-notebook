"""
Provider usage extraction and Bank Batch LLM cost instrumentation.

Read-only telemetry: does not alter prompts, models, or generation behavior.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from open_notebook.utils import token_count

# Bank Batch LLM stages (also used for intent planning when cost_diagnostics passed).
LLM_STAGE_CORE_GENERATION = "core_generation"
LLM_STAGE_LENGTH_RECOVERY = "length_recovery_generation"
LLM_STAGE_BLIND_SOLVER = "blind_solver"
LLM_STAGE_COGNITIVE_QUALITY = "cognitive_quality"
LLM_STAGE_EXPLANATION_GENERATE = "explanation_generate"
LLM_STAGE_EXPLANATION_VALIDATE = "explanation_validate"
LLM_STAGE_INTENT_PLANNER_CATALOG = "intent_planner_catalog"
LLM_STAGE_INTENT_PLANNER_REPLENISH = "intent_planner_replenish"

BANK_BATCH_LLM_STAGES: tuple[str, ...] = (
    LLM_STAGE_INTENT_PLANNER_CATALOG,
    LLM_STAGE_INTENT_PLANNER_REPLENISH,
    LLM_STAGE_CORE_GENERATION,
    LLM_STAGE_LENGTH_RECOVERY,
    LLM_STAGE_BLIND_SOLVER,
    LLM_STAGE_COGNITIVE_QUALITY,
    LLM_STAGE_EXPLANATION_GENERATE,
    LLM_STAGE_EXPLANATION_VALIDATE,
)


@dataclass
class LLMUsageRecord:
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def empty_stage_usage_bucket() -> Dict[str, Any]:
    return {
        "calls": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "grounding_chars": 0,
        "grounding_tokens_est": 0,
        "latency_ms_total": 0.0,
        "avg_latency_ms": 0.0,
        "finish_reasons": {},
        "models": {},
        "prompt_composition": _empty_prompt_composition_aggregate(),
    }


def _empty_prompt_composition_aggregate() -> Dict[str, Any]:
    return {
        "calls": 0,
        "input_tokens_est": 0,
        "grounding_chars": 0,
        "grounding_tokens_est": 0,
        "components_tokens_est": {
            "static_system_instructions": 0,
            "difficulty_contract": 0,
            "structural_answer_rules": 0,
            "intent_objective_form": 0,
            "grounding_text": 0,
            "retry_feedback": 0,
            "other_user_content": 0,
        },
    }


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dig_mapping(root: Any, *keys: str) -> Dict[str, Any]:
    cur = root
    for key in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(key)
    return cur if isinstance(cur, dict) else {}


def normalize_provider_usage(
    *,
    llm_output: Optional[Mapping[str, Any]] = None,
    response_metadata: Optional[Mapping[str, Any]] = None,
    usage_metadata: Optional[Mapping[str, Any]] = None,
) -> LLMUsageRecord:
    """
    Normalize token usage from LangChain / OpenAI-compatible provider payloads.

    Supports OpenAI-style ``token_usage``, nested ``usage`` objects, and
    ``prompt_tokens_details.cached_tokens`` / ``completion_tokens_details.reasoning_tokens``.
    """
    llm_output = dict(llm_output or {})
    response_metadata = dict(response_metadata or {})
    usage_metadata = dict(usage_metadata or {})

    token_usage: Dict[str, Any] = {}
    for candidate in (
        usage_metadata,
        llm_output.get("token_usage") if isinstance(llm_output.get("token_usage"), dict) else {},
        llm_output.get("usage") if isinstance(llm_output.get("usage"), dict) else {},
        response_metadata.get("token_usage")
        if isinstance(response_metadata.get("token_usage"), dict)
        else {},
        response_metadata.get("usage") if isinstance(response_metadata.get("usage"), dict) else {},
    ):
        if candidate:
            token_usage = dict(candidate)
            break

    prompt_details = _dig_mapping(token_usage, "prompt_tokens_details")
    completion_details = _dig_mapping(token_usage, "completion_tokens_details")

    cached = (
        _coerce_int(prompt_details.get("cached_tokens"))
        or _coerce_int(token_usage.get("cached_tokens"))
        or _coerce_int(token_usage.get("cache_read_input_tokens"))
    )
    reasoning = (
        _coerce_int(completion_details.get("reasoning_tokens"))
        or _coerce_int(token_usage.get("reasoning_tokens"))
        or _coerce_int(token_usage.get("output_tokens_details", "reasoning_tokens"))
    )

    input_tokens = _coerce_int(
        token_usage.get("input_tokens")
        or token_usage.get("prompt_tokens")
        or usage_metadata.get("input_tokens")
        or usage_metadata.get("prompt_tokens")
    )
    output_tokens = _coerce_int(
        token_usage.get("output_tokens")
        or token_usage.get("completion_tokens")
        or usage_metadata.get("output_tokens")
        or usage_metadata.get("completion_tokens")
    )
    total_tokens = _coerce_int(
        token_usage.get("total_tokens") or usage_metadata.get("total_tokens")
    )
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    finish_reason = (
        response_metadata.get("finish_reason")
        or llm_output.get("finish_reason")
        or token_usage.get("finish_reason")
    )
    if isinstance(finish_reason, list):
        finish_reason = finish_reason[0] if finish_reason else None
    finish_reason = str(finish_reason) if finish_reason else None

    model = (
        response_metadata.get("model_name")
        or response_metadata.get("model")
        or llm_output.get("model_name")
        or llm_output.get("model")
    )
    provider = response_metadata.get("model_provider") or llm_output.get("model_provider")

    return LLMUsageRecord(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cached_input_tokens=cached,
        reasoning_tokens=reasoning,
        finish_reason=finish_reason,
        model=str(model) if model else None,
        provider=str(provider) if provider else None,
    )


def extract_usage_from_message(message: Any) -> LLMUsageRecord:
    """Extract usage from a LangChain AIMessage (or compatible dict)."""
    if message is None:
        return LLMUsageRecord()
    if isinstance(message, dict):
        response_metadata = message.get("response_metadata") or {}
        usage_metadata = message.get("usage_metadata") or {}
        return normalize_provider_usage(
            response_metadata=response_metadata,
            usage_metadata=usage_metadata,
        )
    response_metadata = getattr(message, "response_metadata", None) or {}
    usage_metadata = getattr(message, "usage_metadata", None) or {}
    return normalize_provider_usage(
        response_metadata=response_metadata,
        usage_metadata=usage_metadata,
    )


def build_prompt_composition(
    *,
    system_prompt: str,
    user_prompt: str,
    grounding_text: str = "",
    static_system_instructions: str = "",
    difficulty_contract: str = "",
    structural_answer_rules: str = "",
    intent_objective_form: str = "",
    retry_feedback: str = "",
) -> Dict[str, Any]:
    """
    Approximate logical prompt composition sizes without altering prompt text.

    ``grounding_text`` is the raw chapter/snippet text embedded in the user prompt.
    Component strings should be the same fragments already used to build the prompt.
    """
    sys_tokens = token_count(system_prompt or "")
    user_tokens = token_count(user_prompt or "")
    grounding_chars = len(grounding_text or "")
    grounding_tokens_est = token_count(grounding_text) if grounding_text else 0
    input_tokens_est = sys_tokens + user_tokens

    static_tokens = token_count(static_system_instructions or system_prompt or "")
    diff_tokens = token_count(difficulty_contract or "")
    struct_tokens = token_count(structural_answer_rules or "")
    intent_tokens = token_count(intent_objective_form or "")
    retry_tokens = token_count(retry_feedback or "")
    known_user = diff_tokens + struct_tokens + intent_tokens + grounding_tokens_est + retry_tokens
    other_user = max(0, user_tokens - known_user)

    grounding_pct = (
        round(100.0 * grounding_tokens_est / input_tokens_est, 2)
        if input_tokens_est
        else 0.0
    )

    return {
        "system_chars": len(system_prompt or ""),
        "user_chars": len(user_prompt or ""),
        "system_tokens_est": sys_tokens,
        "user_tokens_est": user_tokens,
        "input_tokens_est": input_tokens_est,
        "grounding_chars": grounding_chars,
        "grounding_tokens_est": grounding_tokens_est,
        "grounding_pct_of_input_est": grounding_pct,
        "components_tokens_est": {
            "static_system_instructions": static_tokens,
            "difficulty_contract": diff_tokens,
            "structural_answer_rules": struct_tokens,
            "intent_objective_form": intent_tokens,
            "grounding_text": grounding_tokens_est,
            "retry_feedback": retry_tokens,
            "other_user_content": other_user,
        },
    }


def _accumulate_prompt_composition(
    bucket: MutableMapping[str, Any],
    composition: Optional[Mapping[str, Any]],
) -> None:
    if not composition:
        return
    agg = bucket.setdefault("prompt_composition", _empty_prompt_composition_aggregate())
    agg["calls"] = int(agg.get("calls") or 0) + 1
    agg["input_tokens_est"] = int(agg.get("input_tokens_est") or 0) + int(
        composition.get("input_tokens_est") or 0
    )
    agg["grounding_chars"] = int(agg.get("grounding_chars") or 0) + int(
        composition.get("grounding_chars") or 0
    )
    agg["grounding_tokens_est"] = int(agg.get("grounding_tokens_est") or 0) + int(
        composition.get("grounding_tokens_est") or 0
    )
    src_components = composition.get("components_tokens_est") or {}
    dst_components = agg.setdefault(
        "components_tokens_est",
        _empty_prompt_composition_aggregate()["components_tokens_est"],
    )
    if isinstance(src_components, dict):
        for key, value in src_components.items():
            dst_components[key] = int(dst_components.get(key) or 0) + int(value or 0)


def record_llm_stage_usage(
    diagnostics: MutableMapping[str, Any],
    stage: str,
    usage: LLMUsageRecord,
    *,
    elapsed_ms: float,
    prompt_composition: Optional[Mapping[str, Any]] = None,
    model_id: Optional[str] = None,
    tags: Optional[Mapping[str, Any]] = None,
) -> None:
    """Accumulate one LLM call into batch diagnostics (provider + estimated composition)."""
    by_stage = diagnostics.setdefault("llm_usage_by_stage", {})
    bucket = by_stage.setdefault(stage, empty_stage_usage_bucket())
    bucket["calls"] = int(bucket.get("calls") or 0) + 1
    bucket["latency_ms_total"] = float(bucket.get("latency_ms_total") or 0.0) + float(
        elapsed_ms
    )
    n = int(bucket.get("calls") or 0)
    bucket["avg_latency_ms"] = round(float(bucket["latency_ms_total"]) / n, 2) if n else 0.0

    for field_name, key in (
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
        ("cached_input_tokens", "cached_input_tokens"),
        ("reasoning_tokens", "reasoning_tokens"),
    ):
        val = getattr(usage, field_name)
        if val is not None:
            bucket[key] = int(bucket.get(key) or 0) + int(val)

    if prompt_composition:
        bucket["grounding_chars"] = int(bucket.get("grounding_chars") or 0) + int(
            prompt_composition.get("grounding_chars") or 0
        )
        bucket["grounding_tokens_est"] = int(bucket.get("grounding_tokens_est") or 0) + int(
            prompt_composition.get("grounding_tokens_est") or 0
        )
        _accumulate_prompt_composition(bucket, prompt_composition)

    model_name = usage.model or model_id
    if model_name:
        models = bucket.setdefault("models", {})
        models[str(model_name)] = int(models.get(str(model_name)) or 0) + 1

    if usage.finish_reason:
        reasons = bucket.setdefault("finish_reasons", {})
        reasons[str(usage.finish_reason)] = int(reasons.get(str(usage.finish_reason)) or 0) + 1

    # Compact per-call log for wasted-token attribution (no prompt/CoT text).
    call_entry: Dict[str, Any] = {
        "stage": stage,
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "total_tokens": usage.total_tokens,
        "finish_reason": usage.finish_reason,
        "model": model_name,
        "provider": usage.provider,
        "duration_ms": round(float(elapsed_ms), 2),
        "grounding_chars": int((prompt_composition or {}).get("grounding_chars") or 0),
        "grounding_tokens_est": int(
            (prompt_composition or {}).get("grounding_tokens_est") or 0
        ),
    }
    if tags:
        call_entry.update(dict(tags))
    log = diagnostics.setdefault("llm_call_log", [])
    log.append(call_entry)
    diagnostics["llm_call_log"] = log[-500:]


def tag_last_llm_call(
    diagnostics: MutableMapping[str, Any],
    **tags: Any,
) -> None:
    """Attach outcome/metadata to the most recent llm_call_log entry."""
    log = diagnostics.get("llm_call_log") or []
    if not log:
        return
    last = dict(log[-1])
    last.update(tags)
    log[-1] = last
    diagnostics["llm_call_log"] = log


def tag_recent_llm_calls(
    diagnostics: MutableMapping[str, Any],
    *,
    count: int = 3,
    **tags: Any,
) -> None:
    """Attach tags to the last ``count`` llm_call_log entries (no prompt text)."""
    log = list(diagnostics.get("llm_call_log") or [])
    if not log or count <= 0:
        return
    updated = list(log)
    for i in range(max(0, len(updated) - count), len(updated)):
        entry = dict(updated[i])
        entry.update(tags)
        updated[i] = entry
    diagnostics["llm_call_log"] = updated


def build_stage_usage_table(
    diagnostics: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Return ``Stage | Calls | Input | Cached | Output | Reasoning | Avg | Total latency`` rows."""
    by_stage = dict(diagnostics.get("llm_usage_by_stage") or {})
    rows: List[Dict[str, Any]] = []
    stage_order = list(BANK_BATCH_LLM_STAGES) + sorted(
        s for s in by_stage.keys() if s not in BANK_BATCH_LLM_STAGES
    )
    for stage in stage_order:
        bucket = by_stage.get(stage)
        if not bucket or not int(bucket.get("calls") or 0):
            continue
        rows.append(
            {
                "stage": stage,
                "calls": int(bucket.get("calls") or 0),
                "input_tokens": int(bucket.get("input_tokens") or 0),
                "cached_input_tokens": int(bucket.get("cached_input_tokens") or 0),
                "output_tokens": int(bucket.get("output_tokens") or 0),
                "reasoning_tokens": int(bucket.get("reasoning_tokens") or 0),
                "total_tokens": int(bucket.get("total_tokens") or 0),
                "avg_latency_ms": float(bucket.get("avg_latency_ms") or 0.0),
                "latency_ms_total": float(bucket.get("latency_ms_total") or 0.0),
                "grounding_chars": int(bucket.get("grounding_chars") or 0),
                "grounding_tokens_est": int(bucket.get("grounding_tokens_est") or 0),
            }
        )
    return rows


def finalize_llm_usage_diagnostics(
    diagnostics: MutableMapping[str, Any],
    *,
    accepted_count: int = 0,
    processing_time_seconds: Optional[float] = None,
) -> None:
    """Derive batch efficiency + wasted-token summaries from accumulated call logs."""
    diagnostics["stage_usage_table"] = build_stage_usage_table(diagnostics)

    log: Sequence[Mapping[str, Any]] = diagnostics.get("llm_call_log") or []
    total_input = sum(int(c.get("input_tokens") or 0) for c in log)
    total_output = sum(int(c.get("output_tokens") or 0) for c in log)
    total_cached = sum(int(c.get("cached_input_tokens") or 0) for c in log)
    total_reasoning = sum(int(c.get("reasoning_tokens") or 0) for c in log)
    total_tokens = sum(int(c.get("total_tokens") or 0) for c in log)
    total_calls = len(log)

    accepted = max(0, int(accepted_count or 0))
    diagnostics["llm_usage_totals"] = {
        "llm_calls": total_calls,
        "input_tokens": total_input,
        "cached_input_tokens": total_cached,
        "output_tokens": total_output,
        "reasoning_tokens": total_reasoning,
        "total_tokens": total_tokens,
    }

    if accepted:
        diagnostics["batch_efficiency"] = {
            "tokens_per_accepted_question": round(total_tokens / accepted, 2)
            if total_tokens
            else None,
            "llm_calls_per_accepted_question": round(total_calls / accepted, 2),
            "seconds_per_accepted_question": round(
                float(processing_time_seconds) / accepted, 2
            )
            if processing_time_seconds
            else None,
        }
    else:
        diagnostics["batch_efficiency"] = {
            "tokens_per_accepted_question": None,
            "llm_calls_per_accepted_question": None,
            "seconds_per_accepted_question": None,
        }

    core_validated = int(diagnostics.get("core_validated_count") or 0)
    core_gen_tokens = sum(
        int(c.get("total_tokens") or 0)
        for c in log
        if c.get("stage") in (LLM_STAGE_CORE_GENERATION, LLM_STAGE_LENGTH_RECOVERY)
    )
    diagnostics["core_generation_tokens_per_usable_core"] = (
        round(core_gen_tokens / core_validated, 2) if core_validated and core_gen_tokens else None
    )

    def _sum_tokens(predicate) -> int:
        return sum(int(c.get("total_tokens") or 0) for c in log if predicate(c))

    diagnostics["wasted_tokens"] = {
        "generation_failures": _sum_tokens(
            lambda c: c.get("stage") == LLM_STAGE_CORE_GENERATION
            and c.get("outcome") == "generation_failed"
        ),
        "length_recovery_first_attempts": _sum_tokens(
            lambda c: c.get("stage") == LLM_STAGE_CORE_GENERATION
            and c.get("outcome") == "length_recovery_discarded"
        ),
        "cores_rejected_before_explanation": _sum_tokens(
            lambda c: c.get("outcome") == "core_rejected_before_explanation"
        ),
        "intent_planning_all_stages": _sum_tokens(
            lambda c: str(c.get("stage") or "").startswith("intent_planner")
        ),
    }

    # Back-fill stage_tokens_approx from provider totals where available.
    approx = diagnostics.setdefault("stage_tokens_approx", {})
    by_stage = diagnostics.get("llm_usage_by_stage") or {}
    for stage, bucket in by_stage.items():
        stage_key = stage
        if stage == LLM_STAGE_LENGTH_RECOVERY:
            stage_key = "generate"
        elif stage == LLM_STAGE_CORE_GENERATION:
            stage_key = "generate"
        if int(bucket.get("input_tokens") or 0):
            approx[stage_key] = int(approx.get(stage_key) or 0) + int(
                bucket.get("input_tokens") or 0
            )


class UsageCaptureCallback:
    """Minimal LangChain callback handler capturing token usage on LLM end."""

    def __init__(self) -> None:
        self.usage = LLMUsageRecord()
        self.llm_output: Dict[str, Any] = {}

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        llm_output = getattr(response, "llm_output", None) or {}
        self.llm_output = dict(llm_output) if isinstance(llm_output, dict) else {}
        generations = getattr(response, "generations", None) or []
        response_metadata: Dict[str, Any] = {}
        if generations:
            gen0 = generations[0][0] if generations[0] else None
            if gen0 is not None:
                message = getattr(gen0, "message", None)
                if message is not None:
                    self.usage = extract_usage_from_message(message)
                    return
                response_metadata = getattr(gen0, "generation_info", None) or {}
        self.usage = normalize_provider_usage(
            llm_output=self.llm_output,
            response_metadata=response_metadata,
        )


try:
    from langchain_core.callbacks import AsyncCallbackHandler

    class AsyncUsageCaptureCallback(AsyncCallbackHandler, UsageCaptureCallback):
        """Async LangChain callback for structured-output invocations."""

        async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
            UsageCaptureCallback.on_llm_end(self, response, **kwargs)

except ImportError:  # pragma: no cover
    AsyncUsageCaptureCallback = UsageCaptureCallback  # type: ignore[misc, assignment]
