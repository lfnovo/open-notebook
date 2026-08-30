"""
Question Paper Generator — slot-based LangGraph pipeline.

Flow:
  prepare → fill_slots → assemble → coverage → audit → persist_bank

Each blueprint slot is generated and independently validated (separate LLM call).
Cognitive scores are summed in Python; target vs validated difficulty must match.
The 12,000-character book excerpt cap is not used: chapter boundaries are kept
and long chapters are chunked so later portions remain eligible.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.llm_usage import (
    AsyncUsageCaptureCallback,
    LLMUsageRecord,
    LLM_STAGE_BLIND_SOLVER,
    LLM_STAGE_COGNITIVE_QUALITY,
    LLM_STAGE_CORE_GENERATION,
    LLM_STAGE_EXPLANATION_GENERATE,
    LLM_STAGE_EXPLANATION_VALIDATE,
    LLM_STAGE_LENGTH_RECOVERY,
    build_prompt_composition,
    extract_usage_from_message,
    record_llm_stage_usage,
    tag_last_llm_call,
    tag_recent_llm_calls,
)
from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.question_bank import QuestionRecord
from open_notebook.exceptions import ExternalServiceError
from open_notebook.graphs.question_bank_intent import (
    ADHERENCE_PARTIAL,
    INTENT_DRIFT_REJECTION,
    apply_academic_failure_intent_policy,
    apply_duplicate_intent_policy,
    attach_variety_diagnostics,
    classify_academic_failure_family,
    classify_intent_adherence,
    classify_variety_relation,
    cognitive_form_correction_hint,
    empty_intent_diagnostics,
    ensure_easy_safe_assigned_intent,
    format_assigned_intent_guidance,
    format_bank_batch_novelty_brief,
    intent_drift_feedback,
    is_bank_intent_planner_enabled,
    partial_adherence_may_continue,
    question_task_form,
    record_adherence_diagnostic,
    rejection_is_duplicate,
    replenish_running_pool,
    select_closest_bank_stems_for_intent,
    should_early_reject_for_intent_drift,
    should_replenish_catalog,
    take_next_unused_intent,
    variety_counts_toward_intent_retirement,
)
from open_notebook.graphs.question_paper_blueprint import (
    CHAPTER_CHUNK_SIZE,
    COGNITIVE_CRITERIA,
    DIFFICULTY_DEFINITIONS,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    MAX_SLOT_CONCURRENCY,
    VALIDATOR_CRITERION_RUBRIC,
    VALIDATOR_UNAVAILABLE_KEY,
    QuestionSlot,
    apply_independent_validation,
    audit_paper,
    bank_batch_generation_budget_block_reason,
    build_effective_preset,
    build_rejected_attempt_record,
    build_slot_avoidance_history,
    build_slots,
    bump_bank_early_exit,
    bump_reason_counts,
    chunk_chapter_text,
    classify_bank_refill_strategy,
    decide_slot_outcome,
    empty_bank_cost_diagnostics,
    empty_bank_refill_diagnostics,
    finalize_bank_cost_diagnostics,
    find_lexical_duplicate_match,
    find_semantic_duplicate_match,
    format_bank_batch_duplicate_retry_guidance,
    format_bank_batch_strategy_guidance,
    format_diversity_guidance,
    format_slot_difficulty_guidance,
    format_underused_concept_hints,
    generator_structural_self_check,
    is_bank_diversity_planner_enabled,
    is_llm_timeout_error,
    is_near_duplicate,
    bank_batch_llm_timeout_seconds,
    map_bank_batch_timeout_stage,
    record_llm_timeout,
    normalize_difficulty,
    plan_bank_batch_diversity,
    record_bank_cost_stage,
    record_blind_solver_outcome,
    parse_completion_usage_from_exc,
    record_validation_chunk_reselection,
    run_bank_batch_early_gates,
    select_bank_batch_forbidden_stems,
    select_blind_solver_source_snippet,
    select_cognitive_source_window,
    select_source_grounding_window,
    select_validation_chunk_for_generated,
    select_chapter_chunk,
    select_chunk_avoiding_history,
    select_chunk_for_diversity_plan,
    summarize_diversity_usage,
    validate_chapter_selection,
    _extract_intent_words,
    _rejected_validation_stub,
    intent_fingerprint,
)
from open_notebook.utils.error_classifier import classify_error

OPTION_LABELS = ("A", "B", "C", "D", "E")
SECTION_RE = re.compile(
    r"=== SECTION\s+\d+:\s*(.+?)\s*===\n(.*?)(?=\n=== SECTION |\Z)",
    re.S,
)

# Generator completion budget.
# Final Paper: 2048 first, then one 4096 retry on LengthFinishReasonError.
# Bank Batch core generation: 4096 first (no discarded 2048 attempt).
GENERATOR_MAX_TOKENS = 2048
GENERATOR_LENGTH_RETRY_MAX_TOKENS = 4096
BANK_BATCH_GENERATOR_MAX_TOKENS = 4096
# Cognitive validator: 2048 first; one 4096 retry on LengthFinishReasonError only.
COGNITIVE_MAX_TOKENS = 2048
COGNITIVE_LENGTH_RETRY_MAX_TOKENS = 4096
# Blind solver: 2048 first; Bank Batch only — one 4096 retry on LengthFinishReasonError.
BLIND_MAX_TOKENS = 2048
BLIND_LENGTH_RETRY_MAX_TOKENS = 4096
# Bank Batch: initial explanation + one corrective retry (core stays frozen).
MAX_EXPLANATION_ATTEMPTS = 2
EXPLANATION_MAX_TOKENS = 1024


def is_structured_output_length_error(exc: BaseException) -> bool:
    """True when structured generation exhausted completion/length with no usable output."""
    if is_llm_timeout_error(exc):
        return False
    parts: List[str] = [type(exc).__name__, str(exc)]
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        parts.append(type(cause).__name__)
        parts.append(str(cause))
    blob = " ".join(parts).lower()
    if "lengthfinishreason" in blob:
        return True
    if "length limit was reached" in blob:
        return True
    if "could not parse response content as the length limit" in blob:
        return True
    return False


def cognitive_validator_unavailable_payload(
    exc: BaseException,
) -> Tuple[dict, dict]:
    """Fail-closed Cognitive result when the validator LLM did not complete.

    Does not invent criterion scores or quality flags (no fake Easy-8 / Grade /
    grounding). apply_independent_validation still rejects the attempt.
    """
    if is_structured_output_length_error(exc):
        reason = (
            "validator_unavailable: cognitive validator length limit was reached"
        )
    else:
        reason = f"validator_unavailable: cognitive validator error: {exc}"
    return {}, {
        VALIDATOR_UNAVAILABLE_KEY: True,
        "reasons": [reason],
    }


class BlindSolverUnavailable:
    """Bank Batch: Blind LLM did not complete after length recovery. Fail-closed."""

    def __init__(self, reason: str):
        self.reason = reason


def blind_validator_unavailable_reason(exc: BaseException) -> str:
    if is_structured_output_length_error(exc):
        return "validator_unavailable: blind solver length limit was reached"
    return f"validator_unavailable: blind solver error: {exc}"


# ---------------------------------------------------------------------------
# Structured output schemas
# ---------------------------------------------------------------------------

class SlotGeneratedQuestion(BaseModel):
    question: str
    topic: str
    sub_topic: str = ""
    options: List[str] = Field(description="Exactly five options, A–E, in order")
    correct_indices: List[int] = Field(
        description="0-based indices of every correct option"
    )
    answer: str = Field(description="Correct option letter(s) and/or option text")
    explanation: str


class CoreGeneratedQuestion(BaseModel):
    """Bank Batch core generation — explanation is produced only after core validation."""

    question: str
    topic: str
    sub_topic: str = ""
    options: List[str] = Field(description="Exactly five options, A–E, in order")
    correct_indices: List[int] = Field(
        description="0-based indices of every correct option"
    )
    answer: str = Field(description="Correct option letter(s) and/or option text")


class ExplanationOnlyOutput(BaseModel):
    """Post-core explanation for an already-validated Bank Batch question core."""

    explanation: str = Field(
        description="Clear Grade-appropriate explanation defending the correct answer(s)"
    )


class CognitiveCriterionScores(BaseModel):
    knowledge: int
    reasoning: int
    context: int
    application: int
    interpretation: int
    decision_making: int
    concept_integration: int
    distractor_quality: int


class CoverageReportOutput(BaseModel):
    covered_topics: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


class OptionDefensibility(BaseModel):
    option: str = Field(description="Option label, e.g. A, B, C, D, E")
    defensible: bool


class BlindSolverOutput(BaseModel):
    """Stage 1: solve without seeing the answer key. Validation fields only."""

    independently_derived_indices: List[int] = Field(
        description="0-based indices of every option the solver believes is correct"
    )
    option_analysis: List[OptionDefensibility] = Field(
        description="Per-option A–E: label and whether the option is defensible"
    )
    information_sufficient: bool = Field(
        description="Does the stem provide enough information to uniquely determine the answer?"
    )
    arithmetic_consistent: bool = Field(
        description="Are all numbers in the stem and options internally consistent?"
    )
    no_unsupported_claims: bool = Field(
        description="Free of absolute/misleading claims not supported by the material?"
    )
    terminology_grounded: bool = Field(
        default=True,
        description="Are specialized/advanced terms in the stem explicitly supported by the provided chapter excerpt?"
    )


class IndependentValidatorOutput(BaseModel):
    """Stage 2: cognitive + quality scoring (receives the answer key)."""
    criterion_scores: CognitiveCriterionScores
    content_valid: bool
    answer_valid: bool
    grade_appropriate: bool
    distractors_ok: bool
    unambiguous: bool
    language_clear: bool
    grounded_in_material: bool = True
    explanation_valid: bool
    concept_relevant: bool = True
    no_unrelated_external_knowledge: bool = True
    stem_self_contained: bool = True
    natural_assessment_wording: bool = True
    scenario_focused: bool = True
    options_independently_assessable: bool = True
    option_style_balanced: bool = True
    misconception_based_distractors: bool = True
    reasons: List[str] = Field(default_factory=list)


class CoreIndependentValidatorOutput(BaseModel):
    """Bank Batch core phase — same quality flags without explanation_valid."""

    criterion_scores: CognitiveCriterionScores
    content_valid: bool
    answer_valid: bool
    grade_appropriate: bool
    distractors_ok: bool
    unambiguous: bool
    language_clear: bool
    grounded_in_material: bool = True
    concept_relevant: bool = True
    no_unrelated_external_knowledge: bool = True
    stem_self_contained: bool = True
    natural_assessment_wording: bool = True
    scenario_focused: bool = True
    options_independently_assessable: bool = True
    option_style_balanced: bool = True
    misconception_based_distractors: bool = True
    reasons: List[str] = Field(default_factory=list)


class ExplanationValidatorOutput(BaseModel):
    """Bank Batch explanation-only validation after a frozen core passes."""

    explanation_valid: bool
    reasons: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class PaperState(TypedDict, total=False):
    topic: str
    difficulty: str
    target_marks: int
    section_config: dict
    curriculum_objectives: List[str]
    generator_model: Optional[str]
    reviewer_model: Optional[str]
    book_content: Optional[str]
    book_chapters: List[dict]
    grade: str
    subject: str
    language: str
    pass_percentage: int
    options_per_question: int
    blueprint_preset: dict
    max_slot_attempts: int
    max_refill_attempts: int
    slot_concurrency: int
    used_stems: List[str]
    raw_questions: List[dict]
    deduplicated: List[dict]
    approved: List[dict]
    rejected_with_feedback: List[dict]
    failed_slots: List[dict]
    slots: List[dict]
    chapter_chunks: Dict[str, List[str]]
    effective_preset: dict
    book_grounded: bool
    final_paper: dict
    answer_key: List[dict]
    coverage_gaps: List[str]
    covered_topics: List[str]
    retry_count: int
    audit: dict
    # Question Bank Batch mode (optional; final-paper jobs omit these)
    bank_batch_mode: bool
    bank_batch_blueprint: dict
    batch_id: str
    book_id: str
    bank_duplicate_seed_texts: List[str]
    bank_duplicate_seed_questions: List[dict]
    bank_diversity_catalog: dict
    bank_intent_catalog: List[dict]
    bank_intent_assignments: dict
    bank_intent_remaining: List[dict]
    intent_diagnostics: dict
    intent_planner_context: dict
    persisted_question_ids: List[str]
    refill_diagnostics: dict
    cost_diagnostics: dict
    target_refill_cycles_done: int
    max_target_refill_cycles: int
    refill_phase: str
    slot_avoidance_by_number: dict
    # Optional Bank Batch minimum-target + batch-level generation ceilings
    minimum_accepted_questions: Optional[int]
    max_batch_generation_attempts: Optional[int]
    max_batch_runtime_seconds: Optional[int]
    batch_started_at: float
    batch_budget_exhausted_reason: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Extract JSON from model output that may be wrapped in markdown code fences."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        return fence.group(1).strip()
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]
    return text


async def _invoke_structured(
    system_prompt: str,
    user_prompt: str,
    model_id: Optional[str],
    output_schema: type,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    llm_stage: Optional[str] = None,
    cost_diagnostics: Optional[dict] = None,
    prompt_composition: Optional[dict] = None,
    usage_tags: Optional[dict] = None,
    bank_batch_mode: bool = False,
):
    """
    Invoke a model with structured output enforcement via with_structured_output().
    Falls back to plain JSON extraction if the provider does not support it.

    Optional ``llm_stage`` + ``cost_diagnostics`` record provider usage without
    altering prompts or model behavior.

    Bank Batch only: ``bank_batch_mode=True`` wraps the provider ``ainvoke`` in
    ``asyncio.wait_for`` using ``BANK_BATCH_LLM_TIMEOUT_SECONDS`` (default 180).
    Timeout is an infrastructure failure, not a quality/academic failure.
    Final Paper callers omit ``bank_batch_mode`` and are unchanged.
    """
    t0 = time.perf_counter()
    usage = LLMUsageRecord()
    resolved_model_id = model_id
    timed_out = False
    request_timeout = (
        bank_batch_llm_timeout_seconds() if bank_batch_mode else None
    )
    try:
        model = await provision_langchain_model(
            system_prompt,
            model_id,
            "chat",
            max_tokens=max_tokens,
            temperature=temperature,
        )
        resolved_model_id = (
            getattr(model, "model_name", None)
            or getattr(model, "model", None)
            or model_id
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        async def _invoke_model():
            nonlocal usage
            try:
                try:
                    structured = model.with_structured_output(
                        output_schema, include_raw=True
                    )
                    wrapper = await structured.ainvoke(messages)
                    if isinstance(wrapper, dict) and wrapper.get("parsed") is not None:
                        result = wrapper["parsed"]
                        raw_msg = wrapper.get("raw")
                        if raw_msg is not None:
                            usage = extract_usage_from_message(raw_msg)
                    else:
                        result = wrapper
                except TypeError:
                    handler = AsyncUsageCaptureCallback()
                    structured = model.with_structured_output(output_schema)
                    result = await structured.ainvoke(
                        messages, config={"callbacks": [handler]}
                    )
                    usage = handler.usage
            except (NotImplementedError, AttributeError):
                logger.debug(
                    f"Structured output not supported, falling back to plain JSON for {output_schema.__name__}"
                )
                handler = AsyncUsageCaptureCallback()
                response = await model.ainvoke(
                    messages, config={"callbacks": [handler]}
                )
                usage = handler.usage or extract_usage_from_message(response)
                content = response.content
                if isinstance(content, list):
                    content = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    )
                raw = json.loads(_extract_json(str(content)))
                result = output_schema.model_validate(raw)
            return result

        invoke_t0 = time.perf_counter()
        try:
            if request_timeout:
                result = await asyncio.wait_for(
                    _invoke_model(), timeout=request_timeout
                )
            else:
                result = await _invoke_model()
            return result
        except asyncio.TimeoutError:
            timed_out = True
            elapsed_ms = (time.perf_counter() - invoke_t0) * 1000.0
            mapped = map_bank_batch_timeout_stage(llm_stage)
            record_llm_timeout(
                cost_diagnostics,
                stage=mapped,
                duration_ms=elapsed_ms,
                limit_seconds=request_timeout,
            )
            logger.error(
                f"Bank Batch LLM timeout stage={mapped} after {elapsed_ms:.0f}ms "
                f"(limit={request_timeout:g}s)"
            )
            raise ExternalServiceError(
                f"llm_timeout: {mapped} exceeded {request_timeout:g}s "
                f"after {elapsed_ms:.0f}ms"
            )
    except ExternalServiceError:
        raise
    except Exception as e:
        exc_class, message = classify_error(e)
        raise exc_class(message) from e
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if cost_diagnostics is not None and llm_stage:
            if usage.model is None and resolved_model_id:
                usage.model = str(resolved_model_id)
            tags = dict(usage_tags or {})
            if timed_out:
                tags["outcome"] = "llm_timeout"
            record_llm_stage_usage(
                cost_diagnostics,
                llm_stage,
                usage,
                elapsed_ms=elapsed_ms,
                prompt_composition=prompt_composition,
                model_id=str(resolved_model_id) if resolved_model_id else None,
                tags=tags or None,
            )


def parse_book_chapters(
    book_chapters: Optional[List[dict]],
    book_content: Optional[str],
) -> List[dict]:
    """Keep chapter boundaries from structured chapters or === SECTION === markers."""
    if book_chapters:
        parsed = []
        for ch in book_chapters:
            text = (ch.get("text") or "").strip()
            if not text:
                continue
            parsed.append(
                {
                    "title": ch.get("title") or f"Chapter {len(parsed) + 1}",
                    "text": text,
                }
            )
        if parsed:
            return parsed
    content = (book_content or "").strip()
    if not content:
        return []
    matches = SECTION_RE.findall(content)
    if matches:
        return [{"title": title.strip(), "text": body.strip()} for title, body in matches if body.strip()]
    return [{"title": "Full material", "text": content}]


def _letters_from_indices(indices: List[int]) -> str:
    return ", ".join(OPTION_LABELS[i] for i in indices if 0 <= i < len(OPTION_LABELS))


def _slot_from_dict(data: dict) -> QuestionSlot:
        return QuestionSlot(
        question_number=int(data["question_number"]),
        chapter=int(data["chapter"]),
        chapter_title=data.get("chapter_title") or f"Chapter {data.get('chapter')}",
        target_difficulty=normalize_difficulty(data.get("target_difficulty")),
        answer_type=data.get("answer_type") or "single_correct",
        grade=data.get("grade") or "",
        subject=data.get("subject") or "",
    )


def _forbidden_stems_for_bank_generate(
    state: PaperState,
    slot: QuestionSlot,
    *,
    used_stems: List[str],
    approved: List[dict],
    rejected_log: List[dict],
    active_intent: Optional[dict],
) -> List[str]:
    avoidance = build_slot_avoidance_history(rejected_log, slot.question_number)
    existing = list(state.get("bank_duplicate_seed_questions") or []) + list(approved)
    return select_bank_batch_forbidden_stems(
        active_intent,
        used_stems=used_stems,
        rejected_stems=avoidance.get("rejected_stems") or [],
        existing_questions=existing,
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = f"""You are an expert exam-question writer.

HIERARCHY (must follow in this order):
Grade → Curriculum/chapter content → Cognitive difficulty → Question → Answer type

COGNITIVE DIFFICULTY DEFINITIONS (based on cognitive work, NOT length, vocabulary, arithmetic, or fancy wording):
{DIFFICULTY_DEFINITIONS}

RULES:
- Write exactly ONE question that satisfies the requested slot (grade, chapter, difficulty, answer type).
- Provide exactly five options labelled conceptually as A–E (return them as a 5-item list in order).
- For single_correct: exactly one option is correct. correct_indices has one integer.
- For multiple_correct: more than one option is correct. The question wording MUST clearly indicate that more than one answer may be selected. Every marked option must be defensibly correct; every unmarked option must be incorrect.
- Do not create artificial difficulty with confusing wording, tricks, excessive arithmetic, or out-of-syllabus content.
- Use grade-appropriate vocabulary, examples, reasoning complexity, and distractors.
- Phrase questions directly. NEVER start with "According to the excerpt", "As per the passage", or "Based on the text".
- Never write student-facing stems that mention the chapter, book, textbook, excerpt, source material, or what was listed/cited/stated there.
- Set topic and sub_topic from the chapter content.
- Explanation must justify the correct answer(s) and why the other options are wrong.

