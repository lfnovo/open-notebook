"""Interact with a test at its original position in a chat response."""

from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api import exam_service
from api.models import ExamAttemptRequest, ExamAttemptResponse, ExamQuestionResponse
from api.routers.exams import _attempt_response, _question_response
from open_notebook.domain.chat_quiz import ChatQuiz
from open_notebook.domain.notebook import ChatSession
from open_notebook.utils.chat_images import ChatImage

router = APIRouter()


class ChatQuizResponse(BaseModel):
    id: str
    title: str
    questions: List[ExamQuestionResponse]
    images: Dict[str, ChatImage] = Field(default_factory=dict)
    latest_attempt: Optional[ExamAttemptResponse] = None
    review_questions: Optional[List[ExamQuestionResponse]] = None


async def _response(quiz: ChatQuiz) -> ChatQuizResponse:
    await ChatSession.get(quiz.session_id)
    attempts = await quiz.get_attempts()
    latest = attempts[0] if attempts else None
    questions = quiz.get_questions()
    return ChatQuizResponse(
        id=quiz.id or "",
        title=quiz.title,
        questions=[_question_response(question, False) for question in questions],
        images={
            key: image
            if latest
            else image.model_copy(
                update={
                    "name": key,
                    "source_id": None,
                    "source_title": None,
                    "page": None,
                }
            )
            for key, image in quiz.images.items()
        },
        latest_attempt=_attempt_response(latest) if latest else None,
        review_questions=[_question_response(question, True) for question in questions]
        if latest
        else None,
    )


@router.get("/chat-quizzes/{quiz_id}", response_model=ChatQuizResponse)
async def get_chat_quiz(quiz_id: str):
    return await _response(await ChatQuiz.get(quiz_id))


@router.post("/chat-quizzes/{quiz_id}/attempts", response_model=ChatQuizResponse)
async def submit_chat_quiz(quiz_id: str, request: ExamAttemptRequest):
    quiz = await ChatQuiz.get(quiz_id)
    await ChatSession.get(quiz.session_id)
    await exam_service.grade_attempt(quiz, request.answers)
    return await _response(quiz)
