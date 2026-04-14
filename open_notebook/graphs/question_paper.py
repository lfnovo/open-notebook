"""
Question Paper Generator — multi-agent LangGraph pipeline.

Five-agent architecture:
  Generator → Deduplicator → Quality Reviewer → Assembler → Validator + Answer Key

Each agent receives only the context it needs, preventing pattern convergence
that degrades quality when all prior questions accumulate in a single prompt.
"""

import json
import re
from typing import List, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.question_bank import QuestionRecord
from open_notebook.utils.error_classifier import classify_error


# ---------------------------------------------------------------------------
# Structured output schemas (one per agent)
# ---------------------------------------------------------------------------

class GeneratedQuestion(BaseModel):
    question: str
    type: Literal["mcq", "short", "scenario", "calculation", "definition"]
    options: Optional[List[str]] = Field(default=None, description="4 options for MCQ only")
    answer: str
    explanation: str
    topic: str
    difficulty: Literal["easy", "medium", "hard"]

class GeneratorOutput(BaseModel):
    questions: List[GeneratedQuestion]

class DeduplicatorOutput(BaseModel):
    removed_indices: List[int] = Field(default_factory=list, description="0-based indices of questions to remove")

class ReviewScores(BaseModel):
    clarity: int
    distractor_quality: int
    difficulty_match: int
    curriculum_alignment: int

class QuestionReview(BaseModel):
    question_id: int
    verdict: Literal["PASS", "FAIL"]
    scores: ReviewScores
    rewrite_instruction: Optional[str] = None

class ReviewerOutput(BaseModel):
    reviews: List[QuestionReview]

class SectionPlan(BaseModel):
    section_name: str
    indices: List[int]
    marks_per_question: int

class AssemblerOutput(BaseModel):
    plan: List[SectionPlan]

class AnswerKeyEntry(BaseModel):
    question_number: int
    question: str
    answer: str
    explanation: str
    marks: int

class ValidatorOutput(BaseModel):
    covered_topics: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    answer_key: List[AnswerKeyEntry] = Field(default_factory=list)
    marks_total: int = 0
    is_valid: bool = True


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class PaperState(TypedDict):
    topic: str
    difficulty: str                    # easy | medium | hard
    target_marks: int
    section_config: dict               # e.g. {"mcq": 10, "short": 5, "scenario": 3}
    curriculum_objectives: List[str]   # optional list of curriculum points to cover
    generator_model: Optional[str]     # model id overrides
    reviewer_model: Optional[str]
    book_content: Optional[str]        # extracted text from uploaded book (None = no book)
    used_stems: List[str]              # running list of question openers
    raw_questions: List[dict]
    deduplicated: List[dict]
    approved: List[dict]
    rejected_with_feedback: List[dict]
    final_paper: dict
    answer_key: List[dict]
    coverage_gaps: List[str]
    covered_topics: List[str]
    retry_count: int


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
                        return text[start:i + 1]
    return text