CONCEPT AND LEARNING OBJECTIVE:
- Identify the concept being tested and the learning objective (what the student must know or understand to answer).
- When assigned intent metadata is provided (topic, sub_topic, concept, objective, cognitive_form), use it. Do not invent a parallel intent.
- Direct recall is valid, especially for Easy items. Do not ban recall.

GROUNDING (selected book + chapter):
- Stay inside the selected book_id, grade, and chapter content for this slot.
- Allowed: directly taught content; straightforward application; comparison of taught concepts; a reasonable consequence of taught concepts.
- A related concept is allowed only if it can reasonably be derived from THIS chapter without unrelated external knowledge.
- Do not introduce unrelated concepts merely to make the item more interesting or more difficult.
- For a normal conceptual question: the underlying concept must be taught/supported by the selected chapter; options must be reasonable applications of that taught concept. An option does NOT need to appear verbatim in the textbook to be conceptually valid. Do not mark a valid concept application wrong only because that exact example was absent from a textbook list.
- Still forbid: unrelated outside-domain examples; unsupported specialist facts; hallucinated claims; concepts beyond this chapter's scope.

DO NOT COPY THE BOOK MECHANICALLY:
- Understand the concept, then write a fresh assessment question.
- Do not take a textbook sentence and add a question mark.
- Prefer natural assessment wording over near-verbatim copying.

SELF-CONTAINED STEMS:
- The stem must stand on its own.
- The selected chapter/book is INTERNAL grounding only. Never mention the chapter, book, textbook, excerpt, source material, or what was "listed/cited/stated" there in the student-facing stem.
- A normal question must be understandable and answerable without the student knowing which chapter was supplied to the generator.
- Do not use source-pointing language (including "according to the chapter/book/textbook", "listed/cited in the chapter").
- Do NOT write textbook-memory questions such as "Which examples were specifically listed in the chapter?"

CLEAR NATURAL CONSTRUCTION:
- Write clear, concise, grammatically unambiguous, professional, student-friendly stems.
- Avoid: unnecessarily long wording; artificial formality; difficult vocabulary used only to create difficulty; double negatives; hidden assumptions; gotcha wording; wordplay; misleading grammar; irrelevant details.
- Language must not be the source of difficulty. Grade and Difficulty are separate: a higher Grade does not mean a harder cognitive band.

SCENARIOS:
- Use a scenario only when it naturally supports the concept.
- Scenarios must be realistic, grade-appropriate, fully informative, and free of unnecessary storytelling.
- Do not force a scenario into every question.

NUMERICAL ITEMS:
- When calculation is naturally relevant, use realistic numbers and mathematically valid arithmetic.
- Do not add unnecessary arithmetic just to increase difficulty.
"""

BOOK_GROUNDED_RULES = """
BOOK-GROUNDED MODE:
Derive the question exclusively from the CHAPTER CONTENT provided for this slot.
- The underlying concept/fact must be taught or supported by that chapter content.
- Options and examples must be reasonable applications of the taught concept within this chapter's academic scope and Grade.
- An example/option does NOT have to appear verbatim in the chapter to be conceptually valid.
- Do NOT invent unsupported specialist facts, unrelated outside-domain examples, or concepts beyond this chapter.
- Later or earlier parts of the book that are not in this chapter content are out of scope.
- Do not require knowledge that is unrelated to the selected chapter.
- Related ideas are allowed only when they follow directly from this chapter's taught content.
- Never mention the chapter/book/textbook in the student-facing stem; chapter text is backend grounding only.
"""

TOPIC_ONLY_RULES = """
TOPIC-ONLY MODE (no uploaded learning material):
Stay strictly within the exam topic and curriculum objectives.
- Do not wander into unrelated chapters of the same subject.
- Set topic and sub_topic from the exam topic and objectives, not from an invented chapter.
"""

# Bank Batch only — clarifies Subject vs Topic vs Sub-topic (Final Paper unchanged).
BANK_BATCH_TOPIC_METADATA_RULES = """
BANK BATCH TOPIC / SUB-TOPIC METADATA (mandatory):
- Subject is the broad academic area (e.g. "Financial Literacy"). It is NOT the question topic field.
- topic must be a specific concept drawn from the selected chapter content.
- sub_topic must be a more specific concept or section under that topic.
- topic must NOT equal Subject (do not copy the Subject label into topic).
- topic must NOT be a generic label such as "Grade 5", "Chapter 1", or the chapter title alone.
- Derive topic and sub_topic from the chapter content provided for this slot.

Examples of valid patterns (illustrative only — use concepts from THIS chapter):
- Subject = Financial Literacy → topic = Money, sub_topic = Barter System
- Subject = Financial Literacy → topic = Banking, sub_topic = Savings Accounts
- Subject = Financial Literacy → topic = Saving, sub_topic = Saving for Future Goals
- Subject = Financial Literacy → topic = Investing, sub_topic = Compound Interest
Other valid topic examples when present in the chapter: Functions of Money, Budgeting, Needs vs Wants, Simple Interest.
"""

# Bank Batch only — misconception-based distractors (Final Paper unchanged).
BANK_BATCH_DISTRACTOR_RULES = """
BANK BATCH DISTRACTOR CONSTRUCTION (mandatory):
Build options using this process:
1) Identify the concept from the chapter content.
2) State the correct reasoning that yields the answer.
3) List likely Grade-appropriate student misconceptions for that concept.
4) Write wrong options from those misconceptions (not from jokes or unrelated facts).

Wrong options (distractors) must be:
- plausible to a student who partially understands the chapter
- conceptually relevant to the same topic
- Grade-appropriate
- grammatically parallel to the correct option(s)
- similar in length and specificity
- clearly wrong once the taught concept is applied correctly

Avoid:
- joke-like or absurd options
- obviously unrelated statements
- extreme claims that are trivially false
- duplicate or rephrased versions of another option
- options that are also defensibly correct

Illustrative misconception patterns (examples of the principle — derive from THIS chapter, do not force these finance examples if irrelevant):
- Numerical: wrong base for a percentage; forgetting the time period; confusing principal with interest; mixing simple vs compound interest
- Conceptual: confusing related chapter terms with each other; swapping cause and effect; applying a definition to the wrong scenario

SINGLE CORRECT: exactly one defensible option. The other four must be plausible misconceptions of THIS concept, not fillers.
MULTIPLE CORRECT: 2–4 independently assessable correct options. Students must judge each option on its own. Do not write options that logically reveal another option. Do not make all correct options near-paraphrases.
EASY DISTRACTORS: plausible, not deceptively sophisticated. Do not raise cognitive difficulty through harder distractors.
"""

NFO_OPTION_DISTRACTOR_RULES = """
OPTION AND DISTRACTOR QUALITY (mandatory):
Single Correct: exactly five options; exactly one defensible correct answer; four incorrect options that are plausible, relevant, and meaningful.
Multiple Correct: exactly five options; 2–4 correct; every option independently assessable; the defensible set must match the answer key.

Build distractors as: concept → likely student misconception or error → option.
Do not build: concept → random alternative.

Preferred incorrect-option types: common misconception; confusion between related concepts or similar terms; incorrect application; reversed cause and effect; partially correct interpretation; realistic calculation error (wrong operation, wrong quantity, intermediate value, misapplied formula) when the item is numerical.
Do not force numerical error distractors on non-numerical items.

Do not write distractors that are random, absurd, irrelevant, obviously false, from an unrelated category, or filler to reach five options.
Do not create a second defensible correct answer on Single Correct.
On Multiple Correct, avoid options that logically reveal another option, obviously similar correct wording, unrelated incorrect options, or an ambiguous set.

Options should be reasonably comparable in grammar, specificity, complexity, terminology, detail, and natural length. Naturalness matters more than forced equal length.
The correct answer must not stand out only because it is much longer/shorter, the only grammatical option, a stem repeat, the only technical option, the only qualifier, or the only positive/negative statement without a conceptual reason.

Do not shuffle or balance answer letters. Do not raise Easy/Medium/Difficult by making distractors trickier.
"""

# Bank Batch only — Easy generation calibration (validator mapping unchanged).
BANK_BATCH_EASY_CALIBRATION_RULES = """
BANK BATCH EASY CALIBRATION (mandatory when target difficulty is Easy):
Write an Easy item only. Cognitive work must stay in the Easy band (validator still maps totals 8–12 = Easy; do not game the label).

Require:
- one primary concept only
- familiar/direct context from the chapter
- recall, recognition, basic comprehension, or straightforward one-step application
- at most 0–1 meaningful reasoning step
- information explicit in the stem and/or taught material (minimal interpretation)
- correct option identifiable without evaluation of competing strategies
- no meaningful multi-concept integration

Do NOT write Easy items that:
- combine multiple concepts
- require comparison across several judgments
- use multi-step scenarios
- need inference from several facts
- ask for evaluation or the “best decision”
- require interpretation plus calculation
- use non-routine transfer

Quality still matters: Grade-appropriate language; plausible misconception distractors (not jokes, not giveaways). Stay Easy without becoming trivial.
"""

# Compact Easy slot contract echoed in the user prompt (no extra LLM call).
BANK_BATCH_EASY_SLOT_CONTRACT = """
EASY SLOT CONTRACT (mandatory — known before generation; validators still apply unchanged):
- Correct Grade hard constraint; selected chapter scope only
- Assigned concept/objective mandatory; one primary concept only
- 0–1 meaningful reasoning step; recall/basic comprehension/direct one-step application
- No multi-concept integration
- Avoid subjective best / most appropriate / most reasonable wording unless an explicit objective criterion makes exactly one answer defensible
- Exactly 5 options; Single = exactly 1 defensible answer; Multiple = 2–4 defensible answers
- Distractors from plausible misconceptions/errors of the taught concept
- No chapter/book/textbook wording in the student-facing stem
- Avoid forbidden/duplicate opening stem patterns
"""

# Compact Difficult slot contract echoed in the user prompt (no extra LLM call).
BANK_BATCH_DIFFICULT_SLOT_CONTRACT = """
DIFFICULT SLOT CONTRACT (mandatory — known before generation; validators still apply unchanged; Difficult = score 19–24):
- Require genuine analysis, inference, evaluation, and/or transfer — not recall padded with a long story
- Require multiple connected reasoning steps
- Recall alone is insufficient; direct one-step application is insufficient
- Simple constraint matching (limits/fees/hours alone) is insufficient
- Simple comparison alone is insufficient
- Scenario length does not equal difficulty; complexity must come from reasoning, not wording/vocabulary
- Where naturally supported by the selected chapter, integrate 2+ connected concepts
- One concept is allowed only when it truly needs deep multi-step reasoning
- Do not force unrelated concept combinations merely to look Difficult
- Do not use obscure, trick, or confusing wording to manufacture difficulty
- No chapter/book/textbook wording in the student-facing stem
"""

BLIND_SOLVER_SYSTEM = """You are an independent exam-question solver. You have NOT seen the answer key.

TASK (decisions only; no explanations):
1. Read the question stem and all five options (A-E).
2. Using ONLY the stem, options, and any chapter content provided, determine which option(s) are correct.
3. For EACH option A-E, set defensible true or false. Do not write a reason.
4. Set information_sufficient true only if the stem uniquely determines the answer.
5. Set arithmetic_consistent from numerical claims in the stem and options.
6. Set no_unsupported_claims false for absolute or misleading claims not supported by the provided material (e.g. "guaranteed returns", "always grows faster", "banks guarantee wealth").
7. Specialized terminology grounding: set terminology_grounded true only if specialized terms/phrases in the stem are explicitly present in the provided chapter excerpt.

RULES:
- Do NOT assume any option is correct. Solve from first principles.
- For Single Correct: exactly ONE option should be defensible.
- For Multiple Correct: the question wording should indicate multiple answers; at least two should be defensible.
- IMPORTANT (Single Correct defensibility): mark an option defensible only if it fully answers the full objective of the stem. Directionally true but incomplete options are NOT defensible.
- When the stem tests a concept taught by the supplied material, apply the taught definition/principle to the options. Do NOT require an option or example to appear verbatim in the grounding excerpt merely to be defensible.
- This is concept application of the supplied chapter concept — not permission to use unrelated external specialist knowledge.
- The concept itself must be supported by the supplied chapter grounding; unsupported terminology/facts should still fail.
- If the stem lacks information to uniquely determine the answer, set information_sufficient to false.
- If any number (percentage, amount, calculation) is inconsistent between stem, options, or implied logic, set arithmetic_consistent to false.
- If the question makes unsupported absolute financial/factual claims, set no_unsupported_claims to false.
- If terminology_grounded is false, treat the item as invalid (specialized terminology not supported by the chapter excerpt).

Return structured JSON only. No explanations. No reasoning text. Do not describe the solving process."""

VALIDATOR_SYSTEM = f"""You are an independent exam-question validator. You did not write the question.

Score the question on eight cognitive criteria from 1 to 3. Do NOT compute a total.
Do NOT guess or report an overall Easy/Medium/Difficult label.

{VALIDATOR_CRITERION_RUBRIC}

Also judge quality as booleans:
- content_valid: tests curriculum-appropriate content for the given grade and chapter
- answer_valid: marked answers are actually correct; unmarked options are incorrect
- grade_appropriate: vocabulary, sentence complexity, assumed knowledge, scenario maturity, and numerical demand fit the stated Grade. Do NOT treat a higher Grade as requiring a harder Easy/Medium/Difficult cognitive band.
- distractors_ok: incorrect options represent realistic, grade-appropriate misconceptions. Reject if distractors are obviously absurd, irrelevant, nonsensical, or trivially eliminated without understanding the concept. Put a short diagnostic in reasons when possible: irrelevant distractor; absurd/obvious distractor; another defensible answer; answer-style clue; weak misconception basis; option not independently assessable. Do not expose chain-of-thought.
- unambiguous: only one defensible reading of the question
- language_clear: clear, grade-appropriate language without trick wording; difficulty must come from reasoning, not harder vocabulary
- grounded_in_material: true if chapter content is provided and the underlying concept/fact is supported by that material (options may be reasonable concept applications that do not appear word-for-word in the chapter); true if no chapter content was provided. False if the concept itself is unsupported/hallucinated or outside the selected material.
- explanation_valid: explanation correctly defends the answers AND is consistent with the stem and options
- concept_relevant: the item tests a concept that belongs to the selected chapter / assigned intent
- no_unrelated_external_knowledge: answering does not require unrelated knowledge from outside the selected chapter
- stem_self_contained: the stem stands alone and does not lean on unnecessary chapter/page/book/material references
- natural_assessment_wording: a genuine assessment question, not a textbook sentence with a question mark
- scenario_focused: true if there is no scenario, or the scenario is realistic, sufficient, relevant, and free of unnecessary storytelling; false if the scenario is padded, missing information, or age-inappropriate
- options_independently_assessable: each option can be judged on its own; false if one option logically reveals another
- option_style_balanced: the keyed answer does not stand out from style/length/grammar clues alone
- misconception_based_distractors: wrong options follow from the tested concept (misconception/error), not random alternatives. For Easy items, distractors may be plausible without being deceptively sophisticated.

For Multiple Correct questions, do NOT fail the item merely because more than one option is correct.
For Single Correct questions, fail answer_valid if more than one option is defensible.

Return structured scores and flags. Put concise rejection reasons in `reasons` when any check fails.
Do not include chain-of-thought.
"""

# Bank Batch core phase: identical quality rubric without explanation_valid.
CORE_VALIDATOR_SYSTEM = f"""You are an independent exam-question validator. You did not write the question.
This is a CORE validation pass: there is NO explanation yet. Do NOT judge explanation quality.

Score the question on eight cognitive criteria from 1 to 3. Do NOT compute a total.
Do NOT guess or report an overall Easy/Medium/Difficult label.

{VALIDATOR_CRITERION_RUBRIC}

Also judge quality as booleans:
- content_valid: tests curriculum-appropriate content for the given grade and chapter
- answer_valid: marked answers are actually correct; unmarked options are incorrect
- grade_appropriate: vocabulary, sentence complexity, assumed knowledge, scenario maturity, and numerical demand fit the stated Grade. Do NOT treat a higher Grade as requiring a harder Easy/Medium/Difficult cognitive band.
- distractors_ok: incorrect options represent realistic, grade-appropriate misconceptions. Reject if distractors are obviously absurd, irrelevant, nonsensical, or trivially eliminated without understanding the concept. Put a short diagnostic in reasons when possible: irrelevant distractor; absurd/obvious distractor; another defensible answer; answer-style clue; weak misconception basis; option not independently assessable. Do not expose chain-of-thought.
- unambiguous: only one defensible reading of the question
- language_clear: clear, grade-appropriate language without trick wording; difficulty must come from reasoning, not harder vocabulary
- grounded_in_material: true if chapter content is provided and the underlying concept/fact is supported by that material (options may be reasonable concept applications that do not appear word-for-word in the chapter); true if no chapter content was provided. False if the concept itself is unsupported/hallucinated or outside the selected material.
- concept_relevant: the item tests a concept that belongs to the selected chapter / assigned intent
- no_unrelated_external_knowledge: answering does not require unrelated knowledge from outside the selected chapter
- stem_self_contained: the stem stands alone and does not lean on unnecessary chapter/page/book/material references
- natural_assessment_wording: a genuine assessment question, not a textbook sentence with a question mark
- scenario_focused: true if there is no scenario, or the scenario is realistic, sufficient, relevant, and free of unnecessary storytelling; false if the scenario is padded, missing information, or age-inappropriate
- options_independently_assessable: each option can be judged on its own; false if one option logically reveals another
- option_style_balanced: the keyed answer does not stand out from style/length/grammar clues alone
- misconception_based_distractors: wrong options follow from the tested concept (misconception/error), not random alternatives. For Easy items, distractors may be plausible without being deceptively sophisticated.

For Multiple Correct questions, do NOT fail the item merely because more than one option is correct.
For Single Correct questions, fail answer_valid if more than one option is defensible.

Return structured scores and flags. Put concise rejection reasons in `reasons` when any check fails.
Do not include chain-of-thought.
"""

EXPLANATION_GENERATOR_SYSTEM = """You write a short, Grade-appropriate explanation for an already-validated exam question.

RULES:
- Defend ONLY the given correct answer(s). Do not change or suggest different answers.
- Do not rewrite the stem or options.
- Stay grounded in the taught concept from the supplied chapter material when provided.
- Do not invent unsupported facts.
- Do not mention chapter/book/textbook/page/generation-process wording.
- Be clear and concise. No chain-of-thought dump.
"""

EXPLANATION_VALIDATOR_SYSTEM = """You validate ONLY the explanation for an exam question whose stem, options, and answer key are already fixed and validated.

Check:
- explanation_valid: the explanation correctly defends the stored correct answer(s), is consistent with the stem and options, is Grade-appropriate, grounded in the taught concept when material is provided, does not invent unsupported facts, and does not unnecessarily mention chapter/book/textbook/generation context.

