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
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.question_bank import QuestionRecord
from open_notebook.graphs.question_bank_intent import (
    ADHERENCE_PARTIAL,
    INTENT_DRIFT_REJECTION,
    apply_duplicate_intent_policy,
    classify_intent_adherence,
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
    rejection_is_cognitive,
    rejection_is_distractor_or_answer,
    rejection_is_duplicate,
    replenish_running_pool,
    select_closest_bank_stems_for_intent,
    should_early_reject_for_intent_drift,
    should_replenish_catalog,
    take_next_unused_intent,
)
from open_notebook.graphs.question_paper_blueprint import (
    CHAPTER_CHUNK_SIZE,
    COGNITIVE_CRITERIA,
    DIFFICULTY_DEFINITIONS,
    MAX_REFILL_ATTEMPTS,
    MAX_SLOT_ATTEMPTS,
    MAX_SLOT_CONCURRENCY,
    VALIDATOR_CRITERION_RUBRIC,
    QuestionSlot,
    apply_independent_validation,
    audit_paper,
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
    format_underused_concept_hints,
    generator_structural_self_check,
    is_bank_diversity_planner_enabled,
    is_near_duplicate,
    normalize_difficulty,
    plan_bank_batch_diversity,
    record_bank_cost_stage,
    run_bank_batch_early_gates,
    select_bank_batch_forbidden_stems,
    select_blind_solver_source_snippet,
    select_source_grounding_window,
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
    reason: str = ""


class BlindSolverOutput(BaseModel):
    """Stage 1: solve without seeing the answer key."""
    independently_derived_indices: List[int] = Field(
        description="0-based indices of every option the solver believes is correct"
    )
    option_analysis: List[OptionDefensibility] = Field(
        description="Per-option defensibility analysis for A–E"
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
    terminology_issues: List[str] = Field(
        default_factory=list,
        description="Up to a few specialized terms that were not clearly present in the chapter excerpt (if any).",
    )
    solver_reasoning: str = Field(
        default="", description="Brief reasoning for the derived answer"
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
):
    """
    Invoke a model with structured output enforcement via with_structured_output().
    Falls back to plain JSON extraction if the provider does not support it.
    """
    try:
        model = await provision_langchain_model(
            system_prompt,
            model_id,
            "chat",
            max_tokens=max_tokens,
            temperature=temperature,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            structured = model.with_structured_output(output_schema)
            result = await structured.ainvoke(messages)
            return result
        except (NotImplementedError, AttributeError):
            logger.debug(
                f"Structured output not supported, falling back to plain JSON for {output_schema.__name__}"
            )
            response = await model.ainvoke(messages)
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            raw = json.loads(_extract_json(str(content)))
            return output_schema.model_validate(raw)
    except Exception as e:
        exc_class, message = classify_error(e)
        raise exc_class(message) from e


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
- Set topic and sub_topic from the chapter content.
- Explanation must justify the correct answer(s) and why the other options are wrong.
"""

BOOK_GROUNDED_RULES = """
BOOK-GROUNDED MODE:
Derive the question exclusively from the CHAPTER CONTENT provided for this slot.
- Every fact, concept, example, and distractor must be grounded in that chapter content.
- Do NOT invent information that is not in the chapter content.
- Later or earlier parts of the book that are not in this chapter content are out of scope.
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

BLIND_SOLVER_SYSTEM = """You are an independent exam-question solver. You have NOT seen the answer key.

TASK:
1. Read the question stem and all five options (A-E).
2. Using ONLY the stem, options, and any chapter content provided, determine which option(s) are correct.
3. For EACH option A-E, decide whether it is defensible (could be correct) and give a brief reason.
4. Check whether the stem provides ENOUGH INFORMATION to uniquely determine the answer.
5. Re-verify any arithmetic or numerical claims in the stem and options.
6. Flag any absolute or misleading claims not supported by the provided material (e.g. "guaranteed returns", "always grows faster", "banks guarantee wealth").
7. Specialized terminology grounding: identify specialized terms/phrases used in the stem and check whether each is explicitly present in the provided chapter excerpt. If not, set terminology_grounded=false and list a few terminology_issues.

RULES:
- Do NOT assume any option is correct. Solve from first principles.
- For Single Correct: exactly ONE option should be defensible.
- For Multiple Correct: the question wording should indicate multiple answers; at least two should be defensible.
- IMPORTANT (Single Correct defensibility): mark an option defensible only if it fully answers the full objective of the stem. Directionally true but incomplete options are NOT defensible.
- If the stem lacks information to uniquely determine the answer, set information_sufficient to false.
- If any number (percentage, amount, calculation) is inconsistent between stem, options, or implied logic, set arithmetic_consistent to false.
- If the question makes unsupported absolute financial/factual claims, set no_unsupported_claims to false.
- If terminology_grounded is false, treat the item as invalid (specialized terminology not supported by the chapter excerpt).

Return structured output. Do not include chain-of-thought outside solver_reasoning."""

VALIDATOR_SYSTEM = f"""You are an independent exam-question validator. You did not write the question.

Score the question on eight cognitive criteria from 1 to 3. Do NOT compute a total.
Do NOT guess or report an overall Easy/Medium/Difficult label.

{VALIDATOR_CRITERION_RUBRIC}

Also judge quality as booleans:
- content_valid: tests curriculum-appropriate content for the given grade and chapter
- answer_valid: marked answers are actually correct; unmarked options are incorrect
- grade_appropriate: vocabulary, examples, and reasoning fit the stated grade
- distractors_ok: incorrect options represent realistic, grade-appropriate misconceptions. Reject if distractors are obviously absurd, irrelevant, nonsensical, or trivially eliminated without understanding the concept.
- unambiguous: only one defensible reading of the question
- language_clear: clear, grade-appropriate language without trick wording; difficulty must come from reasoning, not harder vocabulary
- grounded_in_material: true if chapter content is provided and the question stays inside it; true if no chapter content was provided
- explanation_valid: explanation correctly defends the answers AND is consistent with the stem and options

For Multiple Correct questions, do NOT fail the item merely because more than one option is correct.
For Single Correct questions, fail answer_valid if more than one option is defensible.

Return structured scores and flags. Put concise rejection reasons in `reasons` when any check fails.
Do not include chain-of-thought.
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
) -> Optional[dict]:
    book_grounded = bool(state.get("book_grounded") and chapter_excerpt)
    system = GENERATOR_SYSTEM + (BOOK_GROUNDED_RULES if book_grounded else TOPIC_ONLY_RULES)
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
        )
    user_prompt = f"""Generate one exam question for this slot.

Grade: {slot.grade or 'not specified'}
Subject: {slot.subject}
Exam topic: {state.get('topic') or slot.subject}
{objectives_block}Question number: {slot.question_number}
Chapter: {slot.chapter} — {slot.chapter_title}
Target cognitive difficulty: {slot.target_difficulty.upper()}
Answer type: {slot.answer_type} ({answer_rule})
Language: {state.get('language') or 'en'}
Options: exactly 5 (A–E)
{topic_meta_block}{easy_cal_block}{intent_block}{novelty_block}{diversity_block}{coverage_block}
Forbidden opening stems: [{forbidden_str}]
{feedback_block}{chapter_block}
Follow the cognitive difficulty definition for {slot.target_difficulty.upper()} exactly.
Use grade-appropriate language for grade "{slot.grade or 'unspecified'}".
"""
    try:
        result: SlotGeneratedQuestion = await _invoke_structured(
            system,
            user_prompt,
            state.get("generator_model"),
            SlotGeneratedQuestion,
            max_tokens=2048,
            temperature=0.7,
        )
        data = result.model_dump()
        options = list(data.get("options") or [])
        if len(options) > 5:
            options = options[:5]
        data["options"] = options
        return data
    except Exception as e:
        logger.error(f"Generator failed for slot {slot.question_number}: {e}")
        return None


async def _blind_solve(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
) -> Optional[BlindSolverOutput]:
    """Stage 1: solve without seeing the answer key, explanation, or target difficulty."""
    source_text = chapter_excerpt or ""
    if state.get("bank_batch_mode"):
        source_text = select_blind_solver_source_snippet(
            chapter_excerpt or "",
            str(generated.get("question") or ""),
            list(generated.get("options") or []),
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
Determine which option(s) are correct. Analyse each option A-E for defensibility.
Check information sufficiency, arithmetic consistency, and unsupported claims.
"""
    try:
        return await _invoke_structured(
            BLIND_SOLVER_SYSTEM,
            user_prompt,
            state.get("reviewer_model") or state.get("generator_model"),
            BlindSolverOutput,
            max_tokens=2048,
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"Blind solver failed for slot {slot.question_number}: {e}")
        return None


async def _validate_cognitive_quality(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
) -> Tuple[dict, dict]:
    """Stage 2: cognitive scoring + quality flags (receives the full answer key)."""
    source_text = chapter_excerpt or ""
    if state.get("bank_batch_mode") and source_text:
        probe = " ".join(
            [
                str(generated.get("question") or ""),
                str(generated.get("topic") or ""),
                str(generated.get("sub_topic") or ""),
                str(generated.get("explanation") or ""),
            ]
        )
        source_text = select_source_grounding_window(source_text, probe)
    chapter_block = ""
    if source_text:
        chapter_block = (
            f"\n--- CHAPTER CONTENT ---\n{source_text}\n--- END CHAPTER CONTENT ---\n"
        )
    user_prompt = f"""Validate this exam question. Do not infer a requested difficulty label.

Grade: {slot.grade or 'not specified'}
Subject: {slot.subject}
Chapter: {slot.chapter} — {slot.chapter_title}
Answer type (requested): {slot.answer_type}

Question: {generated.get('question')}
Options:
{json.dumps(generated.get('options') or [], indent=2)}
Marked correct_indices (0-based): {generated.get('correct_indices')}
Stated answer: {generated.get('answer')}
Explanation: {generated.get('explanation')}
Topic / sub-topic: {generated.get('topic')} / {generated.get('sub_topic')}
{chapter_block}
Score the eight criteria 1-3. Set the quality booleans. Do not total the scores.
"""
    try:
        result: IndependentValidatorOutput = await _invoke_structured(
            VALIDATOR_SYSTEM,
            user_prompt,
            state.get("reviewer_model") or state.get("generator_model"),
            IndependentValidatorOutput,
            max_tokens=2048,
            temperature=0.2,
        )
        flags = result.model_dump()
        scores = flags.pop("criterion_scores")
        return scores, flags
    except Exception as e:
        logger.error(f"Cognitive validator failed for slot {slot.question_number}: {e}")
        scores = {k: 1 for k in COGNITIVE_CRITERIA}
        flags = {
            "content_valid": False,
            "answer_valid": False,
            "grade_appropriate": False,
            "distractors_ok": False,
            "unambiguous": False,
            "language_clear": False,
            "grounded_in_material": False,
            "explanation_valid": False,
            "reasons": [f"validator error: {e}"],
        }
        return scores, flags


async def _validate_slot_independently(
    slot: QuestionSlot,
    generated: dict,
    state: PaperState,
    chapter_excerpt: str,
    existing_texts: List[str],
    existing_questions: Optional[List[dict]] = None,
    cost_diagnostics: Optional[dict] = None,
    cost_lock: Optional[asyncio.Lock] = None,
) -> dict:
    """Two-stage validation: blind solve (no answer key) then cognitive + quality."""
    t0 = time.perf_counter()
    solver_result = await _blind_solve(slot, generated, state, chapter_excerpt)
    blind_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    scores, flags = await _validate_cognitive_quality(
        slot, generated, state, chapter_excerpt
    )
    cog_ms = (time.perf_counter() - t1) * 1000.0

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

        if cost_lock is not None:
            async with cost_lock:
                await _bump()
        else:
            await _bump()

    solver_data = None
    if solver_result:
        solver_data = solver_result.model_dump()

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
            )
            async with lock:
                state["bank_intent_catalog"] = new_cat
                intent_remaining[:] = new_rem
        if not active:
            async with lock:
                nxt = take_next_unused_intent(
                    intent_remaining,
                    retired_ids=intent_retired_ids,
                    assigned_values=list(intent_assignments.values()),
                    target_difficulty=target_difficulty,
                    diagnostics=intent_diagnostics,
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
                )
                if state.get("bank_batch_mode"):
                    async with lock:
                        cost_diagnostics["generated_attempts"] = (
                            int(cost_diagnostics.get("generated_attempts") or 0) + 1
                        )
                        record_bank_cost_stage(
                            cost_diagnostics,
                            "generate",
                            (time.perf_counter() - t_gen) * 1000.0,
                        )
                if not generated:
                    feedback = "Generation failed; rewrite a complete MCQ with five options A–E."
                    outcome = decide_slot_outcome(False, attempt, max_attempts)
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
                        validation = await _validate_slot_independently(
                            slot,
                            generated,
                            state,
                            excerpt,
                            existing_texts,
                            existing_questions=existing_qs,
                            cost_diagnostics=cost_diagnostics,
                            cost_lock=lock,
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
                    )

                record = _compose_question_record(slot, generated, validation, attempt)
                if state.get("bank_batch_mode") and prev_chunk_index is not None:
                    record["source_chunk_index"] = prev_chunk_index
                last_record = record
                stem = " ".join((generated.get("question") or "").split()[:4])
                prev_intent_words = _extract_intent_words(generated.get("question", ""))

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
                # Step 8: duplicate keeps same intent until repeated exhaustion
                if intent_planner_on:
                    async with lock:
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
                            )
                            if extra_fb:
                                feedback = f"{feedback}\n\n{extra_fb}"
                        elif rejection_is_cognitive(reasons) and active_intent:
                            feedback = (
                                f"{feedback}\n\n"
                                f"{cognitive_form_correction_hint(active_intent, slot.target_difficulty)}"
                            )
                        elif rejection_is_distractor_or_answer(reasons) and active_intent:
                            # Keep same intent; reinforce in feedback
                            feedback = (
                                f"{feedback}\n\n"
                                "INTENT RETRY: Keep the same assigned concept/objective; "
                                "fix distractors/answer validity only."
                            )
                async with lock:
                    if state.get("bank_batch_mode"):
                        rejected_log.append(
                            build_rejected_attempt_record(
                                slot=slot,
                                attempt=attempt,
                                generated=generated,
                                rejection_reasons=reasons,
                                rewrite_instruction=feedback,
                                duplicate_match=dup_match,
                                source_chunk_index=prev_chunk_index,
                                phase="fill",
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
            )
            async with lock:
                state["bank_intent_catalog"] = new_cat
                intent_remaining[:] = new_rem
        if not active:
            async with lock:
                nxt = take_next_unused_intent(
                    intent_remaining,
                    retired_ids=intent_retired_ids,
                    assigned_values=list(intent_assignments.values()),
                    target_difficulty=target_difficulty,
                    diagnostics=intent_diagnostics,
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
                )
                if bank_batch_mode:
                    async with lock:
                        cost_diagnostics["generated_attempts"] = (
                            int(cost_diagnostics.get("generated_attempts") or 0) + 1
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
                        validation = await _validate_slot_independently(
                            slot,
                            generated,
                            state,
                            excerpt,
                            existing_texts,
                            existing_questions=existing_qs,
                            cost_diagnostics=cost_diagnostics,
                            cost_lock=lock,
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
                    )

                record = _compose_question_record(
                    slot, generated, validation, MAX_SLOT_ATTEMPTS + attempt
                )
                if bank_batch_mode and prev_chunk_index is not None:
                    record["source_chunk_index"] = prev_chunk_index
                last_record = record
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
                # Step 8: duplicate keeps same intent until repeated exhaustion
                if intent_planner_on:
                    async with lock:
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
                            )
                            if extra_fb:
                                feedback = f"{feedback}\n\n{extra_fb}"
                        elif rejection_is_cognitive(reasons) and active_intent:
                            feedback = (
                                f"{feedback}\n\n"
                                f"{cognitive_form_correction_hint(active_intent, slot.target_difficulty)}"
                            )
                        elif rejection_is_distractor_or_answer(reasons) and active_intent:
                            feedback = (
                                f"{feedback}\n\n"
                                "INTENT RETRY: Keep the same assigned concept/objective; "
                                "fix distractors/answer validity only."
                            )
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
                        tmp_rec = build_rejected_attempt_record(
                            slot=slot,
                            attempt=MAX_SLOT_ATTEMPTS + attempt,
                            generated=generated,
                            rejection_reasons=reasons,
                            rewrite_instruction=feedback,
                            duplicate_match=dup_match,
                            source_chunk_index=prev_chunk_index,
                            phase=f"refill_{refill_phase}",
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
                            build_rejected_attempt_record(
                                slot=slot,
                                attempt=MAX_SLOT_ATTEMPTS + attempt,
                                generated=generated,
                                rejection_reasons=reasons,
                                rewrite_instruction=feedback,
                                duplicate_match=dup_match,
                                source_chunk_index=prev_chunk_index,
                                phase=f"refill_{refill_phase}",
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
