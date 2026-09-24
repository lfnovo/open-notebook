from typing import Dict, List, Optional

from fastapi import APIRouter, Query

from api import exam_service
from api.models import (
    ExamAttemptRequest,
    ExamAttemptResponse,
    ExamCreateRequest,
    ExamQuestionResponse,
    ExamQuestionResultResponse,
    ExamResponse,
)
from open_notebook.ai.models import Model
from open_notebook.database.repository import repo_query
from open_notebook.domain.exam import Exam, ExamAttempt

router = APIRouter()


def _question_response(question, include_answers: bool) -> ExamQuestionResponse:
    response = ExamQuestionResponse(
        id=question.id,
        type=question.type,
        prompt=question.prompt,
        points=question.points,
        options=question.options,
        blank_count=len(question.blanks),
    )
    if include_answers:
        response.correct_option = question.correct_option
        response.correct_options = question.correct_options
        response.blanks = question.blanks
        response.reference_answer = question.reference_answer
        response.rubric = question.rubric
        response.explanation = question.explanation
    return response


def _exam_response(
    exam: Exam,
    stats: Optional[Dict] = None,
    include_questions: bool = False,
    include_answers: bool = False,
) -> ExamResponse:
    questions = exam.get_questions()
    return ExamResponse(
        id=exam.id or "",
        notebook_id=exam.notebook_id,
        title=exam.title,
        difficulty=exam.difficulty,
        language=exam.language,
        instructions=exam.instructions,
        source_ids=exam.source_ids,
        question_count=len(questions),
        max_score=sum(q.points for q in questions),
        attempt_count=(stats or {}).get("attempts", 0),
        best_score=(stats or {}).get("best"),
        questions=(
            [_question_response(q, include_answers) for q in questions]
            if include_questions
            else None
        ),
        created=str(exam.created),
        updated=str(exam.updated),
    )


def _attempt_response(attempt: ExamAttempt) -> ExamAttemptResponse:
    return ExamAttemptResponse(
        id=attempt.id or "",
        exam_id=attempt.exam_id,
        answers=attempt.answers,
        results=[ExamQuestionResultResponse(**r) for r in attempt.results],
        score=attempt.score,
        max_score=attempt.max_score,
        created=str(attempt.created),
    )


async def _attempt_stats() -> Dict[str, Dict]:
    rows = await repo_query(
        "SELECT exam_id, count() AS attempts, math::max(score) AS best "
        "FROM exam_attempt GROUP BY exam_id"
    )
    return {str(row["exam_id"]): row for row in rows}


@router.get("/exams", response_model=List[ExamResponse])
async def list_exams(notebook_id: Optional[str] = Query(None)):
    """List practice exams, optionally only those of one notebook."""
    exams = await Exam.get_by_notebook(notebook_id)
    stats = await _attempt_stats()
    return [_exam_response(exam, stats.get(exam.id or "")) for exam in exams]


@router.post("/exams", response_model=ExamResponse)
async def create_exam(request: ExamCreateRequest):
    """Generate a practice exam from a notebook's sources with the LLM."""
    if request.model_id:
        await Model.get(request.model_id)  # raises NotFoundError
    exam = await exam_service.create_exam(**request.model_dump())
    return _exam_response(exam, include_questions=True)


@router.get("/exams/{exam_id}", response_model=ExamResponse)
async def get_exam(exam_id: str, include_answers: bool = Query(False)):
    """Get an exam with its questions; the answer key only on request."""
    exam = await Exam.get(exam_id)
    stats = await _attempt_stats()
    return _exam_response(
        exam,
        stats.get(exam.id or ""),
        include_questions=True,
        include_answers=include_answers,
    )


@router.delete("/exams/{exam_id}")
async def delete_exam(exam_id: str):
    """Delete an exam and all its attempts."""
    exam = await Exam.get(exam_id)
    await exam.delete()
    return {"message": "Exam deleted successfully"}


@router.post("/exams/{exam_id}/attempts", response_model=ExamAttemptResponse)
async def submit_attempt(exam_id: str, request: ExamAttemptRequest):
    """Submit answers; multiple choice and exact blanks are graded directly,
    free answers by the LLM."""
    exam = await Exam.get(exam_id)
    attempt = await exam_service.grade_attempt(exam, request.answers)
    return _attempt_response(attempt)


@router.get("/exams/{exam_id}/attempts", response_model=List[ExamAttemptResponse])
async def list_attempts(exam_id: str):
    exam = await Exam.get(exam_id)
    return [_attempt_response(a) for a in await exam.get_attempts()]


@router.get("/exam-attempts/{attempt_id}", response_model=ExamAttemptResponse)
async def get_attempt(attempt_id: str):
    return _attempt_response(await ExamAttempt.get(attempt_id))


@router.delete("/exam-attempts/{attempt_id}")
async def delete_attempt(attempt_id: str):
    attempt = await ExamAttempt.get(attempt_id)
    await attempt.delete()
    return {"message": "Attempt deleted successfully"}