async def _invoke_structured(
    system_prompt: str,
    user_prompt: str,
    model_id: Optional[str],
    output_schema: type,
    *,
    max_tokens: int = 4096,
):
    """
    Invoke a model with structured output enforcement via with_structured_output().
    Falls back to plain JSON extraction if the provider does not support it.
    Returns a parsed instance of output_schema, or raises on total failure.
    """
    try:
        model = await provision_langchain_model(
            system_prompt,
            model_id,
            "chat",
            max_tokens=max_tokens,
            temperature=0.7,
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
            # Provider doesn't support structured output — fall back to plain call + JSON parse
            logger.debug(f"Structured output not supported, falling back to plain JSON for {output_schema.__name__}")
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


# ---------------------------------------------------------------------------
# Agent 1 — Generator
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM = """You are an expert question generator for educational exams.

MANDATORY VARIETY RULES:
- Rotate question types: definition → application → analysis → scenario → calculation
- Never start a question with a stem from the forbidden list provided
- For MCQs: all 3 distractors must be plausible to someone with partial knowledge
- Distribute difficulty: 40% recall, 40% application, 20% analysis
{book_instruction}
Return a list of questions in the `questions` field. Each question must have:
  question, type (mcq|short|scenario|calculation|definition),
  options (list of 4 strings for MCQ only, omit otherwise),
  answer, explanation (1-2 sentences), topic, difficulty (easy|medium|hard)"""

BOOK_INSTRUCTION = """
CRITICAL — BOOK-GROUNDED GENERATION:
You MUST derive ALL questions exclusively from the provided book excerpt below.
- Every question, answer, and distractor must be grounded in facts, concepts, or examples from the text.
- Do NOT invent facts not present in the text.
- Do NOT ask about topics not covered in the provided excerpt.
"""


async def generate_questions(state: PaperState) -> dict:
    """Agent 1: Generate a batch of raw questions."""
    logger.info(f"Generator: topic={state['topic']}, difficulty={state['difficulty']}")

    section_config = state["section_config"]
    total_needed = sum(section_config.values())
    batch_size = min(total_needed + 5, 25)

    # Calculate how many of each type are STILL needed after previous rounds
    already_approved = state.get("approved", [])
    approved_by_type: dict = {}
    for q in already_approved:
        t = q.get("type", "").lower().strip()
        approved_by_type[t] = approved_by_type.get(t, 0) + 1

    still_needed = {
        section: max(0, count - approved_by_type.get(section, 0))
        for section, count in section_config.items()
    }
    total_still_needed = sum(still_needed.values()) or 1  # avoid div by zero

    # Scale still_needed proportionally to batch_size
    batch_config: dict = {}
    for section, needed in still_needed.items():
        n = round(needed / total_still_needed * batch_size)
        if n > 0:
            batch_config[section] = n
    if not batch_config:
        batch_config = {k: 1 for k in section_config}  # safety fallback

    section_breakdown = ", ".join(f"{count} {qtype}" for qtype, count in batch_config.items())

    forbidden = state.get("used_stems", [])
    forbidden_str = ", ".join(f'"{s}"' for s in forbidden[:30]) if forbidden else "none"

    rejected_feedback = state.get("rejected_with_feedback", [])
    retry_context = ""
    if rejected_feedback:
        feedback_items = [
            f"- {r.get('rewrite_instruction', '')}"
            for r in rejected_feedback[:5]
            if r.get("rewrite_instruction")
        ]
        if feedback_items:
            retry_context = (
                "\n\nPrevious batch had issues — apply these specific fixes:\n"
                + "\n".join(feedback_items)
            )

    book_content: Optional[str] = state.get("book_content")
    has_book = bool(book_content and book_content.strip())
    system_prompt = GENERATOR_SYSTEM.format(book_instruction=BOOK_INSTRUCTION if has_book else "")

    MAX_BOOK_CHARS = 12_000
    book_excerpt = ""
    if has_book:
        book_excerpt = (
            f"\n\n--- BOOK EXCERPT (generate questions ONLY from this content) ---\n"
            f"{book_content[:MAX_BOOK_CHARS]}"
            + ("\n[... excerpt truncated ...]" if len(book_content) > MAX_BOOK_CHARS else "")
            + "\n--- END OF EXCERPT ---\n"
        )

    user_prompt = f"""Generate exactly {sum(batch_config.values())} questions for this exam batch.

Topic: {state['topic']}
Difficulty: {state['difficulty']}
THIS BATCH must contain EXACTLY: {section_breakdown}
  — Do NOT deviate from these counts or types.
Total marks target: {state['target_marks']}

Forbidden stems (do NOT start any question with these): [{forbidden_str}]
{retry_context}{book_excerpt}
Strictly match the batch breakdown above. Each question's `type` field must match its section."""

    try:
        result: GeneratorOutput = await _invoke_structured(
            system_prompt, user_prompt, state.get("generator_model"),
            GeneratorOutput, max_tokens=8192,
        )
        questions = [q.model_dump() for q in result.questions]
        new_stems = [" ".join(q.get("question", "").split()[:4]) for q in questions if q.get("question")]
        used_stems = list(state.get("used_stems", [])) + new_stems
        logger.info(f"Generator: produced {len(questions)} questions")
        return {"raw_questions": questions, "used_stems": used_stems}
    except Exception as e:
        logger.error(f"Generator failed: {e}")
        return {"raw_questions": []}


# ---------------------------------------------------------------------------
# Agent 2 — Deduplicator
# ---------------------------------------------------------------------------

DEDUP_SYSTEM = """You are a deduplication agent for exam questions.

You are given a numbered list of questions. Identify which ones to remove:
1. Exact duplicates within the batch
2. Questions testing the same concept with only surface-level rewording
3. Questions where knowing one answer trivially reveals another's answer

Do NOT remove questions that share a topic but test genuinely different aspects.

Return ONLY `removed_indices`: the 0-based indices of questions to remove.
If nothing should be removed, return an empty list."""


async def deduplicate_questions(state: PaperState) -> dict:
    """Agent 2: Remove semantic near-duplicates."""
    questions = state.get("raw_questions", [])
    if not questions:
        return {"deduplicated": []}

    bank_samples: List[dict] = []
    for q in questions[:3]:
        similar = await QuestionRecord.search_similar(q.get("question", ""), limit=3)
        bank_samples.extend(similar)

    bank_context = ""
    if bank_samples:
        bank_context = "\n\nExisting bank questions (flag overlaps):\n" + json.dumps(
            [{"question": b.get("question", "")} for b in bank_samples[:10]], indent=2
        )

    # Send only question text + index — no need to echo options/answers back
    summary = [{"index": i, "question": q.get("question", ""), "type": q.get("type", "")}
               for i, q in enumerate(questions)]

    user_prompt = f"""Deduplicate these {len(questions)} questions:{bank_context}

Questions (index + text):
{json.dumps(summary, indent=2)}"""

    try:
        result: DeduplicatorOutput = await _invoke_structured(
            DEDUP_SYSTEM, user_prompt, state.get("generator_model"), DeduplicatorOutput,
        )
        remove_set = set(result.removed_indices)
        kept = [q for i, q in enumerate(questions) if i not in remove_set]
        logger.info(f"Deduplicator: kept {len(kept)}/{len(questions)} questions")
        return {"deduplicated": kept}
    except Exception as e:
        logger.error(f"Deduplicator failed, using all questions: {e}")
        return {"deduplicated": questions}


# ---------------------------------------------------------------------------
# Agent 3 — Quality Reviewer
# ---------------------------------------------------------------------------

REVIEWER_SYSTEM = """You are a quality reviewer for exam questions.

Review each question. Score 1-5 on each dimension:
- clarity: unambiguous wording, grammatically correct
- distractor_quality: wrong options are plausible but clearly wrong to experts (MCQ only, else 5)
- difficulty_match: matches the stated difficulty level
- curriculum_alignment: tests the stated topic, not tangential content

FAIL only if 2 or more dimensions score <= 2, or if clarity scores 1 (completely unintelligible).
For FAIL: provide a specific, actionable one-sentence rewrite_instruction.
For PASS: rewrite_instruction can be null.

Return a `reviews` list. Each item: question_id (0-indexed int), verdict (PASS or FAIL),
scores (clarity, distractor_quality, difficulty_match, curriculum_alignment each 1-5),
rewrite_instruction (string or null)."""


async def review_questions(state: PaperState) -> dict:
    """Agent 3: Score questions and return approved/rejected lists."""
    questions = state.get("deduplicated", [])
    if not questions:
        return {"approved": list(state.get("approved", [])), "rejected_with_feedback": []}

    user_prompt = f"""Review these {len(questions)} questions for topic "{state['topic']}" at difficulty "{state['difficulty']}":

{json.dumps(questions, indent=2)}"""

    try:
        result: ReviewerOutput = await _invoke_structured(
            REVIEWER_SYSTEM, user_prompt, state.get("reviewer_model"), ReviewerOutput,
        )
        approved, rejected = [], []
        for review in result.reviews:
            idx = review.question_id
            if 0 <= idx < len(questions):
                q = dict(questions[idx])
                if review.verdict == "PASS":
                    approved.append(q)
                else:
                    q["rewrite_instruction"] = review.rewrite_instruction or ""
                    rejected.append(q)

        if not result.reviews:
            approved = list(questions)

        logger.info(f"Reviewer: approved={len(approved)}, rejected={len(rejected)}")
        return {
            "approved": list(state.get("approved", [])) + approved,
            "rejected_with_feedback": rejected,
        }
    except Exception as e:
        logger.error(f"Reviewer failed, approving all: {e}")
        return {
            "approved": list(state.get("approved", [])) + questions,
            "rejected_with_feedback": [],
        }


# ---------------------------------------------------------------------------
# Agent 4 — Assembler
# ---------------------------------------------------------------------------

ASSEMBLER_SYSTEM = """You are a question paper assembler.

You are given a pool of questions (each with an index), a section config, and a marks target.
Select which question indices go in each section and assign marks per question.

Rules:
- Difficulty ramps within each section: easy first, hard last
- Total marks must equal the target; distribute marks by type/difficulty
- If the pool has fewer questions than requested, use all available
- Prefer matching question type to section name (e.g. mcq-type in mcq section)

Return a `plan` list. Each item: section_name (string), indices (list of ints), marks_per_question (int)."""


def _python_assemble(approved: list, section_config: dict, target_marks: int, topic: str, difficulty: str) -> dict:
    """Pure-Python assembler: distributes approved questions across sections without duplicates."""
    by_type: dict = {}
    for i, q in enumerate(approved):
        t = q.get("type", "").lower().strip()
        by_type.setdefault(t, []).append(i)

    used: set = set()
    sections = []
    q_num = 1

    for section_name, count in section_config.items():
        key = section_name.lower().strip()
        candidates = [i for i in by_type.get(key, []) if i not in used]
        if not candidates:
            candidates = [i for i in range(len(approved)) if i not in used]
        selected = candidates[:count]
        used.update(selected)

        section_qs = []
        for idx in selected:
            q = approved[idx]
            section_qs.append({
                "question_number": q_num,
                "question": q.get("question", ""),
                "type": q.get("type", ""),
                "options": q.get("options"),
                "marks": 1,
                "topic": q.get("topic", topic),
                "difficulty": q.get("difficulty", difficulty),
            })
            q_num += 1
        sections.append({"section_name": section_name, "questions": section_qs})

    return {"sections": sections, "total_marks": target_marks, "question_count": q_num - 1}


async def assemble_paper(state: PaperState) -> dict:
    """Agent 4: Compose the final ordered paper from approved questions."""
    approved = state.get("approved", [])
    if not approved:
        return {"final_paper": {"sections": [], "total_marks": 0, "question_count": 0}}

    section_config = state["section_config"]
    target_marks = state["target_marks"]

    pool_summary = [
        {"index": i, "type": q.get("type", ""), "topic": q.get("topic", ""), "difficulty": q.get("difficulty", "")}
        for i, q in enumerate(approved)
    ]

    user_prompt = f"""Assemble the question paper.

Section config (section_name → questions needed): {json.dumps(section_config)}
Target marks: {target_marks}
Pool: {len(approved)} questions (indices 0–{len(approved)-1})

Question pool:
{json.dumps(pool_summary, indent=2)}"""

    try:
        result: AssemblerOutput = await _invoke_structured(
            ASSEMBLER_SYSTEM, user_prompt, state.get("generator_model"), AssemblerOutput,
        )
        sections = []
        q_num = 1
        total_marks = 0
        for item in result.plan:
            section_qs = []
            for idx in item.indices:
                if 0 <= idx < len(approved):
                    q = approved[idx]
                    section_qs.append({
                        "question_number": q_num,
                        "question": q.get("question", ""),
                        "type": q.get("type", ""),
                        "options": q.get("options"),
                        "marks": item.marks_per_question,
                        "topic": q.get("topic", state["topic"]),
                        "difficulty": q.get("difficulty", state["difficulty"]),
                    })
                    q_num += 1
                    total_marks += item.marks_per_question
            sections.append({"section_name": item.section_name, "questions": section_qs})

        question_count = q_num - 1
        logger.info(f"Assembler: {question_count} questions, {total_marks} marks")
        return {"final_paper": {"sections": sections, "total_marks": total_marks, "question_count": question_count}}
    except Exception as e:
        logger.error(f"Assembler LLM failed ({e}), using Python fallback")
        paper = _python_assemble(approved, section_config, target_marks, state["topic"], state["difficulty"])
        logger.info(f"Assembler fallback: {paper['question_count']} questions")
        return {"final_paper": paper}


# ---------------------------------------------------------------------------
# Agent 5 — Validator + Answer Key
# ---------------------------------------------------------------------------

VALIDATOR_SYSTEM = """You are a curriculum validator and answer key generator.

Given an assembled question paper and curriculum objectives:
1. List objectives WITH coverage in covered_topics
2. List objectives with zero coverage in gaps
3. Generate answer_key: each answer with a 2-sentence explanation
4. Verify marks total

Return:
  covered_topics: list of covered objective strings
  gaps: list of uncovered objective strings
  answer_key: list of {question_number, question, answer, explanation, marks}
  marks_total: int
  is_valid: bool"""


async def validate_and_key(state: PaperState) -> dict:
    """Agent 5: Validate coverage and generate answer key."""
    final_paper = state.get("final_paper", {})
    if not final_paper or not final_paper.get("sections"):
        return {"answer_key": [], "coverage_gaps": [], "covered_topics": []}

    objectives = state.get("curriculum_objectives", [f"Understand core concepts of {state['topic']}"])

    user_prompt = f"""Validate this paper and generate the answer key:

Curriculum objectives: {json.dumps(objectives)}
Target marks: {state['target_marks']}

Paper:
{json.dumps(final_paper, indent=2)}

Approved questions with answers:
{json.dumps(state.get('approved', []), indent=2)}"""

    approved = state.get("approved", [])
    try:
        result: ValidatorOutput = await _invoke_structured(
            VALIDATOR_SYSTEM, user_prompt, state.get("reviewer_model"), ValidatorOutput,
        )

        if approved:
            try:
                await QuestionRecord.save_batch(approved)
                logger.info(f"Saved {len(approved)} questions to bank")
            except Exception as e:
                logger.warning(f"Failed to save to question bank: {e}")

        return {
            "answer_key": [item.model_dump() for item in result.answer_key],
            "coverage_gaps": result.gaps,
            "covered_topics": result.covered_topics,
        }
    except Exception as e:
        logger.error(f"Validator failed: {e}")
        # Fallback: build basic answer key from the paper
        answer_key = []
        q_num = 1
        for section in final_paper.get("sections", []):
            for q in section.get("questions", []):
                matched = next(
                    (a for a in approved if a.get("question") == q.get("question")), {}
                )
                answer_key.append({
                    "question_number": q_num,
                    "question": q.get("question", ""),
                    "answer": matched.get("answer", "See question"),
                    "explanation": matched.get("explanation", ""),
                    "marks": q.get("marks", 1),
                })
                q_num += 1
        return {"answer_key": answer_key, "coverage_gaps": [], "covered_topics": []}


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

async def increment_retry(state: PaperState) -> dict:
    """Increment retry_count before looping back to generate."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def should_retry(state: PaperState) -> str:
    """After review: retry until we have enough approved questions or exhaust retries."""
    approved = state.get("approved", [])
    retry_count = state.get("retry_count", 0)
    total_needed = sum(state["section_config"].values())

    # Done — have enough questions
    if len(approved) >= total_needed:
        return "assemble"

    # Scale max retries with the number of questions needed:
    # allow up to ceil(total_needed / 10) extra rounds, minimum 3, maximum 8
    max_retries = max(3, min(8, -(-total_needed // 10)))  # ceiling division

    if retry_count < max_retries:
        return "increment_retry"

    return "assemble"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_question_paper_graph():
    graph = StateGraph(PaperState)

    graph.add_node("generate", generate_questions)
    graph.add_node("deduplicate", deduplicate_questions)
    graph.add_node("review", review_questions)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("assemble", assemble_paper)
    graph.add_node("validate", validate_and_key)

    graph.add_edge(START, "generate")
    graph.add_edge("generate", "deduplicate")
    graph.add_edge("deduplicate", "review")
    graph.add_conditional_edges(
        "review",
        should_retry,
        {
            "increment_retry": "increment_retry",
            "assemble": "assemble",
        },
    )
    graph.add_edge("increment_retry", "generate")
    graph.add_edge("assemble", "validate")
    graph.add_edge("validate", END)

    return graph.compile()


question_paper_graph = build_question_paper_graph()
