"""Practice exams: build study material, generate exams and grade attempts."""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from open_notebook.domain.exam import Exam, ExamAttempt, ExamQuestion, QuestionResult
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import InvalidInputError
from open_notebook.graphs.exam import (
    generate_exam_questions,
    grade_with_ai,
    normalize_answer,
)

# ~150k tokens: beyond this the material is truncated rather than sent whole.
MAX_MATERIAL_CHARS = 600_000
MAX_QUESTIONS = 50
# Parallel AI grading calls per attempt.
GRADING_CONCURRENCY = 4


async def build_study_material(
    notebook: Notebook, source_ids: Optional[List[str]], include_notes: bool
) -> tuple[str, List[str]]:
    """Concatenate the selected sources (and optionally notes) of a notebook."""
    sources = await notebook.get_sources(include_full_text=True)
    if source_ids:
        wanted = set(source_ids)
        sources = [s for s in sources if s.id in wanted]

    parts: List[str] = []
    used_ids: List[str] = []
    for source in sources:
        if source.full_text and source.full_text.strip():
            parts.append(
                f"## SOURCE: {source.title or source.id}\n\n{source.full_text}"
            )
            used_ids.append(source.id or "")

    if include_notes:
        for note in await notebook.get_notes(include_content=True):
            if note.content and note.content.strip():
                parts.append(f"## NOTE: {note.title or note.id}\n\n{note.content}")

    material = "\n\n".join(parts)
    if not material.strip():
        raise InvalidInputError(
            "The selected sources have no text content to build an exam from."
        )
    if len(material) > MAX_MATERIAL_CHARS:
        logger.warning(
            f"Exam material truncated from {len(material)} to {MAX_MATERIAL_CHARS} chars"
        )
        material = material[:MAX_MATERIAL_CHARS]
    return material, used_ids


async def create_exam(
    *,
    notebook_id: str,
    title: Optional[str],
    source_ids: Optional[List[str]],
    include_notes: bool,
    num_multiple_choice: int,
    num_multiple_select: int,
    num_fill_blank: int,
    num_open: int,
    difficulty: str,
    language: Optional[str],
    instructions: Optional[str],
    model_id: Optional[str],
) -> Exam:
    total = num_multiple_choice + num_multiple_select + num_fill_blank + num_open
    if total == 0:
        raise InvalidInputError("The exam needs at least one question.")
    if total > MAX_QUESTIONS:
        raise InvalidInputError(f"An exam can have at most {MAX_QUESTIONS} questions.")

    notebook = await Notebook.get(notebook_id)
    material, used_ids = await build_study_material(notebook, source_ids, include_notes)

    generated_title, questions = await generate_exam_questions(
        material,
        num_multiple_choice=num_multiple_choice,
        num_multiple_select=num_multiple_select,
        num_fill_blank=num_fill_blank,
        num_open=num_open,
        difficulty=difficulty,
        language=language,
        instructions=instructions,
        model_id=model_id,
    )

    exam = Exam(
        notebook_id=notebook_id,
        title=(title or "").strip() or generated_title or notebook.name,
        difficulty=difficulty,
        language=language,
        instructions=instructions,
        source_ids=used_ids,
        questions=[q.model_dump() for q in questions],
        model_id=model_id,
    )
    await exam.save()
    return exam


def _as_blank_answers(answer: Any, count: int) -> List[str]:
    values = answer if isinstance(answer, list) else [answer] if answer else []
    values = [str(v) if v is not None else "" for v in values][:count]
    return values + [""] * (count - len(values))


def _as_option_set(answer: Any, option_count: int) -> set[int]:
    values = answer if isinstance(answer, list) else [answer]
    chosen: set[int] = set()
    for value in values:
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= index < option_count:
            chosen.add(index)
    return chosen


def grade_deterministic(
    question: ExamQuestion, answer: Any
) -> Optional[QuestionResult]:
    """Grade without the model when possible; None means AI grading is needed."""

    def result(score: float, feedback: Optional[str] = None) -> QuestionResult:
        return QuestionResult(
            question_id=question.id,
            score=score,
            max_score=question.points,
            is_correct=score >= question.points,
            graded_by="auto",
            feedback=feedback,
        )

    if question.type == "multiple_choice":
        try:
            chosen = int(answer) if answer is not None and answer != "" else None
        except (TypeError, ValueError):
            chosen = None
        return result(question.points if chosen == question.correct_option else 0.0)

    if question.type == "multiple_select":
        # Partial credit: each correct pick earns a share of the points and each
        # wrong pick cancels one correct pick, so "select everything" scores 0.
        picked = _as_option_set(answer, len(question.options))
        correct = set(question.correct_options)
        hits = len(picked & correct)
        wrong = len(picked - correct)
        fraction = max(0, hits - wrong) / len(correct) if correct else 0.0
        return result(round(question.points * fraction, 2))

    if question.type == "fill_blank":
        answers = _as_blank_answers(answer, len(question.blanks))
        if not any(a.strip() for a in answers):
            return result(0.0)
        matches = [
            normalize_answer(given) in {normalize_answer(a) for a in accepted}
            for given, accepted in zip(answers, question.blanks)
        ]
        if all(matches):
            return result(question.points)
        return None

    if not str(answer or "").strip():
        return result(0.0)
    return None


async def grade_attempt(exam: Exam, answers: Dict[str, Any]) -> ExamAttempt:
    questions = exam.get_questions()
    semaphore = asyncio.Semaphore(GRADING_CONCURRENCY)

    async def grade(question: ExamQuestion) -> QuestionResult:
        answer = answers.get(question.id)
        auto = grade_deterministic(question, answer)
        if auto is not None:
            return auto
        student_answer: Any = (
            _as_blank_answers(answer, len(question.blanks))
            if question.type == "fill_blank"
            else str(answer)
        )
        async with semaphore:
            score, feedback = await grade_with_ai(
                question,
                student_answer,
                language=exam.language,
                model_id=exam.model_id,
            )
        return QuestionResult(
            question_id=question.id,
            score=score,
            max_score=question.points,
            is_correct=score >= question.points,
            graded_by="ai",
            feedback=feedback,
        )

    results = await asyncio.gather(*(grade(q) for q in questions))

    attempt = ExamAttempt(
        exam_id=exam.id or "",
        answers={q.id: answers.get(q.id) for q in questions},
        results=[r.model_dump() for r in results],
        score=float(sum(r.score for r in results)),
        max_score=float(sum(r.max_score for r in results)),
    )
    await attempt.save()
    return attempt