Return explanation_valid and concise machine-readable reasons when invalid.
Do not include chain-of-thought.
Do not re-score cognitive difficulty.
Do not change the answer key.
"""


# ---------------------------------------------------------------------------
# Node 1 — Prepare blueprint + chapter chunks
# ---------------------------------------------------------------------------

async def prepare_blueprint(state: PaperState) -> dict:
    """Build question slots and chapter chunks. No LLM call."""
    grade = (state.get("grade") or "").strip()
    subject = (state.get("subject") or state.get("topic") or "").strip()
    raw_preset = state.get("blueprint_preset")

    chapters = parse_book_chapters(state.get("book_chapters"), state.get("book_content"))
    book_grounded = bool(chapters)
    titles = [ch["title"] for ch in chapters] if chapters else None
    if book_grounded:
        validate_chapter_selection(raw_preset, len(chapters))

    preset = build_effective_preset(raw_preset, titles)
    slots = build_slots(preset, grade=grade, subject=subject, chapter_titles=titles)

    chapter_chunks: Dict[str, List[str]] = {}
    for i, ch in enumerate(chapters, start=1):
        chunks = chunk_chapter_text(ch["text"])
        chapter_chunks[str(i)] = chunks
        logger.info(
            f"Chapter {i} '{ch['title']}': {len(ch['text'])} chars → {len(chunks)} chunk(s) "
            f"(chunk_size={CHAPTER_CHUNK_SIZE})"
        )

    logger.info(
        f"Prepared {len(slots)} slots; book_grounded={book_grounded}; "
        f"grade={grade!r}; chapters={list(preset['chapter_difficulty'].keys())}"
    )
    return {
        "slots": [s.to_dict() for s in slots],
        "effective_preset": preset,
        "chapter_chunks": chapter_chunks,
        "book_grounded": book_grounded,
        "approved": [],
        "failed_slots": [],
        "used_stems": [],
        "rejected_with_feedback": [],
    }


# ---------------------------------------------------------------------------
# Per-slot generate + independent validate
# ---------------------------------------------------------------------------

async def _generate_for_slot(
    slot: QuestionSlot,
    state: PaperState,
    chapter_excerpt: str,
    rejection_feedback: Optional[str],
    diversity_guidance: Optional[str] = None,
    soft_coverage_hints: Optional[str] = None,
    intent_guidance: Optional[str] = None,
    novelty_brief: Optional[str] = None,
    forbidden_stems: Optional[List[str]] = None,
    cost_diagnostics: Optional[dict] = None,
) -> Optional[dict]:
    book_grounded = bool(state.get("book_grounded") and chapter_excerpt)
    system = GENERATOR_SYSTEM + NFO_OPTION_DISTRACTOR_RULES + (
        BOOK_GROUNDED_RULES if book_grounded else TOPIC_ONLY_RULES
    )
    bank_batch_mode = bool(state.get("bank_batch_mode"))
    if bank_batch_mode:
        system = system + BANK_BATCH_TOPIC_METADATA_RULES + BANK_BATCH_DISTRACTOR_RULES
        if normalize_difficulty(slot.target_difficulty) == "easy":
            system = system + BANK_BATCH_EASY_CALIBRATION_RULES
    if forbidden_stems is not None:
        forbidden = [s for s in forbidden_stems if str(s).strip()]
    else:
        forbidden = state.get("used_stems") or []
        forbidden = forbidden[-40:]
    forbidden_str = ", ".join(f'"{s}"' for s in forbidden) if forbidden else "none"
    feedback_block = ""
    if rejection_feedback:
        feedback_block = (
            "\nPREVIOUS ATTEMPT WAS REJECTED. Fix these issues while keeping the SAME "
            f"chapter, target difficulty, and answer type:\n{rejection_feedback}\n"
        )

    chapter_block = ""
    if chapter_excerpt:
        chapter_block = (
            f"\n--- CHAPTER CONTENT (use this material; later/other chapters are out of scope) ---\n"
            f"{chapter_excerpt}\n--- END CHAPTER CONTENT ---\n"
        )

    objectives = [str(o).strip() for o in (state.get("curriculum_objectives") or []) if str(o).strip()]
    objectives_block = ""
    if objectives:
        objectives_block = "Curriculum objectives:\n" + "\n".join(f"- {o}" for o in objectives) + "\n"

    answer_rule = (
        "exactly ONE correct option"
        if slot.answer_type == "single_correct"
        else "MORE THAN ONE correct option; say that multiple answers may be selected"
    )
    topic_meta_block = ""
    if bank_batch_mode:
        topic_meta_block = (
            "\nTOPIC / SUB-TOPIC (Bank Batch): "
            "Subject is the broad academic area only. "
            "Set `topic` to a specific concept from the chapter content — "
            "it must NOT equal Subject and must NOT be a generic label "
            "(e.g. Grade 5, Chapter 1). "
            "Set `sub_topic` to a more specific concept/section under that topic.\n"
            "DISTRACTORS (Bank Batch): Derive wrong options from realistic "
            "Grade-appropriate misconceptions of the taught concept; "
            "do not use joke-like or unrelated fillers. "
            "Build distractors around the novel question task in this attempt.\n"
        )
    diversity_block = ""
    if bank_batch_mode and diversity_guidance:
        diversity_block = diversity_guidance
    coverage_block = ""
    if bank_batch_mode and soft_coverage_hints:
        coverage_block = soft_coverage_hints
    intent_block = ""
    if bank_batch_mode and intent_guidance:
        intent_block = intent_guidance
    novelty_block = ""
    if bank_batch_mode and novelty_brief:
        novelty_block = novelty_brief
    easy_cal_block = ""
    if bank_batch_mode and normalize_difficulty(slot.target_difficulty) == "easy":
        easy_cal_block = (
            "\nEASY CALIBRATION (Bank Batch): One primary concept; familiar/direct context; "
            "recall/recognition/basic comprehension or one-step application; 0–1 reasoning step. "
            "Avoid multi-concept, multi-step, evaluation/best-decision, inference-from-several-facts, "
            "and interpretation-plus-calculation items. Keep distractors plausible and Grade-appropriate.\n"
            f"{BANK_BATCH_EASY_SLOT_CONTRACT}"
        )
    difficult_cal_block = ""
    if bank_batch_mode and normalize_difficulty(slot.target_difficulty) == "difficult":
        difficult_cal_block = (
            "\nDIFFICULT CALIBRATION (Bank Batch): Raise genuine reasoning demand. "
            "Multiple connected steps; analysis/inference/evaluation/transfer. "
            "Length and vocabulary do not create Difficult. "
            "Integrate connected chapter concepts only when natural.\n"
            f"{BANK_BATCH_DIFFICULT_SLOT_CONTRACT}"
        )
    user_prompt = f"""Generate one exam question for this slot.

Book ID: {state.get('book_id') or 'not specified'}
Grade: {slot.grade or 'not specified'} (hard constraint; independent of difficulty)
Subject: {slot.subject}
Exam topic: {state.get('topic') or slot.subject}
{objectives_block}Question number: {slot.question_number}
Chapter: {slot.chapter} — {slot.chapter_title}
Target cognitive difficulty (independent of grade): {slot.target_difficulty.upper()}
Answer type: {slot.answer_type} ({answer_rule})
Language: {state.get('language') or 'en'}
Options: exactly 5 (A–E)
{topic_meta_block}{easy_cal_block}{difficult_cal_block}{intent_block}{novelty_block}{diversity_block}{coverage_block}
Forbidden opening stems: [{forbidden_str}]
{feedback_block}{chapter_block}
Follow the cognitive difficulty definition for {slot.target_difficulty.upper()} exactly.
{format_slot_difficulty_guidance(slot.target_difficulty)}
Keep Grade "{slot.grade or 'unspecified'}" as a hard constraint on vocabulary, assumed knowledge, scenarios, and numerical demand.
Do not raise cognitive difficulty just because the Grade is higher.
Write a self-contained assessment question from the concept and learning objective; do not mechanically copy the chapter.
{"Do NOT write an explanation. Produce only the question stem, options, correct answer/indices, and topic metadata." if bank_batch_mode else "Include a clear explanation defending the correct answer(s)."}
"""

    output_schema = CoreGeneratedQuestion if bank_batch_mode else SlotGeneratedQuestion

    difficulty_contract = easy_cal_block + difficult_cal_block
    if slot.target_difficulty:
        difficulty_contract += format_slot_difficulty_guidance(slot.target_difficulty)
    structural_rules = (
        topic_meta_block
        + objectives_block
        + f"Forbidden opening stems: [{forbidden_str}]\n"
        + diversity_block
        + coverage_block
    )
    intent_objective_form = intent_block + novelty_block

    def _generator_composition() -> dict:
        return build_prompt_composition(
            system_prompt=system,
            user_prompt=user_prompt,
            grounding_text=chapter_excerpt or "",
            static_system_instructions=system,
            difficulty_contract=difficulty_contract,
            structural_answer_rules=structural_rules,
            intent_objective_form=intent_objective_form,
            retry_feedback=feedback_block,
        )

    async def _call_generator(max_tokens: int, *, llm_stage: str) -> dict:
        result = await _invoke_structured(
            system,
            user_prompt,
            state.get("generator_model"),
            output_schema,
            max_tokens=max_tokens,
            temperature=0.7,
            llm_stage=llm_stage,
            cost_diagnostics=cost_diagnostics,
            prompt_composition=_generator_composition(),
            bank_batch_mode=bank_batch_mode,
        )
        data = result.model_dump()
        options = list(data.get("options") or [])
        if len(options) > 5:
            options = options[:5]
        data["options"] = options
        if bank_batch_mode:
            # Core phase: never carry a generated explanation forward.
            data["explanation"] = ""
        return data

    initial_max_tokens = (
        BANK_BATCH_GENERATOR_MAX_TOKENS
        if bank_batch_mode
        else GENERATOR_MAX_TOKENS
    )
    # Bank Batch already starts at 4096; a same-budget length retry is wasted.
    allow_length_retry = (not bank_batch_mode) and (
        GENERATOR_LENGTH_RETRY_MAX_TOKENS > initial_max_tokens
    )

    try:
        data = await _call_generator(
            initial_max_tokens, llm_stage=LLM_STAGE_CORE_GENERATION
        )
        if cost_diagnostics is not None:
            tag_last_llm_call(cost_diagnostics, outcome="core_produced")
        return data
    except Exception as first_err:
        if not is_structured_output_length_error(first_err) or not allow_length_retry:
            logger.error(f"Generator failed for slot {slot.question_number}: {first_err}")
            if cost_diagnostics is not None:
                tag_last_llm_call(cost_diagnostics, outcome="generation_failed")
            return None
        # Final Paper only: exactly one recovery at a larger completion budget.
        if cost_diagnostics is not None:
            tag_last_llm_call(cost_diagnostics, outcome="length_recovery_discarded")
            cost_diagnostics["length_limit_retry_attempted"] = (
                int(cost_diagnostics.get("length_limit_retry_attempted") or 0) + 1
            )
            cost_diagnostics["length_limit_retry_initial_tokens"] = GENERATOR_MAX_TOKENS
            cost_diagnostics["length_limit_retry_retry_tokens"] = (
                GENERATOR_LENGTH_RETRY_MAX_TOKENS
            )
        logger.warning(
            f"Generator length-limit for slot {slot.question_number}; "
            f"retrying once with max_tokens={GENERATOR_LENGTH_RETRY_MAX_TOKENS}"
        )
        try:
            data = await _call_generator(
                GENERATOR_LENGTH_RETRY_MAX_TOKENS,
                llm_stage=LLM_STAGE_LENGTH_RECOVERY,
            )
            if cost_diagnostics is not None:
                tag_last_llm_call(cost_diagnostics, outcome="core_produced")
                cost_diagnostics["length_limit_retry_succeeded"] = (
                    int(cost_diagnostics.get("length_limit_retry_succeeded") or 0) + 1
                )
            return data
        except Exception as retry_err:
            if cost_diagnostics is not None:
                tag_last_llm_call(cost_diagnostics, outcome="generation_failed")
                cost_diagnostics["length_limit_retry_failed"] = (
                    int(cost_diagnostics.get("length_limit_retry_failed") or 0) + 1
                )
            logger.error(
                f"Generator failed for slot {slot.question_number} "
                f"after length-limit retry: {retry_err}"
            )
            return None


def _chapter_short_term_source(
    state: PaperState,
    slot: QuestionSlot,
    excerpt: str,
) -> str:
    """Full selected-chapter text for abbreviation extraction (retrieval only)."""
    chunks = (state.get("chapter_chunks") or {}).get(str(slot.chapter)) or []
    joined = "\n".join(str(c) for c in chunks if str(c).strip())
    return joined.strip() or (excerpt or "")


def _bank_batch_validation_excerpt(
    state: PaperState,
    slot: QuestionSlot,
    generated: dict,
    chunks: Sequence[Any],
    original_index: Optional[int],
    excerpt: str,
    cost_diagnostics: Optional[dict],
) -> str:
    """Re-select same-chapter evidence chunk after generation. Bank Batch only."""
    if not state.get("bank_batch_mode"):
        return excerpt or ""
    texts = [str(c or "") for c in (chunks or [])]
    selection = select_validation_chunk_for_generated(
        texts,
        generated,
        original_index=original_index,
        chapter_term_source=_chapter_short_term_source(state, slot, excerpt or ""),
    )
    if not selection.get("excerpt") and excerpt:
        selection["excerpt"] = excerpt
    record_validation_chunk_reselection(cost_diagnostics, selection)
    return str(selection.get("excerpt") or excerpt or "")


def _last_logged_blind_tokens(
    diagnostics: Optional[dict],
) -> Tuple[Optional[int], Optional[int]]:
    if not diagnostics:
        return None, None
    log = diagnostics.get("llm_call_log") or []
    for entry in reversed(log):
        if entry.get("stage") != LLM_STAGE_BLIND_SOLVER:
            continue
        completion = entry.get("output_tokens")
        if completion is None:
            completion = entry.get("completion_tokens")
        reasoning = entry.get("reasoning_tokens")
        return (
            int(completion) if completion is not None else None,
            int(reasoning) if reasoning is not None else None,
        )
    return None, None


async def _blind_solve(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
    *,
    cost_diagnostics: Optional[dict] = None,
) -> Optional[BlindSolverOutput] | BlindSolverUnavailable:
    """Stage 1: solve without seeing the answer key, explanation, or target difficulty."""
    source_text = chapter_excerpt or ""
    if state.get("bank_batch_mode"):
        source_text = select_blind_solver_source_snippet(
            chapter_excerpt or "",
            str(generated.get("question") or ""),
            list(generated.get("options") or []),
            term_source_text=_chapter_short_term_source(
                state, slot, chapter_excerpt or ""
            ),
            diagnostics=cost_diagnostics,
            stage="blind_solver",
        )
    chapter_block = ""
    if source_text:
        chapter_block = (
            f"\n--- SOURCE SNIPPET (terminology check only; solve from the stem) ---\n"
            f"{source_text}\n--- END SOURCE SNIPPET ---\n"
            if state.get("bank_batch_mode")
            else (
                f"\n--- CHAPTER CONTENT ---\n{source_text}\n--- END CHAPTER CONTENT ---\n"
            )
        )
    answer_type_hint = (
        "Single Correct (exactly one option is correct)"
        if slot.answer_type == "single_correct"
        else "Multiple Correct (more than one option may be correct)"
    )
    user_prompt = f"""Solve this exam question independently.

Grade: {slot.grade or 'not specified'}
Answer type: {answer_type_hint}

Question: {generated.get('question')}
Options:
{json.dumps(generated.get('options') or [], indent=2)}
{chapter_block}
Set independently_derived_indices and defensible for A-E. Set information_sufficient, arithmetic_consistent, no_unsupported_claims, and terminology_grounded. JSON only.
"""
    composition = build_prompt_composition(
        system_prompt=BLIND_SOLVER_SYSTEM,
        user_prompt=user_prompt,
        grounding_text=source_text or "",
        static_system_instructions=BLIND_SOLVER_SYSTEM,
    )

    def _bump_blind_retry(field: str) -> None:
        if cost_diagnostics is None:
            return
        cost_diagnostics[field] = int(cost_diagnostics.get(field) or 0) + 1

    def _record_ok() -> None:
        comp, reason = _last_logged_blind_tokens(cost_diagnostics)
        record_blind_solver_outcome(
            cost_diagnostics,
            success=True,
            length_failure=False,
            completion_tokens=comp,
            reasoning_tokens=reason,
        )

    def _record_fail(exc: BaseException) -> None:
        comp, reason = parse_completion_usage_from_exc(exc)
        if comp is None and reason is None:
            comp, reason = _last_logged_blind_tokens(cost_diagnostics)
        record_blind_solver_outcome(
            cost_diagnostics,
            success=False,
            length_failure=is_structured_output_length_error(exc),
            completion_tokens=comp,
            reasoning_tokens=reason,
        )

    async def _invoke_blind(max_tokens: int) -> BlindSolverOutput:
        return await _invoke_structured(
            BLIND_SOLVER_SYSTEM,
            user_prompt,
            state.get("reviewer_model") or state.get("generator_model"),
            BlindSolverOutput,
            max_tokens=max_tokens,
            temperature=0.2,
            llm_stage=LLM_STAGE_BLIND_SOLVER,
            cost_diagnostics=cost_diagnostics,
            prompt_composition=composition,
            bank_batch_mode=bool(state.get("bank_batch_mode")),
        )

    try:
        result = await _invoke_blind(max_tokens=2048)
        _record_ok()
        return result
    except Exception as first_err:
        logger.error(
            f"Blind solver failed for slot {slot.question_number}: {first_err}"
        )
        _record_fail(first_err)
        if not is_structured_output_length_error(first_err) or not state.get(
            "bank_batch_mode"
        ):
            return None
        _bump_blind_retry("blind_length_retry_attempted")
        logger.warning(
            f"Blind solver length-limit for slot {slot.question_number}; "
            f"retrying once with max_tokens={BLIND_LENGTH_RETRY_MAX_TOKENS}"
        )
        try:
            result = await _invoke_blind(max_tokens=BLIND_LENGTH_RETRY_MAX_TOKENS)
            _bump_blind_retry("blind_length_retry_success")
            _record_ok()
            return result
        except Exception as retry_err:
            _bump_blind_retry("blind_length_retry_failed")
            logger.error(
                f"Blind solver failed for slot {slot.question_number} "
                f"after length-limit retry: {retry_err}"
            )
            _record_fail(retry_err)
            return BlindSolverUnavailable(
                blind_validator_unavailable_reason(retry_err)
            )


async def _validate_cognitive_quality(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
    *,
    cost_diagnostics: Optional[dict] = None,
) -> Tuple[dict, dict]:
    """Stage 2: cognitive scoring + quality flags (receives the full answer key).

    Bank Batch core phase omits explanation from the prompt and does not ask for
    explanation_valid; explanation is validated later in a dedicated pass.
    """
    bank_core = bool(state.get("bank_batch_mode")) and not str(
        generated.get("explanation") or ""
    ).strip()
    source_text = chapter_excerpt or ""
    if state.get("bank_batch_mode") and source_text:
        probe_parts = [
            str(generated.get("question") or ""),
            str(generated.get("topic") or ""),
            str(generated.get("sub_topic") or ""),
        ]
        if not bank_core:
            probe_parts.append(str(generated.get("explanation") or ""))
        source_text = select_cognitive_source_window(
            source_text,
            " ".join(probe_parts),
            term_source_text=_chapter_short_term_source(
                state, slot, chapter_excerpt or ""
            ),
            diagnostics=cost_diagnostics,
            stage="cognitive_quality",
        )
    chapter_block = ""
    if source_text:
        chapter_block = (
            f"\n--- CHAPTER CONTENT ---\n{source_text}\n--- END CHAPTER CONTENT ---\n"
        )
    explanation_block = ""
    if not bank_core:
        explanation_block = f"Explanation: {generated.get('explanation')}\n"
    user_prompt = f"""Validate this exam question. Do not infer a requested difficulty label.
Grade and Difficulty are separate constraints. Judge grade_appropriate against Grade only.
{"This is a CORE validation pass: ignore explanation quality." if bank_core else ""}

Book ID: {state.get('book_id') or 'not specified'}
Grade: {slot.grade or 'not specified'}
Subject: {slot.subject}
Chapter: {slot.chapter} — {slot.chapter_title}
Answer type (requested): {slot.answer_type}

