"""Practice tests embedded in chat messages, with private answer keys."""

from typing import Any, ClassVar

from pydantic import Field

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.domain.exam import ExamAttempt, ExamQuestion
from open_notebook.utils.chat_images import ChatImage


class ChatQuiz(ObjectModel):
    table_name: ClassVar[str] = "chat_quiz"
    nullable_fields: ClassVar[set[str]] = {"model_id", "language"}
    session_id: str
    title: str
    questions: list[dict[str, Any]] = Field(default_factory=list)
    images: dict[str, ChatImage] = Field(default_factory=dict)
    model_id: str | None = None
    language: str | None = None

    def _prepare_save_data(self) -> dict[str, Any]:
        data = super()._prepare_save_data()
        data["session_id"] = ensure_record_id(self.session_id)
        if self.model_id:
            data["model_id"] = ensure_record_id(self.model_id)
        return data

    async def save(self) -> None:
        await super().save()
        self.images = {
            key: ChatImage.model_validate(value) for key, value in self.images.items()
        }

    def get_questions(self) -> list[ExamQuestion]:
        return [ExamQuestion(**question) for question in self.questions]

    async def get_attempts(self) -> list["ChatQuizAttempt"]:
        rows = await repo_query(
            "SELECT * FROM chat_quiz_attempt WHERE exam_id = $quiz ORDER BY created DESC",
            {"quiz": ensure_record_id(self.id or "")},
        )
        return [ChatQuizAttempt(**row) for row in rows]


class ChatQuizAttempt(ExamAttempt):
    table_name: ClassVar[str] = "chat_quiz_attempt"
