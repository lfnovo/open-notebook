from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError

QuestionType = Literal["multiple_choice", "multiple_select", "fill_blank", "open"]


class ExamQuestion(BaseModel):
    """A single exam question, including its answer key.

    - multiple_choice: `options` + `correct_option` (0-based index).
    - multiple_select: `options` + `correct_options` (two or more 0-based
      indexes; "select all that apply").
    - fill_blank: `prompt` contains one `___` marker per blank; `blanks[i]`
      lists the acceptable answers for blank i.
    - open: free-form answer graded by the LLM against `reference_answer`
      and `rubric`.
    """

    id: str
    type: QuestionType
    prompt: str
    points: float = 1.0
    options: List[str] = Field(default_factory=list)
    correct_option: Optional[int] = None
    correct_options: List[int] = Field(default_factory=list)
    blanks: List[List[str]] = Field(default_factory=list)
    reference_answer: Optional[str] = None
    rubric: Optional[str] = None
    explanation: Optional[str] = None


class QuestionResult(BaseModel):
    question_id: str
    score: float
    max_score: float
    is_correct: bool
    graded_by: Literal["auto", "ai"]
    feedback: Optional[str] = None


class Exam(ObjectModel):
    table_name: ClassVar[str] = "exam"
    nullable_fields: ClassVar[set[str]] = {"model_id", "language", "instructions"}
    notebook_id: str
    title: str
    difficulty: str = "medium"
    language: Optional[str] = None
    instructions: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    model_id: Optional[str] = None

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        data["notebook_id"] = ensure_record_id(data["notebook_id"])
        if data.get("model_id"):
            data["model_id"] = ensure_record_id(data["model_id"])
        return data

    def get_questions(self) -> List[ExamQuestion]:
        return [ExamQuestion(**q) for q in self.questions]

    @property
    def max_score(self) -> float:
        return sum(q.points for q in self.get_questions())

    @classmethod
    async def get_by_notebook(cls, notebook_id: Optional[str]) -> List["Exam"]:
        try:
            if notebook_id:
                rows = await repo_query(
                    "SELECT * FROM exam WHERE notebook_id = $nb ORDER BY created DESC",
                    {"nb": ensure_record_id(notebook_id)},
                )
            else:
                rows = await repo_query("SELECT * FROM exam ORDER BY created DESC")
            return [cls(**row) for row in rows]
        except Exception as e:
            raise DatabaseOperationError(e)

    async def get_attempts(self) -> List["ExamAttempt"]:
        try:
            rows = await repo_query(
                "SELECT * FROM exam_attempt WHERE exam_id = $exam ORDER BY created DESC",
                {"exam": ensure_record_id(self.id or "")},
            )
            return [ExamAttempt(**row) for row in rows]
        except Exception as e:
            raise DatabaseOperationError(e)

    async def delete(self) -> bool:
        await repo_query(
            "DELETE exam_attempt WHERE exam_id = $exam",
            {"exam": ensure_record_id(self.id or "")},
        )
        return await super().delete()


class ExamAttempt(ObjectModel):
    table_name: ClassVar[str] = "exam_attempt"
    exam_id: str
    answers: Dict[str, Any] = Field(default_factory=dict)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    score: float = 0.0
    max_score: float = 0.0

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        data["exam_id"] = ensure_record_id(data["exam_id"])
        return data