Question: {generated.get('question')}
Options:
{json.dumps(generated.get('options') or [], indent=2)}
Marked correct_indices (0-based): {generated.get('correct_indices')}
Stated answer: {generated.get('answer')}
{explanation_block}Topic / sub-topic: {generated.get('topic')} / {generated.get('sub_topic')}
{chapter_block}
Score the eight criteria 1-3. Set the quality booleans. Do not total the scores.
"""
    composition = build_prompt_composition(
        system_prompt=CORE_VALIDATOR_SYSTEM if bank_core else VALIDATOR_SYSTEM,
        user_prompt=user_prompt,
        grounding_text=source_text or "",
        static_system_instructions=CORE_VALIDATOR_SYSTEM if bank_core else VALIDATOR_SYSTEM,
    )

    def _bump_cognitive_retry(field: str) -> None:
        if cost_diagnostics is None:
            return
        cost_diagnostics[field] = int(cost_diagnostics.get(field) or 0) + 1

    async def _invoke_cognitive(max_tokens: int) -> Tuple[dict, dict]:
        if bank_core:
            result: CoreIndependentValidatorOutput = await _invoke_structured(
                CORE_VALIDATOR_SYSTEM,
                user_prompt,
                state.get("reviewer_model") or state.get("generator_model"),
                CoreIndependentValidatorOutput,
                max_tokens=max_tokens,
                temperature=0.2,
                llm_stage=LLM_STAGE_COGNITIVE_QUALITY,
                cost_diagnostics=cost_diagnostics,
                prompt_composition=composition,
                bank_batch_mode=bool(state.get("bank_batch_mode")),
            )
            flags = result.model_dump()
            scores = flags.pop("criterion_scores")
            # explanation_valid is deferred; do not invent a pass.
            flags.pop("explanation_valid", None)
            return scores, flags
        result_full: IndependentValidatorOutput = await _invoke_structured(
            VALIDATOR_SYSTEM,
            user_prompt,
            state.get("reviewer_model") or state.get("generator_model"),
            IndependentValidatorOutput,
            max_tokens=max_tokens,
            temperature=0.2,
            llm_stage=LLM_STAGE_COGNITIVE_QUALITY,
            cost_diagnostics=cost_diagnostics,
            prompt_composition=composition,
            bank_batch_mode=bool(state.get("bank_batch_mode")),
        )
        flags = result_full.model_dump()
        scores = flags.pop("criterion_scores")
        return scores, flags

    try:
        return await _invoke_cognitive(COGNITIVE_MAX_TOKENS)
    except Exception as first_err:
        if not is_structured_output_length_error(first_err) or not state.get(
            "bank_batch_mode"
        ):
            logger.error(
                f"Cognitive validator failed for slot {slot.question_number}: {first_err}"
            )
            return cognitive_validator_unavailable_payload(first_err)
        _bump_cognitive_retry("cognitive_length_retry_attempted")
        logger.warning(
            f"Cognitive validator length-limit for slot {slot.question_number}; "
            f"retrying once with max_tokens={COGNITIVE_LENGTH_RETRY_MAX_TOKENS}"
        )
        try:
            scores, flags = await _invoke_cognitive(COGNITIVE_LENGTH_RETRY_MAX_TOKENS)
            _bump_cognitive_retry("cognitive_length_retry_succeeded")
            return scores, flags
        except Exception as retry_err:
            _bump_cognitive_retry("cognitive_length_retry_failed")
            logger.error(
                f"Cognitive validator failed for slot {slot.question_number} "
                f"after length-limit retry: {retry_err}"
            )
            return cognitive_validator_unavailable_payload(retry_err)


async def _generate_explanation_for_core(
    slot: QuestionSlot,
    core: dict,
    state: PaperState,
    chapter_excerpt: str,
    *,
    rejection_feedback: Optional[str] = None,
    cost_diagnostics: Optional[dict] = None,
) -> Optional[str]:
    """Generate explanation only; must not alter the frozen question core."""
    source_text = chapter_excerpt or ""
    if state.get("bank_batch_mode") and source_text:
        probe = " ".join(
            [
                str(core.get("question") or ""),
                str(core.get("topic") or ""),
                str(core.get("sub_topic") or ""),
            ]
        )
        source_text = select_source_grounding_window(source_text, probe)
    chapter_block = ""
    if source_text:
        chapter_block = (
            f"\n--- CHAPTER CONTENT ---\n{source_text}\n--- END CHAPTER CONTENT ---\n"
        )
    feedback_block = ""
    if rejection_feedback:
        feedback_block = (
            "\nPREVIOUS EXPLANATION WAS REJECTED. Fix only the explanation:\n"
            f"{rejection_feedback}\n"
        )
    user_prompt = f"""Write an explanation for this validated exam question.
Do NOT change the stem, options, or correct answer.

Grade: {slot.grade or 'not specified'}
Subject: {slot.subject}
Chapter: {slot.chapter} — {slot.chapter_title}
Answer type: {slot.answer_type}

Question: {core.get('question')}
Options:
{json.dumps(core.get('options') or [], indent=2)}
Correct indices (0-based, frozen): {core.get('correct_indices')}
Correct answer (frozen): {core.get('answer')}
Topic / sub-topic: {core.get('topic')} / {core.get('sub_topic')}
{feedback_block}{chapter_block}
"""
    composition = build_prompt_composition(
        system_prompt=EXPLANATION_GENERATOR_SYSTEM,
        user_prompt=user_prompt,
        grounding_text=source_text or "",
        static_system_instructions=EXPLANATION_GENERATOR_SYSTEM,
        retry_feedback=feedback_block,
    )
    try:
        result: ExplanationOnlyOutput = await _invoke_structured(
            EXPLANATION_GENERATOR_SYSTEM,
            user_prompt,
            state.get("generator_model"),
            ExplanationOnlyOutput,
            max_tokens=EXPLANATION_MAX_TOKENS,
            temperature=0.4,
            llm_stage=LLM_STAGE_EXPLANATION_GENERATE,
            cost_diagnostics=cost_diagnostics,
            prompt_composition=composition,
            bank_batch_mode=bool(state.get("bank_batch_mode")),
        )
        text = str(result.explanation or "").strip()
        return text or None
    except Exception as e:
        logger.error(
            f"Explanation generator failed for slot {slot.question_number}: {e}"
        )
        return None


async def _validate_explanation_only(
    slot: QuestionSlot,
    core: dict,
    explanation: str,
    state: PaperState,
    chapter_excerpt: str,
    *,
    cost_diagnostics: Optional[dict] = None,
) -> Tuple[bool, List[str]]:
    """Validate explanation against a frozen core. Does not re-run cognitive scoring."""
    source_text = chapter_excerpt or ""
    if state.get("bank_batch_mode") and source_text:
        probe = " ".join(
            [
                str(core.get("question") or ""),
                str(core.get("topic") or ""),
                str(explanation or ""),
            ]
        )
        source_text = select_source_grounding_window(source_text, probe)
    chapter_block = ""
    if source_text:
        chapter_block = (
            f"\n--- CHAPTER CONTENT ---\n{source_text}\n--- END CHAPTER CONTENT ---\n"
        )
    user_prompt = f"""Validate ONLY this explanation for a frozen exam question.

Grade: {slot.grade or 'not specified'}
Subject: {slot.subject}
Chapter: {slot.chapter} — {slot.chapter_title}
Answer type: {slot.answer_type}

