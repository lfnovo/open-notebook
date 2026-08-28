from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel

# --- Structured-output schemas for the flashcards/quiz LLM calls -----------
# Used with PydanticOutputParser in commands/study_commands.py, following the
# same Prompter + PydanticOutputParser pattern as open_notebook/graphs/ask.py
# (see docs/7-DEVELOPMENT/prompts.md "format-instructions delegation").


class Flashcard(BaseModel):
    front: str = Field(..., description="The question, prompt, or term side")
    back: str = Field(..., description="The concise answer or explanation side")


class FlashcardList(BaseModel):
    items: List[Flashcard] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    question: str
    options: List[str] = Field(..., description="Candidate answers, one of which is correct")
    correct_index: int = Field(..., description="Index into `options` of the correct answer")
    explanation: str = Field(..., description="Why the correct answer is correct")


class QuizList(BaseModel):
    items: List[QuizQuestion] = Field(default_factory=list)


# --- Domain model -----------------------------------------------------------


class StudySet(ObjectModel):
    """A generated set of flashcards or quiz questions for a notebook.

    Mirrors open_notebook/podcasts/models.py::PodcastEpisode: `command` links
    back to the async surreal-commands job that generated it, and the same
    batch job-status helpers are provided for list views.
    """

    table_name: ClassVar[str] = "study_set"

    notebook: str = Field(..., description="Notebook record ID this study set was generated from")
    kind: Literal["flashcards", "quiz"] = Field(..., description="Type of study material")
    name: str = Field(..., description="Display name for the study set")
    content: str = Field(
        ..., description="Source context used to generate this study set (audit/regen)"
    )
    items: List[Dict[str, Any]] = Field(
        default_factory=list, description="Flashcards or quiz items (flexible JSON)"
    )
    model_id: Optional[str] = Field(
        default=None, description="Model record ID used for generation"
    )
    command: Optional[Union[str, RecordID]] = Field(
        default=None, description="Link to the surreal-commands generation job"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("command", mode="before")
    @classmethod
    def parse_command(cls, value):
        if isinstance(value, str) and value:
            return ensure_record_id(value)
        return value

    def _prepare_save_data(self) -> dict:
        data = super()._prepare_save_data()
        if data.get("notebook"):
            data["notebook"] = ensure_record_id(data["notebook"])
        if data.get("model_id"):
            data["model_id"] = ensure_record_id(data["model_id"])
        if data.get("command") is not None:
            data["command"] = ensure_record_id(data["command"])
        return data

    async def get_job_status(self) -> Optional[str]:
        """Get the status of the associated command."""
        if not self.command:
            return None
        try:
            from surreal_commands import get_command_status

            status = await get_command_status(str(self.command))
            return status.status if status else "unknown"
        except Exception:
            return "unknown"

    async def get_job_detail(self) -> dict:
        """Get status and error_message of the associated command."""
        if not self.command:
            return {"status": None, "error_message": None}
        try:
            from surreal_commands import get_command_status

            status = await get_command_status(str(self.command))
            if not status:
                return {"status": "unknown", "error_message": None}
            return {
                "status": status.status,
                "error_message": getattr(status, "error_message", None),
            }
        except Exception:
            return {"status": "unknown", "error_message": None}

    @classmethod
    async def get_job_details_for_commands(
        cls, command_ids: List[Union[str, RecordID]]
    ) -> Dict[str, dict]:
        """Batch-fetch {status, error_message} for many commands in one query.

        Mirrors PodcastEpisode.get_job_details_for_commands - avoids one
        round trip per study set when listing (no connection pooling in the
        repository layer).
        """
        ids = [cid for cid in command_ids if cid]
        grouped: Dict[str, dict] = {}
        if not ids:
            return grouped
        try:
            result = await repo_query(
                "SELECT * FROM command WHERE id IN $command_ids",
                {"command_ids": [ensure_record_id(cid) for cid in ids]},
            )
        except Exception as e:
            logger.error(f"Error batch-fetching command status: {e}")
            return grouped
        for row in result:
            grouped[str(row.get("id"))] = {
                "status": row.get("status", "unknown"),
                "error_message": row.get("error_message"),
            }
        return grouped

    @classmethod
    async def get_for_notebook(cls, notebook_id: str) -> List["StudySet"]:
        """List study sets for a notebook, newest first."""
        try:
            result = await repo_query(
                "SELECT * FROM study_set WHERE notebook = $notebook_id ORDER BY created DESC",
                {"notebook_id": ensure_record_id(notebook_id)},
            )
            return [cls(**row) for row in result]
        except Exception as e:
            logger.error(f"Error fetching study sets for notebook {notebook_id}: {e}")
            raise