Question: {core.get('question')}
Options:
{json.dumps(core.get('options') or [], indent=2)}
Correct indices (0-based, frozen): {core.get('correct_indices')}
Correct answer (frozen): {core.get('answer')}
Explanation under review:
{explanation}
{chapter_block}
Set explanation_valid. List concise reasons if invalid.
"""
    composition = build_prompt_composition(
        system_prompt=EXPLANATION_VALIDATOR_SYSTEM,
        user_prompt=user_prompt,
        grounding_text=source_text or "",
        static_system_instructions=EXPLANATION_VALIDATOR_SYSTEM,
    )
    try:
        result: ExplanationValidatorOutput = await _invoke_structured(
            EXPLANATION_VALIDATOR_SYSTEM,
            user_prompt,
            state.get("reviewer_model") or state.get("generator_model"),
            ExplanationValidatorOutput,
            max_tokens=1024,
            temperature=0.2,
            llm_stage=LLM_STAGE_EXPLANATION_VALIDATE,
            cost_diagnostics=cost_diagnostics,
            prompt_composition=composition,
            bank_batch_mode=bool(state.get("bank_batch_mode")),
        )
        reasons = [str(r) for r in (result.reasons or []) if str(r).strip()]
        if not result.explanation_valid and not reasons:
            reasons = ["explanation is invalid"]
        return bool(result.explanation_valid), reasons
    except Exception as e:
        logger.error(
            f"Explanation validator failed for slot {slot.question_number}: {e}"
        )
        return False, [f"explanation validator error: {e}"]


async def _finalize_bank_batch_explanation(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
    *,
    cost_diagnostics: Optional[dict] = None,
    cost_lock: Optional[asyncio.Lock] = None,
) -> Tuple[bool, dict, List[str]]:
    """
    After core validation passes: generate + validate explanation with bounded retries.

    Returns (ok, updated_generated, failure_reasons). On success, generated includes
    a validated explanation and the frozen core fields are unchanged.
    """
    frozen = {
        "question": generated.get("question"),
        "options": list(generated.get("options") or []),
        "correct_indices": list(generated.get("correct_indices") or []),
        "answer": generated.get("answer"),
        "topic": generated.get("topic"),
        "sub_topic": generated.get("sub_topic"),
    }
    feedback: Optional[str] = None
    last_reasons: List[str] = ["explanation is invalid"]

    async def _bump(field: str, amount: int = 1) -> None:
        if cost_diagnostics is None:
            return

        def _do() -> None:
            cost_diagnostics[field] = int(cost_diagnostics.get(field) or 0) + amount

        if cost_lock is not None:
            async with cost_lock:
                _do()
        else:
            _do()

    async def _stage(name: str, elapsed_ms: float) -> None:
        if cost_diagnostics is None:
            return
        if cost_lock is not None:
            async with cost_lock:
                record_bank_cost_stage(cost_diagnostics, name, elapsed_ms)
        else:
            record_bank_cost_stage(cost_diagnostics, name, elapsed_ms)

    t_wall = time.perf_counter()
    for attempt in range(1, MAX_EXPLANATION_ATTEMPTS + 1):
        if attempt > 1:
            await _bump("explanation_retry_calls")
        t0 = time.perf_counter()
        explanation = await _generate_explanation_for_core(
            slot,
            frozen,
            state,
            chapter_excerpt,
            rejection_feedback=feedback,
            cost_diagnostics=cost_diagnostics,
        )
        await _stage("explanation_generate", (time.perf_counter() - t0) * 1000.0)
        await _bump("explanation_generation_calls")
        if not explanation:
            last_reasons = ["explanation generation failed"]
            feedback = "Produce a complete Grade-appropriate explanation defending the correct answer(s)."
            continue

        # Freeze invariant: core must remain identical.
        for key, value in frozen.items():
            if generated.get(key) != value:
                generated[key] = value

        t1 = time.perf_counter()
        ok, reasons = await _validate_explanation_only(
            slot,
            frozen,
            explanation,
            state,
            chapter_excerpt,
            cost_diagnostics=cost_diagnostics,
        )
        await _stage("explanation_validate", (time.perf_counter() - t1) * 1000.0)
        await _bump("explanation_validation_calls")
        if ok:
            generated["explanation"] = explanation
            if attempt > 1:
                await _bump("explanation_retries_succeeded")
            await _stage(
                "explanation_finalize", (time.perf_counter() - t_wall) * 1000.0
            )
            return True, generated, []

        await _bump("explanation_validation_failures")
        last_reasons = reasons or ["explanation is invalid"]
        feedback = "; ".join(last_reasons)

    await _bump("explanation_retries_failed")
    await _stage("explanation_finalize", (time.perf_counter() - t_wall) * 1000.0)
    return False, generated, last_reasons


async def _validate_slot_independently(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
    existing_texts: List[str],
    existing_questions: Optional[List[dict]] = None,
    cost_diagnostics: Optional[dict] = None,
    cost_lock: Optional[asyncio.Lock] = None,
    assigned_intent: Optional[dict] = None,
) -> dict:
    """Blind solve + cognitive/quality concurrently; both mandatory, then combine.

    Neither call's result is used as input to the other. Blind remains answer-key
    blind; cognitive still receives the full key. Results merge only afterward via
    apply_independent_validation.

    Bank Batch core phase defers explanation_valid to a later explanation pass.
    """

    async def _timed_blind():
        t0 = time.perf_counter()
        result = await _blind_solve(
            slot, generated, state, chapter_excerpt, cost_diagnostics=cost_diagnostics
        )
        return result, (time.perf_counter() - t0) * 1000.0

    async def _timed_cognitive():
        t0 = time.perf_counter()
        result = await _validate_cognitive_quality(
            slot,
            generated,
            state,
            chapter_excerpt,
            cost_diagnostics=cost_diagnostics,
        )
        return result, (time.perf_counter() - t0) * 1000.0

    t_wall = time.perf_counter()
    # return_exceptions=True waits for both tasks (no orphans). Propagate any
    # unexpected raise so a single surviving validator cannot accept alone.
    gathered = await asyncio.gather(
        _timed_blind(), _timed_cognitive(), return_exceptions=True
    )
    wall_ms = (time.perf_counter() - t_wall) * 1000.0

    failures = [item for item in gathered if isinstance(item, BaseException)]
    if failures:
        raise failures[0]

    solver_result, blind_ms = gathered[0]
    (scores, flags), cog_ms = gathered[1]

    if cost_diagnostics is not None:
        async def _bump() -> None:
            cost_diagnostics["blind_solver_calls"] = (
                int(cost_diagnostics.get("blind_solver_calls") or 0) + 1
            )
            record_bank_cost_stage(cost_diagnostics, "blind_solver", blind_ms)
            cost_diagnostics["cognitive_quality_calls"] = (
                int(cost_diagnostics.get("cognitive_quality_calls") or 0) + 1
            )
            record_bank_cost_stage(cost_diagnostics, "cognitive_quality", cog_ms)
            record_bank_cost_stage(
                cost_diagnostics, "concurrent_validation", wall_ms
            )

        if cost_lock is not None:
            async with cost_lock:
                await _bump()
        else:
            await _bump()

    solver_data = None
    flags = dict(flags or {})
    if isinstance(solver_result, BlindSolverUnavailable):
        flags[VALIDATOR_UNAVAILABLE_KEY] = True
        extra = list(flags.get("reasons") or [])
        extra.append(solver_result.reason)
        flags["reasons"] = extra
    elif solver_result is not None:
        solver_data = solver_result.model_dump()

    bank_core = bool(state.get("bank_batch_mode")) and not str(
        generated.get("explanation") or ""
    ).strip()
    return apply_independent_validation(
        slot=slot,
        criterion_scores=scores,
        quality_flags=flags,
        question=generated,
        existing_question_texts=existing_texts,
        existing_questions=existing_questions or [],
        book_grounded=bool(state.get("book_grounded") and chapter_excerpt),
        blind_solver=solver_data,
        content_aware_lexical=bool(state.get("bank_batch_mode")),
        assigned_intent=assigned_intent,
        require_explanation_valid=not bank_core,
    )


def _compose_question_record(
    slot: QuestionSlot,
    generated: dict,
    validation: dict,
    generation_attempts: int,
) -> dict:
    indices = list(generated.get("correct_indices") or [])
    q_type = "multi_correct" if slot.answer_type == "multiple_correct" else "mcq"
    return {
        "question_number": slot.question_number,
        "question": generated.get("question", ""),
        "type": q_type,
        "answer_type": slot.answer_type,
        "options": generated.get("options") or [],
        "correct_indices": indices,
        "answer": generated.get("answer") or _letters_from_indices(indices),
        "explanation": generated.get("explanation", ""),
        "topic": generated.get("topic") or slot.subject,
        "sub_topic": generated.get("sub_topic") or "",
        "grade": slot.grade,
        "subject": slot.subject,
        "chapter": slot.chapter,
        "chapter_title": slot.chapter_title,
        "section_ref": slot.chapter_title,
        "target_difficulty": slot.target_difficulty,
        "validated_cognitive_difficulty": validation["validated_cognitive_difficulty"],
        "difficulty": slot.target_difficulty,  # legacy display field; equals target only when passed
        "difficulty_score": validation["difficulty_score"],
        "difficulty_scores": validation["difficulty_scores"],
        "validation_status": validation["validation_status"],
        "validation_reasons": validation["validation_reasons"],
        "generation_attempts": generation_attempts,
        # Blind-solver / quality validation flags (persisted for QA auditing).
        "blind_solver_answer": validation.get("blind_solver_answer", "N/A (not persisted)"),
        "answer_agreement": validation.get("answer_agreement", "N/A (not persisted)"),
        "information_sufficient": validation.get(
            "information_sufficient", "N/A (not persisted)"
        ),
        "arithmetic_consistent": validation.get(
            "arithmetic_consistent", "N/A (not persisted)"
        ),
        "no_unsupported_claims": validation.get(
            "no_unsupported_claims", "N/A (not persisted)"
        ),
        "option_defensibility": validation.get(
            "option_defensibility", "N/A (not persisted)"
        ),
        "distractors_ok": validation.get("distractors_ok", "N/A (not persisted)"),
        "terminology_grounded": validation.get(
            "terminology_grounded", "N/A (not persisted)"
        ),
        # Post-exam statistical fields (null until student response data exists)
        "observed_facility": None,
        "observed_discrimination": None,
        "calibrated_difficulty": None,
        "calibration_status": None,
    }


async def check_bank_duplicate(question_text: str) -> bool:
    """Persistent question-bank duplicate check (text-contains search, not embedding).

    LIMITATION: Uses lexical text search (string::contains). Does not detect
    semantically similar questions with different wording. A future improvement
    could use embedding similarity or a composite key of
    (chapter + topic + sub_topic + question_intent) to avoid generating multiple
    questions testing the same concept.
    """
    try:
        similar = await QuestionRecord.search_similar(question_text, limit=5)
    except Exception as e:
        logger.warning(f"Bank search failed: {e}")
        return False
    texts = [s.get("question", "") for s in similar]
    return is_near_duplicate(question_text, texts)


def _duplicate_context(
    state: PaperState, approved: List[dict]
) -> tuple[List[str], List[dict]]:
    """Merge in-batch approved questions with optional bank-batch seed duplicates."""
    seed_texts = list(state.get("bank_duplicate_seed_texts") or [])
    seed_qs = list(state.get("bank_duplicate_seed_questions") or [])
    existing_texts = [q.get("question", "") for q in approved] + seed_texts
    existing_qs = list(approved) + seed_qs
    return existing_texts, existing_qs


def _bank_soft_coverage_hints(state: PaperState, approved: List[dict]) -> str:
    if not state.get("bank_batch_mode"):
        return ""
    usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(approved)
    return format_underused_concept_hints(
        usage_qs,
        state.get("bank_diversity_catalog") or {},
    )


def _resolve_duplicate_rejection(
    generated: dict,
    slot: QuestionSlot,
    existing_qs: List[dict],
    reasons: List[str],
    *,
    bank_batch_mode: bool,
) -> tuple[List[str], Optional[dict], str]:
    """Enrich duplicate rejections with match metadata and Bank Batch retry guidance."""
    reasons = list(reasons or [])
    reasons_l = " ".join(reasons).lower()
    match = None
    if any("semantic duplicate" in r.lower() for r in reasons):
        match = find_semantic_duplicate_match(
            {
                "question": generated.get("question", ""),
                "topic": generated.get("topic", ""),
                "chapter": slot.chapter,
            },
            existing_qs,
        )
    if match is None and (
        "near-duplicate" in reasons_l or "duplicate or near-duplicate" in reasons_l
    ):
        match = find_lexical_duplicate_match(
            generated.get("question", ""),
            existing_qs,
            content_aware=bank_batch_mode,
        )

    feedback = "; ".join(reasons) if reasons else "quality checks failed"
    if bank_batch_mode and (
        match
        or "duplicate" in reasons_l
        or "near-duplicate" in reasons_l
    ):
        guidance = format_bank_batch_duplicate_retry_guidance(match)
        feedback = f"{feedback}\n\n{guidance}"
    return reasons, match, feedback


async def _is_external_duplicate(question_text: str, state: PaperState) -> bool:
    """Global bank duplicate check (final-paper mode only). Bank batch uses scoped seeds."""
    if state.get("bank_batch_mode"):
        return False
    return await check_bank_duplicate(question_text)


async def fill_slots(state: PaperState) -> dict:
    """Generate + independently validate each blueprint slot with bounded concurrency."""
    slots = [_slot_from_dict(s) for s in (state.get("slots") or [])]
    max_attempts = int(state.get("max_slot_attempts") or MAX_SLOT_ATTEMPTS)
    concurrency = int(state.get("slot_concurrency") or MAX_SLOT_CONCURRENCY)
    concurrency = max(1, min(concurrency, 8))
    chapter_chunks: Dict[str, List[str]] = state.get("chapter_chunks") or {}
    approved: List[dict] = []
    failed_slots: List[dict] = []
    used_stems: List[str] = list(state.get("used_stems") or [])
    rejected_log: List[dict] = []
    cost_diagnostics = dict(
        state.get("cost_diagnostics") or empty_bank_cost_diagnostics()
    )
    intent_diagnostics = dict(
        state.get("intent_diagnostics") or empty_intent_diagnostics()
    )
    intent_assignments: Dict[str, dict] = dict(state.get("bank_intent_assignments") or {})
    intent_remaining: List[dict] = list(state.get("bank_intent_remaining") or [])
    intent_retired_ids: set = set()
    intent_dup_hits: Dict[str, int] = {}
    intent_family_hits: Dict[str, Dict[str, int]] = {}
    slot_prev_rejected_form: Dict[str, str] = {}
    intent_planner_on = bool(
        state.get("bank_batch_mode") and is_bank_intent_planner_enabled()
    )
    lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(concurrency)
    intent_ctx = dict(state.get("intent_planner_context") or {})

    async def _top_up_intents(
        active: Optional[dict],
        slot_key: str,
        chunks_for_slot: List[str],
        *,
        target_difficulty: str = "",
    ):
        nonlocal intent_remaining, intent_assignments, intent_diagnostics
        if not intent_planner_on:
            return active
        n_slots = len(state.get("slots") or [])
        async with lock:
            catalog = list(state.get("bank_intent_catalog") or [])
            missing = max(0, n_slots - len(approved))
            unused = len(intent_remaining)
            need_expand = should_replenish_catalog(
                unused_intents=unused,
                missing_slots=missing,
                catalog_size=len(catalog),
                requested_count=int(intent_ctx.get("requested_count") or n_slots),
                planner_calls=int(intent_diagnostics.get("planner_calls") or 0),
                replenish_rounds=int(intent_diagnostics.get("replenishment_rounds") or 0),
                require_capacity_for_missing=False,
            )
            retired_objs = [
                x
                for x in catalog
                if str(x.get("intent_id") or "") in intent_retired_ids
            ]
            bank_qs = list(state.get("bank_duplicate_seed_questions") or [])
            accepted_qs = list(approved)
            remaining_snap = list(intent_remaining)
        if need_expand:
            new_cat, new_rem = await replenish_running_pool(
                catalog=catalog,
                remaining=remaining_snap,
                missing_slots=missing,
                requested_count=int(intent_ctx.get("requested_count") or n_slots),
                chunks=chunks_for_slot,
                grade=str(intent_ctx.get("grade") or state.get("grade") or ""),
                subject=str(intent_ctx.get("subject") or state.get("subject") or ""),
                chapter=int(intent_ctx.get("chapter") or 0),
                chapter_title=str(intent_ctx.get("chapter_title") or ""),
                difficulty=str(intent_ctx.get("difficulty") or "easy"),
                bank_questions=bank_qs,
                retired_intents=retired_objs,
                accepted_questions=accepted_qs,
                diagnostics=intent_diagnostics,
                model_id=state.get("generator_model"),
                cache_key=str(intent_ctx.get("cache_key") or ""),
                book_id=str(intent_ctx.get("book_id") or state.get("book_id") or ""),
                content_hash=str(intent_ctx.get("content_hash") or ""),
                cost_diagnostics=cost_diagnostics,
            )
            async with lock:
                state["bank_intent_catalog"] = new_cat
                intent_remaining[:] = new_rem
        if not active:
            async with lock:
                usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(
                    approved
                )
                nxt = take_next_unused_intent(
                    intent_remaining,
                    retired_ids=intent_retired_ids,
                    assigned_values=list(intent_assignments.values()),
                    target_difficulty=target_difficulty,
                    diagnostics=intent_diagnostics,
                    usage_questions=usage_qs,
                )
                if nxt:
                    intent_assignments[slot_key] = nxt
                    return nxt
                intent_diagnostics["catalog_exhaustion_count"] = int(
                    intent_diagnostics.get("catalog_exhaustion_count") or 0
                ) + 1
            return None
        if state.get("bank_batch_mode"):
            async with lock:
                active = ensure_easy_safe_assigned_intent(
                    active,
                    intent_remaining,
                    target_difficulty=target_difficulty,
                    retired_ids=intent_retired_ids,
                    assigned_values=list(intent_assignments.values()),
                    diagnostics=intent_diagnostics,
                    assignments=intent_assignments,
                    slot_key=slot_key,
                )
        return active

    async def _process_slot(slot: QuestionSlot) -> None:
        feedback = None
        outcome = "needs_manual_review"
        last_record = None
        prev_intent_words: set = set()
        prev_chunk_index: Optional[int] = None
        slot_key = str(int(slot.question_number))
        active_intent: Optional[dict] = None
        if intent_planner_on:
            active_intent = intent_assignments.get(slot_key)
        async with semaphore:
            for attempt in range(1, max_attempts + 1):
                if state.get("bank_batch_mode"):
                    async with lock:
                        budget_block = bank_batch_generation_budget_block_reason(
                            state, cost_diagnostics=cost_diagnostics
                        )
                        if budget_block:
                            state["batch_budget_exhausted_reason"] = budget_block
                            feedback = (
                                "Batch generation budget exhausted; "
                                "preserving accepted questions and stopping new attempts."
                            )
                            outcome = "needs_manual_review"
                            break
                variety_diag = None
                chunks = chapter_chunks.get(str(slot.chapter), [])
                if intent_planner_on:
                    active_intent = await _top_up_intents(
                        active_intent,
                        slot_key,
                        chunks,
                        target_difficulty=slot.target_difficulty,
                    )
                diversity_guidance = None
                intent_guidance = None
                if state.get("bank_batch_mode") and is_bank_diversity_planner_enabled():
                    async with lock:
                        usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(
                            approved
                        )
                    usage = summarize_diversity_usage(usage_qs)
                    plan = plan_bank_batch_diversity(
                        slot=slot,
                        attempt=attempt,
                        catalog=state.get("bank_diversity_catalog") or {},
                        usage=usage,
                        chunks=chunks,
                        previous_intent_words=prev_intent_words or None,
                        previous_chunk_index=prev_chunk_index,
                    )
                    # Soft planner must never alter slot constraints
                    assert plan.target_difficulty == normalize_difficulty(slot.target_difficulty)
                    assert plan.answer_type == slot.answer_type
                    excerpt, prev_chunk_index = select_chunk_for_diversity_plan(chunks, plan)
                    diversity_guidance = format_diversity_guidance(plan)
                elif intent_planner_on and active_intent:
                    idx = active_intent.get("chunk_index")
                    try:
                        idx_i = int(idx) if idx is not None else None
                    except (TypeError, ValueError):
                        idx_i = None
                    if chunks and idx_i is not None and 0 <= idx_i < len(chunks):
                        excerpt = chunks[idx_i]
                        prev_chunk_index = idx_i
                    else:
                        excerpt = select_chapter_chunk(chunks, slot.question_number - 1, attempt)
                        if chunks:
                            prev_chunk_index = (
                                slot.question_number - 1 + max(attempt, 1) - 1
                            ) % len(chunks)
                    intent_guidance = format_assigned_intent_guidance(active_intent)
                else:
                    excerpt = select_chapter_chunk(chunks, slot.question_number - 1, attempt)
                    if chunks:
                        prev_chunk_index = (
                            slot.question_number - 1 + max(attempt, 1) - 1
                        ) % len(chunks)
                    # Bank Batch fill retries: avoid previously tried chunks for this slot
                    if (
                        state.get("bank_batch_mode")
                        and not is_bank_diversity_planner_enabled()
                        and not (intent_planner_on and active_intent)
                        and attempt > 1
                        and chunks
                    ):
                        avoided = []
                        for entry in rejected_log:
                            if (
                                entry.get("question_number") == slot.question_number
                                and entry.get("source_chunk_index") is not None
                            ):
                                try:
                                    avoided.append(int(entry["source_chunk_index"]))
                                except (TypeError, ValueError):
                                    pass
                        if avoided:
                            excerpt, prev_chunk_index = select_chunk_avoiding_history(
                                chunks,
                                slot.question_number - 1,
                                attempt,
                                avoided,
                            )
                soft_hints = ""
                if state.get("bank_batch_mode") and not is_bank_diversity_planner_enabled():
                    async with lock:
                        soft_hints = _bank_soft_coverage_hints(state, approved)
                # Bank Batch strategy-aware retry feedback (within fill budget)
                if (
                    state.get("bank_batch_mode")
                    and attempt > 1
                    and feedback
                ):
                    avoidance = build_slot_avoidance_history(
                        rejected_log, slot.question_number
                    )
                    strategy = classify_bank_refill_strategy(
                        [feedback], avoidance
                    )
                    feedback = (
                        f"{feedback}\n\n"
                        f"{format_bank_batch_strategy_guidance(strategy, slot=slot, avoidance=avoidance, soft_coverage_hints=soft_hints)}"
                    )
                # Step 8: compact novelty brief (assigned intent + closest bank avoids)
                novelty_brief = None
                if intent_planner_on and active_intent:
                    async with lock:
                        existing_for_novelty = list(
                            state.get("bank_duplicate_seed_questions") or []
                        ) + list(approved)
                        avoidance_nov = build_slot_avoidance_history(
                            rejected_log, slot.question_number
                        )
                    closest = select_closest_bank_stems_for_intent(
                        active_intent,
                        existing_for_novelty,
                        limit=3,
                    )
                    used_forms = [
                        question_task_form(s)
                        for s in (avoidance_nov.get("rejected_stems") or [])
                        if question_task_form(s)
                    ]
                    used_forms.extend(
                        item.get("question_form") or ""
                        for item in closest
                        if item.get("question_form")
                    )
                    novelty_brief = format_bank_batch_novelty_brief(
                        active_intent,
                        chapter_excerpt=excerpt or "",
                        closest_bank=closest,
                        rejected_stems=avoidance_nov.get("rejected_stems") or [],
                        matched_stems=avoidance_nov.get("matched_stems") or [],
                        used_forms=used_forms,
                        target_difficulty=slot.target_difficulty,
                    )
                    async with lock:
                        intent_diagnostics["novelty_briefs_created"] = (
                            int(intent_diagnostics.get("novelty_briefs_created") or 0)
                            + 1
                        )
                        n_avoid = len(closest) + len(
                            avoidance_nov.get("matched_stems") or []
                        ) + min(3, len(avoidance_nov.get("rejected_stems") or []))
                        intent_diagnostics["novelty_avoid_stems_included"] = (
                            int(
                                intent_diagnostics.get("novelty_avoid_stems_included")
                                or 0
                            )
                            + n_avoid
                        )
                t_gen = time.perf_counter()
                forbidden_stems = None
                if state.get("bank_batch_mode"):
                    async with lock:
                        forbidden_stems = _forbidden_stems_for_bank_generate(
                            state,
                            slot,
                            used_stems=used_stems,
                            approved=approved,
                            rejected_log=rejected_log,
                            active_intent=active_intent,
                        )
                length_retries_before = int(
                    cost_diagnostics.get("length_limit_retry_attempted") or 0
                )
                generated = await _generate_for_slot(
                    slot,
                    state,
                    excerpt,
                    feedback,
                    diversity_guidance=diversity_guidance,
                    soft_coverage_hints=soft_hints or None,
                    intent_guidance=intent_guidance,
                    novelty_brief=novelty_brief,
                    forbidden_stems=forbidden_stems,
                    cost_diagnostics=cost_diagnostics,
                )
                if state.get("bank_batch_mode"):
                    async with lock:
                        length_extra = max(
                            0,
                            int(cost_diagnostics.get("length_limit_retry_attempted") or 0)
                            - length_retries_before,
                        )
                        cost_diagnostics["generated_attempts"] = (
                            int(cost_diagnostics.get("generated_attempts") or 0)
                            + 1
                            + length_extra
                        )
                        cost_diagnostics["core_generation_calls"] = (
                            int(cost_diagnostics.get("core_generation_calls") or 0)
                            + 1
                            + length_extra
                        )
                        cost_diagnostics["core_generation_llm_calls"] = int(
                            cost_diagnostics.get("core_generation_calls") or 0
                        )
                        if length_extra:
                            cost_diagnostics["length_recovery_extra_calls"] = (
                                int(
                                    cost_diagnostics.get("length_recovery_extra_calls")
                                    or 0
                                )
                                + length_extra
                            )
                        record_bank_cost_stage(
                            cost_diagnostics,
                            "generate",
                            (time.perf_counter() - t_gen) * 1000.0,
                        )
                if not generated:
                    feedback = "Generation failed; rewrite a complete MCQ with five options A–E."
                    outcome = decide_slot_outcome(False, attempt, max_attempts)
                    if state.get("bank_batch_mode"):
                        async with lock:
                            cost_diagnostics["core_generation_failures"] = (
                                int(
                                    cost_diagnostics.get("core_generation_failures") or 0
                                )
                                + 1
                            )
                    if outcome == "retry":
                        continue
                    break

                if state.get("bank_batch_mode"):
                    self_check_errors = generator_structural_self_check(
                        generated, answer_type=slot.answer_type
                    )
                    if self_check_errors:
                        feedback = "; ".join(self_check_errors)
                        outcome = decide_slot_outcome(False, attempt, max_attempts)
                        async with lock:
                            bump_bank_early_exit(cost_diagnostics, "structural")
                            cost_diagnostics["explanations_avoided_core_failed"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                                + 1
                            )
                            cost_diagnostics["cores_rejected_before_explanation"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                            )
                            rejected_log.append(
                                build_rejected_attempt_record(
                                    slot=slot,
                                    attempt=attempt,
                                    generated=generated,
                                    rejection_reasons=self_check_errors,
                                    rewrite_instruction=feedback,
                                    source_chunk_index=prev_chunk_index,
                                    phase="fill",
                                )
                            )
                        if outcome == "retry":
                            continue
                        break

                # Step 7C: calibrated intent adherence (Bank Batch).
                # STRONG/PARTIAL → continue to Step 3B + quality validators.
                # TRUE DRIFT only → early reject; retry same assigned intent.
                if intent_planner_on and active_intent:
                    adh = classify_intent_adherence(active_intent, generated)
                    async with lock:
                        record_adherence_diagnostic(intent_diagnostics, adh)
                        if adh == ADHERENCE_PARTIAL and partial_adherence_may_continue(
                            active_intent,
                            generated,
                            target_difficulty=slot.target_difficulty,
                            answer_type=slot.answer_type,
                        ):
                            intent_diagnostics["adherence_partial_continued"] = (
                                int(
                                    intent_diagnostics.get(
                                        "adherence_partial_continued"
                                    )
                                    or 0
                                )
                                + 1
                            )
                    reject_drift = should_early_reject_for_intent_drift(adh)
                    if adh == ADHERENCE_PARTIAL and not partial_adherence_may_continue(
                        active_intent,
                        generated,
                        target_difficulty=slot.target_difficulty,
                        answer_type=slot.answer_type,
                    ):
                        reject_drift = True
                    if reject_drift:
                        feedback = intent_drift_feedback(active_intent)
                        outcome = decide_slot_outcome(False, attempt, max_attempts)
                        async with lock:
                            intent_diagnostics["drift_early_exits"] = (
                                int(intent_diagnostics.get("drift_early_exits") or 0) + 1
                            )
                            bump_bank_early_exit(cost_diagnostics, "intent_drift")
                            cost_diagnostics["explanations_avoided_core_failed"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                                + 1
                            )
                            cost_diagnostics["cores_rejected_before_explanation"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                            )
                            rej = build_rejected_attempt_record(
                                slot=slot,
                                attempt=attempt,
                                generated=generated,
                                rejection_reasons=[INTENT_DRIFT_REJECTION],
                                rewrite_instruction=feedback,
                                source_chunk_index=prev_chunk_index,
                                phase="fill",
                            )
                            rej["assigned_intent_id"] = active_intent.get("intent_id")
                            rej["intent_adherence"] = adh
                            rejected_log.append(rej)
                        if outcome == "retry":
                            continue
                        break

                async with lock:
                    existing_texts, existing_qs = _duplicate_context(state, approved)
                _lex_aware = bool(state.get("bank_batch_mode"))

                # Step 5 (Bank Batch): cheap gates before blind/cognitive LLM.
                if state.get("bank_batch_mode"):
                    t_early = time.perf_counter()
                    early_reasons, early_cat = run_bank_batch_early_gates(
                        slot=slot,
                        generated=generated,
                        existing_question_texts=existing_texts,
                        existing_questions=existing_qs,
                    )
                    async with lock:
                        record_bank_cost_stage(
                            cost_diagnostics,
                            "early_gates",
                            (time.perf_counter() - t_early) * 1000.0,
                        )
                    if early_reasons:
                        validation = _rejected_validation_stub(slot, early_reasons)
                        async with lock:
                            bump_bank_early_exit(cost_diagnostics, early_cat)
                    else:
                        validation_excerpt = _bank_batch_validation_excerpt(
                            state,
                            slot,
                            generated,
                            chunks,
                            prev_chunk_index,
                            excerpt or "",
                            cost_diagnostics,
                        )
                        validation = await _validate_slot_independently(
                            slot,
                            generated,
                            state,
                            validation_excerpt,
                            existing_texts,
                            existing_questions=existing_qs,
                            cost_diagnostics=cost_diagnostics,
                            cost_lock=lock,
                            assigned_intent=active_intent,
                        )
                elif is_near_duplicate(
                    generated.get("question", ""),
                    existing_texts,
                    content_aware=_lex_aware,
                ) or await _is_external_duplicate(generated.get("question", ""), state):
                    validation = {
                        "passed": False,
                        "validation_status": "rejected",
                        "validation_reasons": ["duplicate or near-duplicate of an existing question"],
                        "difficulty_scores": {},
                        "difficulty_score": 0,
                        "validated_cognitive_difficulty": "easy",
                        "target_difficulty": slot.target_difficulty,
                    }
                else:
                    validation = await _validate_slot_independently(
                        slot, generated, state, excerpt, existing_texts,
                        existing_questions=existing_qs,
                        assigned_intent=active_intent,
                    )

                record = _compose_question_record(slot, generated, validation, attempt)
                if state.get("bank_batch_mode") and prev_chunk_index is not None:
                    record["source_chunk_index"] = prev_chunk_index
                last_record = record
                variety_diag = None
                if state.get("bank_batch_mode") and generated:
                    variety_diag = classify_variety_relation(
                        active_intent or {},
                        generated.get("question") or "",
                        existing_qs,
                        target_difficulty=slot.target_difficulty,
                    )
                stem = " ".join((generated.get("question") or "").split()[:4])
                prev_intent_words = _extract_intent_words(generated.get("question", ""))

                if validation["passed"]:
                    # Race-safe duplicate check before spending explanation tokens.
                    async with lock:
                        post_texts, post_qs = _duplicate_context(state, approved)
                        if is_near_duplicate(
                            generated.get("question", ""),
                            post_texts,
                            content_aware=_lex_aware,
                        ):
                            validation["passed"] = False
                            validation["validation_status"] = "rejected"
                            validation["validation_reasons"] = [
                                "duplicate or near-duplicate of an existing question"
                            ]
                            record["validation_status"] = "rejected"
                            record["validation_reasons"] = validation["validation_reasons"]
                            existing_qs = post_qs

                # Bank Batch: core-validated only → generate/validate explanation.
                if validation["passed"] and state.get("bank_batch_mode"):
                    record["core_validated"] = True
                    async with lock:
                        cost_diagnostics["core_validated_count"] = (
                            int(cost_diagnostics.get("core_validated_count") or 0) + 1
                        )
                    expl_ok, generated, expl_reasons = await _finalize_bank_batch_explanation(
                        slot,
                        generated,
                        state,
                        excerpt,
                        cost_diagnostics=cost_diagnostics,
                        cost_lock=lock,
                    )
                    if not expl_ok:
                        validation["passed"] = False
                        validation["validation_status"] = "rejected"
                        validation["validation_reasons"] = [
                            r if "explanation" in r.lower() else f"explanation is invalid: {r}"
                            for r in (expl_reasons or ["explanation is invalid"])
                        ]
                        generated["explanation"] = ""
                        record = _compose_question_record(
                            slot, generated, validation, attempt
                        )
                        if prev_chunk_index is not None:
                            record["source_chunk_index"] = prev_chunk_index
                        record["core_validated"] = True
                        last_record = record
                    else:
                        record = _compose_question_record(
                            slot, generated, validation, attempt
                        )
                        if prev_chunk_index is not None:
                            record["source_chunk_index"] = prev_chunk_index
                        record["core_validated"] = True
                        last_record = record

                if validation["passed"]:
                    async with lock:
                        post_texts, post_qs = _duplicate_context(state, approved)
                        if is_near_duplicate(
                            generated.get("question", ""),
                            post_texts,
                            content_aware=_lex_aware,
                        ):
                            validation["passed"] = False
                            validation["validation_status"] = "rejected"
                            validation["validation_reasons"] = [
                                "duplicate or near-duplicate of an existing question"
                            ]
                            record["validation_status"] = "rejected"
                            record["validation_reasons"] = validation["validation_reasons"]
                            existing_qs = post_qs
                        elif state.get("bank_batch_mode") and not str(
                            record.get("explanation") or ""
                        ).strip():
                            # Safety: never accept/persist without a validated explanation.
                            validation["passed"] = False
                            validation["validation_status"] = "rejected"
                            validation["validation_reasons"] = [
                                "explanation is invalid"
                            ]
                            record["validation_status"] = "rejected"
                            record["validation_reasons"] = validation["validation_reasons"]
                        else:
                            approved.append(record)
                            if stem:
                                used_stems.append(stem)
                            if intent_planner_on and active_intent:
                                record["assigned_intent_id"] = active_intent.get(
                                    "intent_id"
                                )
                                intent_diagnostics[
                                    "questions_accepted_from_assigned_intent"
                                ] = int(
                                    intent_diagnostics.get(
                                        "questions_accepted_from_assigned_intent"
                                    )
                                    or 0
                                ) + 1
                                prev_form = slot_prev_rejected_form.get(slot_key) or ""
                                new_form = question_task_form(
                                    generated.get("question") or ""
                                )
                                if (
                                    prev_form
                                    and new_form
                                    and prev_form != new_form
                                ):
                                    intent_diagnostics[
                                        "duplicate_retry_changed_question_form"
                                    ] = int(
                                        intent_diagnostics.get(
                                            "duplicate_retry_changed_question_form"
                                        )
                                        or 0
                                    ) + 1
                            outcome = "accept"
                            logger.info(
                                f"Q{slot.question_number} accepted ({slot.target_difficulty}/"
                                f"{slot.answer_type}/ch{slot.chapter}) on attempt {attempt}"
                            )
                            return

                # Core failed after blind/cognitive (and no explanation was attempted).
                if (
                    state.get("bank_batch_mode")
                    and not validation.get("passed")
                    and not record.get("core_validated")
                ):
                    async with lock:
                        cost_diagnostics["explanations_avoided_core_failed"] = (
                            int(
                                cost_diagnostics.get("explanations_avoided_core_failed")
                                or 0
                            )
                            + 1
                        )
                        cost_diagnostics["cores_rejected_before_explanation"] = int(
                            cost_diagnostics.get("explanations_avoided_core_failed") or 0
                        )
                        tag_recent_llm_calls(
                            cost_diagnostics,
                            count=3,
                            outcome="core_rejected_before_explanation",
                        )

                if stem:
                    async with lock:
                        used_stems.append(stem)

                outcome = decide_slot_outcome(False, attempt, max_attempts)
                reasons = list(validation.get("validation_reasons") or ["quality checks failed"])
                _, dup_match, feedback = _resolve_duplicate_rejection(
                    generated,
                    slot,
                    existing_qs,
                    reasons,
                    bank_batch_mode=bool(state.get("bank_batch_mode")),
                )
                # Step 8: duplicate keeps same intent until repeated exhaustion.
                # Academic failure families: first hit → corrective retry; second same
                # family → retire intent and pick a fresh underrepresented replacement.
                if intent_planner_on:
                    async with lock:
                        usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(
                            approved
                        )
                        if rejection_is_duplicate(reasons) and active_intent:
                            prev_form = question_task_form(
                                generated.get("question") or ""
                            )
                            if prev_form:
                                slot_prev_rejected_form[slot_key] = prev_form
                            active_intent, extra_fb, _retired = apply_duplicate_intent_policy(
                                active_intent=active_intent,
                                intent_dup_hits=intent_dup_hits,
                                intent_retired_ids=intent_retired_ids,
                                intent_remaining=intent_remaining,
                                intent_assignments=intent_assignments,
                                slot_key=slot_key,
                                intent_diagnostics=intent_diagnostics,
                                dup_match=dup_match,
                                target_difficulty=slot.target_difficulty,
                                usage_questions=usage_qs,
                            )
                            if extra_fb:
                                feedback = f"{feedback}\n\n{extra_fb}"
                        elif (
                            variety_counts_toward_intent_retirement(variety_diag)
                            and active_intent
                        ):
                            intent_diagnostics["variety_low_novelty_retries"] = (
                                int(
                                    intent_diagnostics.get("variety_low_novelty_retries")
                                    or 0
                                )
                                + 1
                            )
                            active_intent, extra_fb, _retired = apply_duplicate_intent_policy(
                                active_intent=active_intent,
                                intent_dup_hits=intent_dup_hits,
                                intent_retired_ids=intent_retired_ids,
                                intent_remaining=intent_remaining,
                                intent_assignments=intent_assignments,
                                slot_key=slot_key,
                                intent_diagnostics=intent_diagnostics,
                                dup_match=dup_match,
                                target_difficulty=slot.target_difficulty,
                                usage_questions=usage_qs,
                            )
                            if extra_fb:
                                feedback = f"{feedback}\n\n{extra_fb}"
                        elif active_intent:
                            family = classify_academic_failure_family(reasons)
                            if family:
                                active_intent, extra_fb, _retired = (
                                    apply_academic_failure_intent_policy(
                                        active_intent=active_intent,
                                        failure_family=family,
                                        intent_family_hits=intent_family_hits,
                                        intent_retired_ids=intent_retired_ids,
                                        intent_remaining=intent_remaining,
                                        intent_assignments=intent_assignments,
                                        slot_key=slot_key,
                                        intent_diagnostics=intent_diagnostics,
                                        target_difficulty=slot.target_difficulty,
                                        usage_questions=usage_qs,
                                        rejection_reasons=reasons,
                                    )
                                )
                                if extra_fb:
                                    feedback = f"{feedback}\n\n{extra_fb}"
                async with lock:
                    if state.get("bank_batch_mode"):
                        rejected_log.append(
                            attach_variety_diagnostics(
                                build_rejected_attempt_record(
                                    slot=slot,
                                    attempt=attempt,
                                    generated=generated,
                                    rejection_reasons=reasons,
                                    rewrite_instruction=feedback,
                                    duplicate_match=dup_match,
                                    source_chunk_index=prev_chunk_index,
                                    phase="fill",
                                ),
                                variety_diag,
                                active_intent,
                            )
                        )
                    else:
                        rejected_log.append(
                            {
                                "question_number": slot.question_number,
                                "attempt": attempt,
                                "rewrite_instruction": feedback,
                                "chapter": slot.chapter,
                                "target_difficulty": slot.target_difficulty,
                                "answer_type": slot.answer_type,
                            }
                        )
                logger.info(
                    f"Q{slot.question_number} rejected attempt {attempt}/{max_attempts}: {feedback}"
                )
                if outcome == "retry":
                    continue
                break

        if outcome != "accept":
            failed = last_record or {
                "question_number": slot.question_number,
                "chapter": slot.chapter,
                "chapter_title": slot.chapter_title,
                "target_difficulty": slot.target_difficulty,
                "answer_type": slot.answer_type,
                "grade": slot.grade,
                "validation_status": "needs_manual_review",
                "validation_reasons": [feedback or "generation failed"],
                "generation_attempts": max_attempts,
            }
            failed["validation_status"] = "needs_manual_review"
            async with lock:
                failed_slots.append(failed)
            logger.warning(
                f"Q{slot.question_number} needs_manual_review after {max_attempts} attempts"
            )

    logger.info(f"Filling {len(slots)} slots with concurrency={concurrency}")
    await asyncio.gather(*[_process_slot(slot) for slot in slots])

    return {
        "approved": approved,
        "failed_slots": failed_slots,
        "used_stems": used_stems,
        "rejected_with_feedback": rejected_log,
        "raw_questions": approved,
        "deduplicated": approved,
        "cost_diagnostics": finalize_bank_cost_diagnostics(cost_diagnostics),
        "bank_intent_assignments": intent_assignments,
        "bank_intent_remaining": intent_remaining,
        "bank_intent_catalog": list(state.get("bank_intent_catalog") or []),
        "intent_diagnostics": intent_diagnostics,
        "batch_budget_exhausted_reason": state.get("batch_budget_exhausted_reason"),
    }


# ---------------------------------------------------------------------------
# Reason-aware feedback for refill attempts
# ---------------------------------------------------------------------------

_REASON_GUIDANCE: Dict[str, str] = {
    "duplicate": (
        "Your previous question was rejected as a DUPLICATE. You MUST produce a "
        "substantially DIFFERENT question. Use a DIFFERENT scenario, calculation "
        "pattern, concept framing, question intent, and distractor structure. "
        "Prefer a different learning outcome, topic, or sub-topic from the SAME "
        "chapter. Do NOT rephrase the same idea."
    ),
    "difficulty": (
        "Your previous question was rejected because it was NOT difficult enough. "
        "A Difficult question MUST require: multiple connected reasoning steps, "
        "concept integration across sub-topics, analysis/evaluation/inference, "
        "and non-obvious distractors that reflect deep misconceptions. "
        "Do NOT increase difficulty through vocabulary, confusing wording, or "
        "excessive arithmetic. Increase COGNITIVE DEMAND."
    ),
    "difficulty_too_hard": (
        "Your previous question was rejected because it was TOO DIFFICULT for the "
        "target level. Simplify the cognitive demand: reduce the number of reasoning "
        "steps, use more direct recall or single-step application, and ensure "
        "distractors are clearly wrong to a student at this level."
    ),
    "answer_type": (
        "Your previous question was rejected for answer-type issues. "
        "For multiple_correct: ensure at least TWO options are defensibly correct "
        "and state in the question that multiple answers may be selected. "
        "For single_correct: ensure EXACTLY ONE option is defensible."
    ),
    "grounding": (
        "Your previous question was rejected because it was NOT grounded in the "
        "chapter material. Use a DIFFERENT chunk/section of the chapter. "
        "Every fact, concept, and distractor must come from the provided content."
    ),
    "answer_validity": (
        "Your previous question had invalid answers. Ensure the marked correct "
        "answer(s) are actually correct and all unmarked options are clearly wrong. "
        "Double-check the explanation justifies the correct answer(s)."
    ),
    "independent_solver": (
        "An independent solver derived a DIFFERENT answer from yours. Your marked "
        "correct answer may be wrong or another option may also be defensible. "
        "Rewrite so that EXACTLY the intended option(s) are correct and all others "
        "are clearly incorrect. Verify your explanation."
    ),
    "multiple_defensible": (
        "Your single-correct question has MORE THAN ONE defensible option. "
        "Rewrite so that exactly ONE option is correct and the others are clearly "
        "wrong. Each distractor should represent a specific misconception."
    ),
    "information_insufficient": (
        "The question stem does not provide enough information to uniquely determine "
        "the answer. Add the missing facts, data, or constraints to the stem so "
        "that a student with the right knowledge can solve it unambiguously."
    ),
    "arithmetic_inconsistency": (
        "There is a numerical or arithmetic inconsistency in the question. "
        "Recompute all calculations. Ensure numbers in the stem, options, and "
        "explanation are mutually consistent."
    ),
    "unsupported_claim": (
        "The question contains an absolute or misleading claim not supported by the "
        "chapter material (e.g. 'guaranteed returns', 'always grows faster'). "
        "Remove or qualify the claim, or ground it in the supplied curriculum."
    ),
    "semantic_duplicate": (
        "Your question tests substantially the same concept/intent as another "
        "accepted question. Choose a DIFFERENT learning outcome, topic, or "
        "question intent from the same chapter."
    ),
    "topic_metadata": (
        "The topic or sub_topic metadata is generic (e.g. 'Grade 5', 'Chapter 3'). "
        "Set topic to an actual concept from the chapter (e.g. 'Simple Interest', "
        "'Needs vs Wants'). Set sub_topic to a meaningful sub-concept."
    ),
    "subjective_best_objective_criterion": (
        "The stem uses subjective terms like 'best/smart', but it does not provide "
        "an explicit objective decision criterion. Rewrite the question so the "
        "student can judge options using measurable constraints (budgets, reserves, "
        "maximize/minimize savings) and remove ambiguity."
    ),
    "irrelevant_distractors": (
        "One or more incorrect options are irrelevant/absurd (off-topic). Rewrite "
        "distractors as realistic Grade-appropriate misconceptions that are "
        "conceptually connected to the same learning goal."
    ),
    "redundant_correct_options": (
        "For multiple_correct questions, the correct options appear semantically "
        "redundant (same underlying idea reworded). Rewrite so each correct option "
        "represents a distinct valid idea."
    ),
    "terminology_grounding": (
        "The stem includes specialized terminology not clearly supported by the "
        "provided chapter excerpt. Rewrite using Grade-appropriate language that "
        "appears in the supplied material."
    ),
}


def _build_reason_aware_feedback(
    rejection_reasons: List[str],
    previous_stems: List[str],
    accepted_topics: List[str],
    slot: QuestionSlot,
    *,
    bank_batch_mode: bool = False,
    duplicate_match: Optional[dict] = None,
) -> str:
    """Build enhanced feedback using the specific rejection reason."""
    parts: List[str] = []

    reasons_lower = " ".join(r.lower() for r in rejection_reasons)

    if "duplicate" in reasons_lower or "near-duplicate" in reasons_lower:
        if bank_batch_mode:
            parts.append(format_bank_batch_duplicate_retry_guidance(duplicate_match))
        else:
            parts.append(_REASON_GUIDANCE["duplicate"])
    if "difficulty mismatch" in reasons_lower:
        if f"target={slot.target_difficulty}" in reasons_lower:
            validated = ""
            for r in rejection_reasons:
                if "validated=" in r:
                    validated = r.split("validated=")[1].split()[0].rstrip(")")
                    break
            if validated and normalize_difficulty(validated) in ("easy", "medium") and slot.target_difficulty == "difficult":
                parts.append(_REASON_GUIDANCE["difficulty"])
            elif validated and slot.target_difficulty in ("easy", "medium"):
                parts.append(_REASON_GUIDANCE["difficulty_too_hard"])
            else:
                parts.append(_REASON_GUIDANCE["difficulty"])
    if "answer_type" in reasons_lower or "single_correct requires" in reasons_lower:
        parts.append(_REASON_GUIDANCE["answer_type"])
    if "answer validity" in reasons_lower or "answer_valid" in reasons_lower:
        parts.append(_REASON_GUIDANCE["answer_validity"])
    if "grounded" in reasons_lower or "hallucination" in reasons_lower:
        parts.append(_REASON_GUIDANCE["grounding"])
    if "independent solver disagrees" in reasons_lower:
        parts.append(_REASON_GUIDANCE["independent_solver"])
    if "multiple defensible" in reasons_lower:
        parts.append(_REASON_GUIDANCE["multiple_defensible"])
    if "information" in reasons_lower and "insufficient" in reasons_lower:
        parts.append(_REASON_GUIDANCE["information_insufficient"])
    if "arithmetic" in reasons_lower or "numerical inconsistency" in reasons_lower:
        parts.append(_REASON_GUIDANCE["arithmetic_inconsistency"])
    if "unsupported" in reasons_lower and "claim" in reasons_lower:
        parts.append(_REASON_GUIDANCE["unsupported_claim"])
    if "semantic duplicate" in reasons_lower:
        if bank_batch_mode:
            if not any("Do not paraphrase this question" in p for p in parts):
                parts.append(format_bank_batch_duplicate_retry_guidance(duplicate_match))
        else:
            parts.append(_REASON_GUIDANCE["semantic_duplicate"])
    if "topic metadata" in reasons_lower or "generic topic" in reasons_lower:
        parts.append(_REASON_GUIDANCE["topic_metadata"])
    if "subjective 'best'" in reasons_lower:
        parts.append(_REASON_GUIDANCE["subjective_best_objective_criterion"])
    if "unclear/irrelevant distractor" in reasons_lower:
        parts.append(_REASON_GUIDANCE["irrelevant_distractors"])
    if "redundant correct options" in reasons_lower:
        parts.append(_REASON_GUIDANCE["redundant_correct_options"])
    if "terminology" in reasons_lower:
        parts.append(_REASON_GUIDANCE["terminology_grounding"])

    if not parts:
        parts.append(
            "Previous attempt was rejected: " + "; ".join(rejection_reasons)
        )

    if previous_stems:
        stems_str = ", ".join(f'"{s}"' for s in previous_stems[-10:])
        parts.append(f"Previously rejected stems (AVOID these): [{stems_str}]")

    if accepted_topics:
        topic_counts: Dict[str, int] = {}
        for t in accepted_topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        heavy = [t for t, c in topic_counts.items() if c >= 2]
        if heavy:
            parts.append(
                f"Already well-covered topics in this paper (prefer a DIFFERENT topic): "
                + ", ".join(heavy)
            )

    return "\n\n".join(parts)


async def refill_slots(state: PaperState) -> dict:
    """Second pass: re-attempt only unfilled slots with reason-aware generation.

    Accepted questions in ``approved`` are never regenerated. Bank Batch mode uses
    strategy-aware feedback + chunk avoidance from rejection history (Step 4).
    """
    failed = state.get("failed_slots") or []
    if not failed:
        return {}

    max_refill = int(state.get("max_refill_attempts") or MAX_REFILL_ATTEMPTS)
    concurrency = int(state.get("slot_concurrency") or MAX_SLOT_CONCURRENCY)
    concurrency = max(1, min(concurrency, 8))
    chapter_chunks: Dict[str, List[str]] = state.get("chapter_chunks") or {}
    bank_batch_mode = bool(state.get("bank_batch_mode"))
    refill_phase = str(state.get("refill_phase") or "normal")

    # Snapshot approved — never mutate or regenerate these
    approved: List[dict] = list(state.get("approved") or [])
    approved_ids = {id(q) for q in approved}
    used_stems: List[str] = list(state.get("used_stems") or [])
    still_failed: List[dict] = []
    rejected_log: List[dict] = list(state.get("rejected_with_feedback") or [])
    diagnostics = dict(state.get("refill_diagnostics") or empty_bank_refill_diagnostics())
    cost_diagnostics = dict(
        state.get("cost_diagnostics") or empty_bank_cost_diagnostics()
    )
    intent_diagnostics = dict(
        state.get("intent_diagnostics") or empty_intent_diagnostics()
    )
    intent_assignments: Dict[str, dict] = dict(state.get("bank_intent_assignments") or {})
    intent_remaining: List[dict] = list(state.get("bank_intent_remaining") or [])
    intent_retired_ids: set = set()
    intent_dup_hits: Dict[str, int] = {}
    intent_family_hits: Dict[str, Dict[str, int]] = {}
    slot_prev_rejected_form: Dict[str, str] = {}
    intent_planner_on = bool(bank_batch_mode and is_bank_intent_planner_enabled())
    lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(concurrency)
    intent_ctx = dict(state.get("intent_planner_context") or {})

    async def _top_up_intents(
        active: Optional[dict],
        slot_key: str,
        chunks_for_slot: List[str],
        *,
        target_difficulty: str = "",
    ):
        nonlocal intent_remaining, intent_assignments, intent_diagnostics
        if not intent_planner_on:
            return active
        n_slots = len(state.get("slots") or [])
        async with lock:
            catalog = list(state.get("bank_intent_catalog") or [])
            missing = max(0, n_slots - len(approved))
            unused = len(intent_remaining)
            need_expand = should_replenish_catalog(
                unused_intents=unused,
                missing_slots=missing,
                catalog_size=len(catalog),
                requested_count=int(intent_ctx.get("requested_count") or n_slots),
                planner_calls=int(intent_diagnostics.get("planner_calls") or 0),
                replenish_rounds=int(intent_diagnostics.get("replenishment_rounds") or 0),
                require_capacity_for_missing=False,
            )
            retired_objs = [
                x for x in catalog if str(x.get("intent_id") or "") in intent_retired_ids
            ]
            bank_qs = list(state.get("bank_duplicate_seed_questions") or [])
            accepted_qs = list(approved)
            remaining_snap = list(intent_remaining)
        if need_expand:
            new_cat, new_rem = await replenish_running_pool(
                catalog=catalog,
                remaining=remaining_snap,
                missing_slots=missing,
                requested_count=int(intent_ctx.get("requested_count") or n_slots),
                chunks=chunks_for_slot,
                grade=str(intent_ctx.get("grade") or state.get("grade") or ""),
                subject=str(intent_ctx.get("subject") or state.get("subject") or ""),
                chapter=int(intent_ctx.get("chapter") or 0),
                chapter_title=str(intent_ctx.get("chapter_title") or ""),
                difficulty=str(intent_ctx.get("difficulty") or "easy"),
                bank_questions=bank_qs,
                retired_intents=retired_objs,
                accepted_questions=accepted_qs,
                diagnostics=intent_diagnostics,
                model_id=state.get("generator_model"),
                cache_key=str(intent_ctx.get("cache_key") or ""),
                book_id=str(intent_ctx.get("book_id") or state.get("book_id") or ""),
                content_hash=str(intent_ctx.get("content_hash") or ""),
                cost_diagnostics=cost_diagnostics,
            )
            async with lock:
                state["bank_intent_catalog"] = new_cat
                intent_remaining[:] = new_rem
        if not active:
            async with lock:
                usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(
                    approved
                )
                nxt = take_next_unused_intent(
                    intent_remaining,
                    retired_ids=intent_retired_ids,
                    assigned_values=list(intent_assignments.values()),
                    target_difficulty=target_difficulty,
                    diagnostics=intent_diagnostics,
                    usage_questions=usage_qs,
                )
                if nxt:
                    intent_assignments[slot_key] = nxt
                    return nxt
                intent_diagnostics["catalog_exhaustion_count"] = int(
                    intent_diagnostics.get("catalog_exhaustion_count") or 0
                ) + 1
            return None
        if state.get("bank_batch_mode"):
            async with lock:
                active = ensure_easy_safe_assigned_intent(
                    active,
                    intent_remaining,
                    target_difficulty=target_difficulty,
                    retired_ids=intent_retired_ids,
                    assigned_values=list(intent_assignments.values()),
                    diagnostics=intent_diagnostics,
                    assignments=intent_assignments,
                    slot_key=slot_key,
                )
        return active

    accepted_topics = [q.get("topic", "") for q in approved]

    # Build per-slot retry memory from the rejected log
    slot_rejected_stems: Dict[int, List[str]] = {}
    slot_rejected_reasons: Dict[int, List[str]] = {}
    slot_last_dup_match: Dict[int, Optional[dict]] = {}
    slot_avoidance: Dict[int, dict] = {}
    for entry in rejected_log:
        qn = entry.get("question_number")
        if qn is not None:
            slot_rejected_stems.setdefault(qn, [])
            slot_rejected_reasons.setdefault(qn, [])
            if entry.get("question"):
                slot_rejected_stems[qn].append(
                    " ".join(str(entry["question"]).split()[:8])
                )
            if entry.get("rewrite_instruction"):
                slot_rejected_reasons[qn].append(entry["rewrite_instruction"])
            if entry.get("duplicate_type") or entry.get("matched_stem"):
                slot_last_dup_match[qn] = {
                    "matched_question_id": entry.get("matched_question_id"),
                    "matched_stem": entry.get("matched_stem"),
                    "matched_topic": entry.get("matched_topic"),
                    "matched_sub_topic": entry.get("matched_sub_topic"),
                    "matched_intent_fingerprint": entry.get("matched_intent_fingerprint"),
                    "duplicate_type": entry.get("duplicate_type"),
                }
    for f in failed:
        qn = f.get("question_number")
        if qn and f.get("question"):
            slot_rejected_stems.setdefault(qn, []).append(
                " ".join(f["question"].split()[:8])
            )
        if qn is not None and bank_batch_mode:
            slot_avoidance[qn] = build_slot_avoidance_history(rejected_log, qn)

    logger.info(
        f"Refill pass ({refill_phase}): {len(failed)} unfilled slot(s), "
        f"max {max_refill} additional attempts each; "
        f"preserving {len(approved)} accepted question(s)"
    )

    async def _refill_one(failed_record: dict) -> None:
        slot = _slot_from_dict(failed_record)
        qn = slot.question_number
        # Hard invariant: difficulty / answer_type frozen from failed slot metadata
        assert slot.target_difficulty == normalize_difficulty(
            failed_record.get("target_difficulty") or slot.target_difficulty
        )
        assert slot.answer_type == (
            failed_record.get("answer_type") or slot.answer_type
        )

        prev_stems = slot_rejected_stems.get(qn, [])
        prev_reasons = slot_rejected_reasons.get(qn, [])
        avoidance = slot_avoidance.get(qn) or build_slot_avoidance_history(
            rejected_log, qn
        )

        last_rejection = prev_reasons[-1] if prev_reasons else "quality checks failed"
        last_reason_list = [last_rejection]
        # Prefer structured reasons from last rejected attempt when available
        for entry in reversed(rejected_log):
            if entry.get("question_number") == qn and entry.get("rejection_reasons"):
                last_reason_list = list(entry["rejection_reasons"])
                break

        strategy = (
            classify_bank_refill_strategy(last_reason_list, avoidance)
            if bank_batch_mode
            else "normal"
        )
        soft_for_strategy = ""
        if bank_batch_mode and not is_bank_diversity_planner_enabled():
            soft_for_strategy = _bank_soft_coverage_hints(state, approved)

        feedback = _build_reason_aware_feedback(
            last_reason_list,
            prev_stems,
            accepted_topics,
            slot,
            bank_batch_mode=bank_batch_mode,
            duplicate_match=slot_last_dup_match.get(qn),
        )
        if bank_batch_mode:
            feedback = (
                f"{feedback}\n\n"
                f"{format_bank_batch_strategy_guidance(strategy, slot=slot, avoidance=avoidance, soft_coverage_hints=soft_for_strategy)}"
            )
            async with lock:
                strategies = diagnostics.setdefault("strategies_used", {})
                strategies[strategy] = int(strategies.get(strategy) or 0) + 1

        outcome = "needs_manual_review"
        last_record = None
        prev_intent_fp = None
        if avoidance.get("intent_fingerprints"):
            prev_intent_fp = avoidance["intent_fingerprints"][-1]
        prev_chunk_for_slot = (
            avoidance["chunk_indices"][-1] if avoidance.get("chunk_indices") else None
        )
        slot_key = str(int(qn))
        active_intent: Optional[dict] = None
        if intent_planner_on:
            active_intent = intent_assignments.get(slot_key)

        async with semaphore:
            for attempt in range(1, max_refill + 1):
                if bank_batch_mode:
                    async with lock:
                        budget_block = bank_batch_generation_budget_block_reason(
                            state, cost_diagnostics=cost_diagnostics
                        )
                        if budget_block:
                            state["batch_budget_exhausted_reason"] = budget_block
                            feedback = (
                                "Batch generation budget exhausted; "
                                "preserving accepted questions and stopping new attempts."
                            )
                            outcome = "needs_manual_review"
                            break
                variety_diag = None
                chunks = chapter_chunks.get(str(slot.chapter), [])
                if intent_planner_on:
                    active_intent = await _top_up_intents(
                        active_intent,
                        slot_key,
                        chunks,
                        target_difficulty=slot.target_difficulty,
                    )
                diversity_guidance = None
                intent_guidance = None
                prev_chunk_index: Optional[int] = None
                if bank_batch_mode and is_bank_diversity_planner_enabled():
                    async with lock:
                        usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(
                            approved
                        )
                    usage = summarize_diversity_usage(usage_qs)
                    prev_words = set()
                    if failed_record.get("question"):
                        prev_words = _extract_intent_words(failed_record.get("question", ""))
                    for stem_text in prev_stems:
                        prev_words |= _extract_intent_words(stem_text)
                    plan = plan_bank_batch_diversity(
                        slot=slot,
                        attempt=attempt + MAX_SLOT_ATTEMPTS,
                        catalog=state.get("bank_diversity_catalog") or {},
                        usage=usage,
                        chunks=chunks,
                        previous_intent_words=prev_words or None,
                        previous_chunk_index=failed_record.get("source_chunk_index"),
                    )
                    assert plan.target_difficulty == normalize_difficulty(slot.target_difficulty)
                    assert plan.answer_type == slot.answer_type
                    excerpt, prev_chunk_index = select_chunk_for_diversity_plan(chunks, plan)
                    diversity_guidance = format_diversity_guidance(plan)
                elif intent_planner_on and active_intent:
                    idx = active_intent.get("chunk_index")
                    try:
                        idx_i = int(idx) if idx is not None else None
                    except (TypeError, ValueError):
                        idx_i = None
                    if chunks and idx_i is not None and 0 <= idx_i < len(chunks):
                        excerpt = chunks[idx_i]
                        prev_chunk_index = idx_i
                    else:
                        attempt_offset = attempt + MAX_SLOT_ATTEMPTS
                        excerpt = select_chapter_chunk(
                            chunks, slot.question_number - 1, attempt_offset
                        )
                        if chunks:
                            prev_chunk_index = (
                                slot.question_number - 1 + attempt_offset - 1
                            ) % len(chunks)
                    intent_guidance = format_assigned_intent_guidance(active_intent)
                elif bank_batch_mode:
                    attempt_offset = attempt + MAX_SLOT_ATTEMPTS
                    if strategy == "repeated_duplicate" or attempt > 1:
                        excerpt, prev_chunk_index = select_chunk_avoiding_history(
                            chunks,
                            slot.question_number - 1,
                            attempt_offset,
                            avoidance.get("chunk_indices") or [],
                        )
                    else:
                        excerpt = select_chapter_chunk(
                            chunks, slot.question_number - 1, attempt_offset
                        )
                        if chunks:
                            prev_chunk_index = (
                                slot.question_number - 1 + attempt_offset - 1
                            ) % len(chunks)
                else:
                    excerpt = select_chapter_chunk(
                        chunks, slot.question_number - 1, attempt + MAX_SLOT_ATTEMPTS
                    )
                    if chunks:
                        prev_chunk_index = (
                            slot.question_number - 1 + attempt + MAX_SLOT_ATTEMPTS - 1
                        ) % len(chunks)

                soft_hints = ""
                if bank_batch_mode and not is_bank_diversity_planner_enabled():
                    async with lock:
                        soft_hints = _bank_soft_coverage_hints(state, approved)

                if (
                    bank_batch_mode
                    and prev_chunk_for_slot is not None
                    and prev_chunk_index is not None
                    and prev_chunk_index != prev_chunk_for_slot
                ):
                    async with lock:
                        diagnostics["retries_changed_chunk"] = (
                            int(diagnostics.get("retries_changed_chunk") or 0) + 1
                        )
                    prev_chunk_for_slot = prev_chunk_index

                # Step 8 novelty brief (Bank Batch refill)
                novelty_brief = None
                if intent_planner_on and active_intent:
                    async with lock:
                        existing_for_novelty = list(
                            state.get("bank_duplicate_seed_questions") or []
                        ) + list(approved)
                        avoidance_nov = (
                            slot_avoidance.get(qn)
                            or build_slot_avoidance_history(rejected_log, qn)
                        )
                    closest = select_closest_bank_stems_for_intent(
                        active_intent,
                        existing_for_novelty,
                        limit=3,
                    )
                    used_forms = [
                        question_task_form(s)
                        for s in (avoidance_nov.get("rejected_stems") or [])
                        if question_task_form(s)
                    ]
                    used_forms.extend(
                        item.get("question_form") or ""
                        for item in closest
                        if item.get("question_form")
                    )
                    novelty_brief = format_bank_batch_novelty_brief(
                        active_intent,
                        chapter_excerpt=excerpt or "",
                        closest_bank=closest,
                        rejected_stems=avoidance_nov.get("rejected_stems") or [],
                        matched_stems=avoidance_nov.get("matched_stems") or [],
                        used_forms=used_forms,
                        target_difficulty=slot.target_difficulty,
                    )
                    async with lock:
                        intent_diagnostics["novelty_briefs_created"] = (
                            int(intent_diagnostics.get("novelty_briefs_created") or 0)
                            + 1
                        )
                        n_avoid = len(closest) + len(
                            avoidance_nov.get("matched_stems") or []
                        ) + min(3, len(avoidance_nov.get("rejected_stems") or []))
                        intent_diagnostics["novelty_avoid_stems_included"] = (
                            int(
                                intent_diagnostics.get("novelty_avoid_stems_included")
                                or 0
                            )
                            + n_avoid
                        )

                t_gen = time.perf_counter()
                forbidden_stems = None
                if state.get("bank_batch_mode"):
                    async with lock:
                        forbidden_stems = _forbidden_stems_for_bank_generate(
                            state,
                            slot,
                            used_stems=used_stems,
                            approved=approved,
                            rejected_log=rejected_log,
                            active_intent=active_intent,
                        )
                length_retries_before = int(
                    cost_diagnostics.get("length_limit_retry_attempted") or 0
                )
                generated = await _generate_for_slot(
                    slot,
                    state,
                    excerpt,
                    feedback,
                    diversity_guidance=diversity_guidance,
                    soft_coverage_hints=soft_hints or None,
                    intent_guidance=intent_guidance,
                    novelty_brief=novelty_brief,
                    forbidden_stems=forbidden_stems,
                    cost_diagnostics=cost_diagnostics,
                )
                if bank_batch_mode:
                    async with lock:
                        length_extra = max(
                            0,
                            int(cost_diagnostics.get("length_limit_retry_attempted") or 0)
                            - length_retries_before,
                        )
                        cost_diagnostics["generated_attempts"] = (
                            int(cost_diagnostics.get("generated_attempts") or 0)
                            + 1
                            + length_extra
                        )
                        cost_diagnostics["core_generation_calls"] = (
                            int(cost_diagnostics.get("core_generation_calls") or 0)
                            + 1
                            + length_extra
                        )
                        cost_diagnostics["core_generation_llm_calls"] = int(
                            cost_diagnostics.get("core_generation_calls") or 0
                        )
                        if length_extra:
                            cost_diagnostics["length_recovery_extra_calls"] = (
                                int(
                                    cost_diagnostics.get("length_recovery_extra_calls")
                                    or 0
                                )
                                + length_extra
                            )
                        record_bank_cost_stage(
                            cost_diagnostics,
                            "generate",
                            (time.perf_counter() - t_gen) * 1000.0,
                        )
                if not generated:
                    feedback = "Generation failed; rewrite a complete MCQ with five options A–E."
                    outcome = decide_slot_outcome(False, attempt, max_refill)
                    if outcome == "retry":
                        continue
                    break

                if bank_batch_mode:
                    self_check_errors = generator_structural_self_check(
                        generated, answer_type=slot.answer_type
                    )
                    if self_check_errors:
                        feedback = "; ".join(self_check_errors)
                        outcome = decide_slot_outcome(False, attempt, max_refill)
                        async with lock:
                            bump_bank_early_exit(cost_diagnostics, "structural")
                            bump_reason_counts(diagnostics, self_check_errors)
                            cost_diagnostics["explanations_avoided_core_failed"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                                + 1
                            )
                            cost_diagnostics["cores_rejected_before_explanation"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                            )
                            rejected_log.append(
                                build_rejected_attempt_record(
                                    slot=slot,
                                    attempt=MAX_SLOT_ATTEMPTS + attempt,
                                    generated=generated,
                                    rejection_reasons=self_check_errors,
                                    rewrite_instruction=feedback,
                                    source_chunk_index=prev_chunk_index,
                                    phase=f"refill_{refill_phase}",
                                )
                            )
                            avoidance = build_slot_avoidance_history(rejected_log, qn)
                            slot_avoidance[qn] = avoidance
                        if outcome == "retry":
                            continue
                        break

                # Step 7C: calibrated intent adherence (Bank Batch).
                if intent_planner_on and active_intent:
                    adh = classify_intent_adherence(active_intent, generated)
                    async with lock:
                        record_adherence_diagnostic(intent_diagnostics, adh)
                        if adh == ADHERENCE_PARTIAL and partial_adherence_may_continue(
                            active_intent,
                            generated,
                            target_difficulty=slot.target_difficulty,
                            answer_type=slot.answer_type,
                        ):
                            intent_diagnostics["adherence_partial_continued"] = (
                                int(
                                    intent_diagnostics.get(
                                        "adherence_partial_continued"
                                    )
                                    or 0
                                )
                                + 1
                            )
                    reject_drift = should_early_reject_for_intent_drift(adh)
                    if adh == ADHERENCE_PARTIAL and not partial_adherence_may_continue(
                        active_intent,
                        generated,
                        target_difficulty=slot.target_difficulty,
                        answer_type=slot.answer_type,
                    ):
                        reject_drift = True
                    if reject_drift:
                        feedback = intent_drift_feedback(active_intent)
                        outcome = decide_slot_outcome(False, attempt, max_refill)
                        async with lock:
                            intent_diagnostics["drift_early_exits"] = (
                                int(intent_diagnostics.get("drift_early_exits") or 0) + 1
                            )
                            bump_bank_early_exit(cost_diagnostics, "intent_drift")
                            bump_reason_counts(diagnostics, [INTENT_DRIFT_REJECTION])
                            cost_diagnostics["explanations_avoided_core_failed"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                                + 1
                            )
                            cost_diagnostics["cores_rejected_before_explanation"] = (
                                int(
                                    cost_diagnostics.get(
                                        "explanations_avoided_core_failed"
                                    )
                                    or 0
                                )
                            )
                            rej = build_rejected_attempt_record(
                                slot=slot,
                                attempt=MAX_SLOT_ATTEMPTS + attempt,
                                generated=generated,
                                rejection_reasons=[INTENT_DRIFT_REJECTION],
                                rewrite_instruction=feedback,
                                source_chunk_index=prev_chunk_index,
                                phase=f"refill_{refill_phase}",
                            )
                            rej["assigned_intent_id"] = active_intent.get("intent_id")
                            rej["intent_adherence"] = adh
                            rejected_log.append(rej)
                            avoidance = build_slot_avoidance_history(rejected_log, qn)
                            slot_avoidance[qn] = avoidance
                        if outcome == "retry":
                            continue
                        break

                async with lock:
                    existing_texts, existing_qs = _duplicate_context(state, approved)

                _lex_aware = bank_batch_mode
                if bank_batch_mode:
                    t_early = time.perf_counter()
                    early_reasons, early_cat = run_bank_batch_early_gates(
                        slot=slot,
                        generated=generated,
                        existing_question_texts=existing_texts,
                        existing_questions=existing_qs,
                    )
                    async with lock:
                        record_bank_cost_stage(
                            cost_diagnostics,
                            "early_gates",
                            (time.perf_counter() - t_early) * 1000.0,
                        )
                    if early_reasons:
                        validation = _rejected_validation_stub(slot, early_reasons)
                        async with lock:
                            bump_bank_early_exit(cost_diagnostics, early_cat)
                    else:
                        validation_excerpt = _bank_batch_validation_excerpt(
                            state,
                            slot,
                            generated,
                            chunks,
                            prev_chunk_index,
                            excerpt or "",
                            cost_diagnostics,
                        )
                        validation = await _validate_slot_independently(
                            slot,
                            generated,
                            state,
                            validation_excerpt,
                            existing_texts,
                            existing_questions=existing_qs,
                            cost_diagnostics=cost_diagnostics,
                            cost_lock=lock,
                            assigned_intent=active_intent,
                        )
                elif is_near_duplicate(
                    generated.get("question", ""),
                    existing_texts,
                    content_aware=_lex_aware,
                ) or await _is_external_duplicate(generated.get("question", ""), state):
                    validation = {
                        "passed": False,
                        "validation_status": "rejected",
                        "validation_reasons": [
                            "duplicate or near-duplicate of an existing question"
                        ],
                        "difficulty_scores": {},
                        "difficulty_score": 0,
                        "validated_cognitive_difficulty": "easy",
                        "target_difficulty": slot.target_difficulty,
                    }
                else:
                    validation = await _validate_slot_independently(
                        slot, generated, state, excerpt, existing_texts,
                        existing_questions=existing_qs,
                        assigned_intent=active_intent,
                    )

                record = _compose_question_record(
                    slot, generated, validation, MAX_SLOT_ATTEMPTS + attempt
                )
                if bank_batch_mode and prev_chunk_index is not None:
                    record["source_chunk_index"] = prev_chunk_index
                last_record = record
                variety_diag = None
                if bank_batch_mode and generated:
                    variety_diag = classify_variety_relation(
                        active_intent or {},
                        generated.get("question") or "",
                        existing_qs,
                        target_difficulty=slot.target_difficulty,
                    )
                stem = " ".join((generated.get("question") or "").split()[:4])
                new_fp = intent_fingerprint(generated.get("question") or "")

                if validation["passed"]:
                    async with lock:
                        post_texts, post_qs = _duplicate_context(state, approved)
                        if is_near_duplicate(
                            generated.get("question", ""),
                            post_texts,
                            content_aware=_lex_aware,
                        ):
                            validation["passed"] = False
                            record["validation_status"] = "rejected"
                            record["validation_reasons"] = [
                                "duplicate or near-duplicate of an existing question"
                            ]
                            existing_qs = post_qs

                if validation["passed"] and bank_batch_mode:
                    record["core_validated"] = True
                    async with lock:
                        cost_diagnostics["core_validated_count"] = (
                            int(cost_diagnostics.get("core_validated_count") or 0) + 1
                        )
                    expl_ok, generated, expl_reasons = await _finalize_bank_batch_explanation(
                        slot,
                        generated,
                        state,
                        excerpt,
                        cost_diagnostics=cost_diagnostics,
                        cost_lock=lock,
                    )
                    if not expl_ok:
                        validation["passed"] = False
                        validation["validation_status"] = "rejected"
                        validation["validation_reasons"] = [
                            r if "explanation" in r.lower() else f"explanation is invalid: {r}"
                            for r in (expl_reasons or ["explanation is invalid"])
                        ]
                        generated["explanation"] = ""
                        record = _compose_question_record(
                            slot, generated, validation, MAX_SLOT_ATTEMPTS + attempt
                        )
                        if prev_chunk_index is not None:
                            record["source_chunk_index"] = prev_chunk_index
                        record["core_validated"] = True
                        last_record = record
                    else:
                        record = _compose_question_record(
                            slot, generated, validation, MAX_SLOT_ATTEMPTS + attempt
                        )
                        if prev_chunk_index is not None:
                            record["source_chunk_index"] = prev_chunk_index
                        record["core_validated"] = True
                        last_record = record

                if validation["passed"]:
                    async with lock:
                        post_texts, post_qs = _duplicate_context(state, approved)
                        if is_near_duplicate(
                            generated.get("question", ""),
                            post_texts,
                            content_aware=_lex_aware,
                        ):
                            validation["passed"] = False
                            record["validation_status"] = "rejected"
                            record["validation_reasons"] = [
                                "duplicate or near-duplicate of an existing question"
                            ]
                            existing_qs = post_qs
                        elif bank_batch_mode and not str(
                            record.get("explanation") or ""
                        ).strip():
                            validation["passed"] = False
                            record["validation_status"] = "rejected"
                            record["validation_reasons"] = ["explanation is invalid"]
                        else:
                            approved.append(record)
                            approved_ids.add(id(record))
                            if stem:
                                used_stems.append(stem)
                            if intent_planner_on and active_intent:
                                record["assigned_intent_id"] = active_intent.get(
                                    "intent_id"
                                )
                                intent_diagnostics[
                                    "questions_accepted_from_assigned_intent"
                                ] = int(
                                    intent_diagnostics.get(
                                        "questions_accepted_from_assigned_intent"
                                    )
                                    or 0
                                ) + 1
                                prev_form = slot_prev_rejected_form.get(slot_key) or ""
                                new_form = question_task_form(
                                    generated.get("question") or ""
                                )
                                if prev_form and new_form and prev_form != new_form:
                                    intent_diagnostics[
                                        "duplicate_retry_changed_question_form"
                                    ] = int(
                                        intent_diagnostics.get(
                                            "duplicate_retry_changed_question_form"
                                        )
                                        or 0
                                    ) + 1
                            outcome = "accept"
                            logger.info(
                                f"Q{qn} REFILL accepted ({slot.target_difficulty}/"
                                f"{slot.answer_type}/ch{slot.chapter}) on refill attempt {attempt} "
                                f"[{refill_phase}/{strategy}]"
                            )
                            return

                if (
                    bank_batch_mode
                    and not validation.get("passed")
                    and not record.get("core_validated")
                ):
                    async with lock:
                        cost_diagnostics["explanations_avoided_core_failed"] = (
                            int(
                                cost_diagnostics.get("explanations_avoided_core_failed")
                                or 0
                            )
                            + 1
                        )
                        cost_diagnostics["cores_rejected_before_explanation"] = int(
                            cost_diagnostics.get("explanations_avoided_core_failed") or 0
                        )
                        tag_recent_llm_calls(
                            cost_diagnostics,
                            count=3,
                            outcome="core_rejected_before_explanation",
                        )

                if stem:
                    async with lock:
                        used_stems.append(stem)
                        prev_stems.append(stem)

                reasons = list(validation.get("validation_reasons") or ["quality checks failed"])
                _, dup_match, dup_feedback = _resolve_duplicate_rejection(
                    generated,
                    slot,
                    existing_qs,
                    reasons,
                    bank_batch_mode=bank_batch_mode,
                )
                feedback = _build_reason_aware_feedback(
                    reasons,
                    prev_stems,
                    accepted_topics,
                    slot,
                    bank_batch_mode=bank_batch_mode,
                    duplicate_match=dup_match,
                )
                # Step 8: duplicate keeps same intent until repeated exhaustion.
                # Academic failure families: first hit → corrective retry; second same
                # family → retire intent and pick a fresh underrepresented replacement.
                if intent_planner_on:
                    async with lock:
                        usage_qs = list(state.get("bank_duplicate_seed_questions") or []) + list(
                            approved
                        )
                        if rejection_is_duplicate(reasons) and active_intent:
                            prev_form = question_task_form(
                                generated.get("question") or ""
                            )
                            if prev_form:
                                slot_prev_rejected_form[slot_key] = prev_form
                            active_intent, extra_fb, _retired = apply_duplicate_intent_policy(
                                active_intent=active_intent,
                                intent_dup_hits=intent_dup_hits,
                                intent_retired_ids=intent_retired_ids,
                                intent_remaining=intent_remaining,
                                intent_assignments=intent_assignments,
                                slot_key=slot_key,
                                intent_diagnostics=intent_diagnostics,
                                dup_match=dup_match,
                                target_difficulty=slot.target_difficulty,
                                usage_questions=usage_qs,
                            )
                            if extra_fb:
                                feedback = f"{feedback}\n\n{extra_fb}"
                        elif (
                            variety_counts_toward_intent_retirement(variety_diag)
                            and active_intent
                        ):
                            intent_diagnostics["variety_low_novelty_retries"] = (
                                int(
                                    intent_diagnostics.get("variety_low_novelty_retries")
                                    or 0
                                )
                                + 1
                            )
                            active_intent, extra_fb, _retired = apply_duplicate_intent_policy(
                                active_intent=active_intent,
                                intent_dup_hits=intent_dup_hits,
                                intent_retired_ids=intent_retired_ids,
                                intent_remaining=intent_remaining,
                                intent_assignments=intent_assignments,
                                slot_key=slot_key,
                                intent_diagnostics=intent_diagnostics,
                                dup_match=dup_match,
                                target_difficulty=slot.target_difficulty,
                                usage_questions=usage_qs,
                            )
                            if extra_fb:
                                feedback = f"{feedback}\n\n{extra_fb}"
                        elif active_intent:
                            family = classify_academic_failure_family(reasons)
                            if family:
                                active_intent, extra_fb, _retired = (
                                    apply_academic_failure_intent_policy(
                                        active_intent=active_intent,
                                        failure_family=family,
                                        intent_family_hits=intent_family_hits,
                                        intent_retired_ids=intent_retired_ids,
                                        intent_remaining=intent_remaining,
                                        intent_assignments=intent_assignments,
                                        slot_key=slot_key,
                                        intent_diagnostics=intent_diagnostics,
                                        target_difficulty=slot.target_difficulty,
                                        usage_questions=usage_qs,
                                        rejection_reasons=reasons,
                                    )
                                )
                                if extra_fb:
                                    feedback = f"{feedback}\n\n{extra_fb}"
                # Refresh strategy for subsequent attempts using updated avoidance
                if bank_batch_mode:
                    if prev_intent_fp and new_fp and new_fp != prev_intent_fp:
                        async with lock:
                            diagnostics["duplicate_retries_changed_intent"] = (
                                int(diagnostics.get("duplicate_retries_changed_intent") or 0)
                                + 1
                            )
                    if new_fp:
                        prev_intent_fp = new_fp
                    async with lock:
                        # provisional append for avoidance rebuild
                        tmp_rec = attach_variety_diagnostics(
                            build_rejected_attempt_record(
                                slot=slot,
                                attempt=MAX_SLOT_ATTEMPTS + attempt,
                                generated=generated,
                                rejection_reasons=reasons,
                                rewrite_instruction=feedback,
                                duplicate_match=dup_match,
                                source_chunk_index=prev_chunk_index,
                                phase=f"refill_{refill_phase}",
                            ),
                            variety_diag,
                            active_intent,
                        )
                        avoidance = build_slot_avoidance_history(
                            rejected_log + [tmp_rec], qn
                        )
                        slot_avoidance[qn] = avoidance
                    strategy = classify_bank_refill_strategy(reasons, avoidance)
                    soft_for_strategy = soft_hints or soft_for_strategy
                    feedback = (
                        f"{feedback}\n\n"
                        f"{format_bank_batch_strategy_guidance(strategy, slot=slot, avoidance=avoidance, soft_coverage_hints=soft_for_strategy)}"
                    )
                    if dup_match and "Do not paraphrase this question" not in feedback:
                        feedback = (
                            f"{feedback}\n\n"
                            f"{format_bank_batch_duplicate_retry_guidance(dup_match)}"
                        )
                elif dup_match and "Do not paraphrase" in dup_feedback:
                    if "Do not paraphrase this question" not in feedback:
                        feedback = f"{feedback}\n\n{format_bank_batch_duplicate_retry_guidance(dup_match)}"

                async with lock:
                    bump_reason_counts(diagnostics, reasons)
                    if bank_batch_mode:
                        rejected_log.append(
                            attach_variety_diagnostics(
                                build_rejected_attempt_record(
                                    slot=slot,
                                    attempt=MAX_SLOT_ATTEMPTS + attempt,
                                    generated=generated,
                                    rejection_reasons=reasons,
                                    rewrite_instruction=feedback,
                                    duplicate_match=dup_match,
                                    source_chunk_index=prev_chunk_index,
                                    phase=f"refill_{refill_phase}",
                                ),
                                variety_diag,
                                active_intent,
                            )
                        )
                    else:
                        rejected_log.append(
                            {
                                "question_number": qn,
                                "attempt": MAX_SLOT_ATTEMPTS + attempt,
                                "rewrite_instruction": "; ".join(reasons),
                                "chapter": slot.chapter,
                                "target_difficulty": slot.target_difficulty,
                                "answer_type": slot.answer_type,
                            }
                        )
                logger.info(
                    f"Q{qn} refill rejected attempt {attempt}/{max_refill}: "
                    + "; ".join(reasons)
                )
                if decide_slot_outcome(False, attempt, max_refill) == "retry":
                    continue
                break

        if outcome != "accept":
            entry = last_record or {
                "question_number": qn,
                "chapter": slot.chapter,
                "chapter_title": slot.chapter_title,
                "target_difficulty": slot.target_difficulty,
                "answer_type": slot.answer_type,
                "grade": slot.grade,
                "validation_status": "needs_manual_review",
                "validation_reasons": [feedback or "refill failed"],
                "generation_attempts": MAX_SLOT_ATTEMPTS + max_refill,
            }
            entry["validation_status"] = "needs_manual_review"
            # Preserve frozen constraints on exhausted slots
            entry["target_difficulty"] = slot.target_difficulty
            entry["answer_type"] = slot.answer_type
            entry["chapter"] = slot.chapter
            async with lock:
                still_failed.append(entry)
                diagnostics["slots_exhausted"] = int(
                    diagnostics.get("slots_exhausted") or 0
                ) + 1
            logger.warning(
                f"Q{qn} still needs_manual_review after {max_refill} refill attempts"
            )

    await asyncio.gather(*[_refill_one(f) for f in failed])

    logger.info(
        f"Refill complete ({refill_phase}): {len(failed)} attempted, "
        f"{len(failed) - len(still_failed)} recovered, "
        f"{len(still_failed)} still failed"
    )
    return {
        "approved": approved,
        "failed_slots": still_failed,
        "used_stems": used_stems,
        "rejected_with_feedback": rejected_log,
        "raw_questions": approved,
        "deduplicated": approved,
        "refill_diagnostics": diagnostics,
        "cost_diagnostics": finalize_bank_cost_diagnostics(cost_diagnostics),
        "slot_avoidance_by_number": {
            str(k): v for k, v in slot_avoidance.items()
        },
        "bank_intent_assignments": intent_assignments,
        "bank_intent_remaining": intent_remaining,
        "bank_intent_catalog": list(state.get("bank_intent_catalog") or []),
        "intent_diagnostics": intent_diagnostics,
        "batch_budget_exhausted_reason": state.get("batch_budget_exhausted_reason"),
    }


# ---------------------------------------------------------------------------
# Assemble + coverage (deterministic; no LLM for counts)
# ---------------------------------------------------------------------------

async def assemble_paper(state: PaperState) -> dict:
    """Assemble approved questions in slot/question_number order."""
    approved = sorted(state.get("approved") or [], key=lambda q: int(q.get("question_number") or 0))
    target_marks = int(state.get("target_marks") or len(approved))
    pass_percentage = int(state.get("pass_percentage") or 70)
    marks_each = 1
    questions = []
    answer_key = []
    for q in approved:
        q_num = int(q.get("question_number") or 0)
        entry = {
            "question_number": q_num,
            "question": q.get("question", ""),
            "type": q.get("type", "mcq"),
            "answer_type": q.get("answer_type"),
            "options": q.get("options"),
            "correct_indices": q.get("correct_indices"),
            "marks": marks_each,
            "topic": q.get("topic", state.get("topic")),
            "sub_topic": q.get("sub_topic"),
            "grade": q.get("grade"),
            "chapter": q.get("chapter"),
            "chapter_title": q.get("chapter_title"),
            "section_ref": q.get("section_ref") or q.get("chapter_title"),
            "difficulty": q.get("validated_cognitive_difficulty") or q.get("target_difficulty"),
            "target_difficulty": q.get("target_difficulty"),
            "validated_cognitive_difficulty": q.get("validated_cognitive_difficulty"),
            "difficulty_score": q.get("difficulty_score"),
            "difficulty_scores": q.get("difficulty_scores"),
            "validation_status": q.get("validation_status"),
            "validation_reasons": q.get("validation_reasons") or [],
            "generation_attempts": q.get("generation_attempts"),
            "explanation": q.get("explanation", ""),
            "answer": q.get("answer", ""),
            # Blind-solver / quality validation (from _compose_question_record)
            "blind_solver_answer": q.get("blind_solver_answer", "N/A (not persisted)"),
            "answer_agreement": q.get("answer_agreement", "N/A (not persisted)"),
            "information_sufficient": q.get(
                "information_sufficient", "N/A (not persisted)"
            ),
            "arithmetic_consistent": q.get(
                "arithmetic_consistent", "N/A (not persisted)"
            ),
            "no_unsupported_claims": q.get(
                "no_unsupported_claims", "N/A (not persisted)"
            ),
            "option_defensibility": q.get(
                "option_defensibility", "N/A (not persisted)"
            ),
            "distractors_ok": q.get("distractors_ok", "N/A (not persisted)"),
            "terminology_grounded": q.get(
                "terminology_grounded", "N/A (not persisted)"
            ),
        }
        questions.append(entry)
        answer_key.append(
            {
                "question_number": q_num,
                "question": q.get("question", ""),
                "answer": q.get("answer", ""),
                "explanation": q.get("explanation", ""),
                "marks": marks_each,
                "section_ref": q.get("section_ref") or q.get("chapter_title"),
            }
        )
    paper = {
        "sections": [{"section_name": "mcq", "questions": questions}],
        "total_marks": marks_each * len(questions),
        "question_count": len(questions),
        "pass_percentage": pass_percentage,
        "target_marks": target_marks,
        "grade": state.get("grade") or "",
        "subject": state.get("subject") or state.get("topic") or "",
        "failed_slots": state.get("failed_slots") or [],
    }
    logger.info(f"Assembler: {len(questions)} approved, {len(state.get('failed_slots') or [])} failed slots")
    return {
        "final_paper": paper,
        "answer_key": answer_key,
    }


COVERAGE_SYSTEM = """You are a curriculum coverage reporter for an exam paper.

Given the assembled questions and curriculum objectives:
1. List objectives that ARE covered by at least one question in covered_topics
2. List objectives with zero coverage in gaps

Do not validate marks, difficulty counts, or answer types.
Do not invent extra objectives. Use the provided objective list.
If the only objective is a generic subject understanding goal, judge whether the paper addresses that subject."""


async def report_coverage(state: PaperState) -> dict:
    """LLM curriculum coverage report. Separate from the deterministic blueprint audit."""
    topic = state.get("topic") or state.get("subject") or "the subject"
    objectives = list(state.get("curriculum_objectives") or [])
    if not objectives:
        objectives = [f"Understand core concepts of {topic}"]

    final_paper = state.get("final_paper") or {}
    approved = state.get("approved") or []
    summary = [
        {
            "question_number": q.get("question_number"),
            "question": q.get("question"),
            "topic": q.get("topic"),
            "sub_topic": q.get("sub_topic"),
            "chapter_title": q.get("chapter_title"),
        }
        for q in approved
    ]
    user_prompt = f"""Report curriculum coverage for this paper.

Curriculum objectives: {json.dumps(objectives)}
Subject/topic: {topic}

Questions:
{json.dumps(summary, indent=2)}
"""
    try:
        result: CoverageReportOutput = await _invoke_structured(
            COVERAGE_SYSTEM,
            user_prompt,
            state.get("reviewer_model") or state.get("generator_model"),
            CoverageReportOutput,
            max_tokens=2048,
            temperature=0.2,
        )
        covered = result.covered_topics or []
        gaps = result.gaps or []
        logger.info(f"Coverage report: {len(covered)} covered, {len(gaps)} gaps")
        return {"covered_topics": covered, "coverage_gaps": gaps}
    except Exception as e:
        logger.warning(f"Coverage reporter failed, using question topics: {e}")
        topics: List[str] = []
        for q in approved:
            label = q.get("topic") or q.get("chapter_title")
            if label and label not in topics:
                topics.append(label)
        return {"covered_topics": topics, "coverage_gaps": []}


async def audit_assembled_paper(state: PaperState) -> dict:
    """Deterministic blueprint audit. Does not call an LLM for numeric checks."""
    preset = state.get("effective_preset") or build_effective_preset(state.get("blueprint_preset"))
    questions = []
    for section in (state.get("final_paper") or {}).get("sections", []):
        questions.extend(section.get("questions") or [])
    failed = state.get("failed_slots") or []
    result = audit_paper(questions, preset, options_per_question=5, require_validated=True)
    if failed:
        result["ok"] = False
        result["errors"] = list(result.get("errors") or []) + [
            f"{len(failed)} slot(s) need manual review: "
            + ", ".join(f"Q{f.get('question_number')}" for f in failed)
        ]
    logger.info(f"Paper audit ok={result['ok']} errors={result.get('errors')}")
    return {"audit": result}


async def persist_question_bank(state: PaperState) -> dict:
    """Save approved questions to the persistent bank (existing behaviour)."""
    audit = state.get("audit") or {}
    approved = state.get("approved") or []
    if not audit.get("ok"):
        logger.warning("Skipping question-bank save because paper audit failed")
        return {}
    if approved:
        try:
            await QuestionRecord.save_batch(approved)
            logger.info(f"Saved {len(approved)} questions to bank")
        except Exception as e:
            logger.warning(f"Failed to save to question bank: {e}")
    return {}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _needs_refill(state: PaperState) -> str:
    """Route after fill_slots: refill if there are failed slots, else assemble."""
    if state.get("failed_slots"):
        return "refill_slots"
    return "assemble"


def build_question_paper_graph():
    graph = StateGraph(PaperState)

    graph.add_node("prepare", prepare_blueprint)
    graph.add_node("fill_slots", fill_slots)
    graph.add_node("refill_slots", refill_slots)
    graph.add_node("assemble", assemble_paper)
    graph.add_node("coverage", report_coverage)
    graph.add_node("audit", audit_assembled_paper)
    graph.add_node("persist_bank", persist_question_bank)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "fill_slots")
    graph.add_conditional_edges("fill_slots", _needs_refill, {
        "refill_slots": "refill_slots",
        "assemble": "assemble",
    })
    graph.add_edge("refill_slots", "assemble")
    graph.add_edge("assemble", "coverage")
    graph.add_edge("coverage", "audit")
    graph.add_edge("audit", "persist_bank")
    graph.add_edge("persist_bank", END)

    return graph.compile()


question_paper_graph = build_question_paper_graph()
