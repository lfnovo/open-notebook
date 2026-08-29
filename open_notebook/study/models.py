from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import InvalidInputError

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


# --- Spaced repetition (retrieval practice + distributed practice) ---------
# Dunlosky et al. (2013) rank practice testing as high-utility on its own,
# but the bigger win is *distributed* practice testing - repeating the same
# retrieval over spaced-out sessions beats massing it in one sitting. This is
# a deliberately lightweight SM-2-style scheme (day-granularity, no fuzz, no
# per-deck tuning) - two people studying together, not a general SRS engine.
# State lives inside each flashcard item dict (`items` is a FLEXIBLE
# array<object> - see migration 25), so no schema/migration change is
# needed: `ease`, `interval`, `reps`, `due`, `last_reviewed` are simply
# absent on a freshly generated card, which naturally makes it "due" (new
# cards are immediately eligible for their first review, same as Anki).

SrsRating = Literal["again", "hard", "good", "easy"]

_SRS_MIN_EASE = 1.3
_SRS_DEFAULT_EASE = 2.5


def score_flashcard_review(
    item: Dict[str, Any], rating: str, now: Optional[datetime] = None
) -> Dict[str, Any]:
    """Compute the next SM-2-style review state for one flashcard item.

    Returns a *new* dict (copy of `item`) with the review fields set/updated.
    Does not persist - callers write it back into `StudySet.items[i]` and
    save. `interval` is whole days; `due` is an ISO date (YYYY-MM-DD), so
    "due" comparisons are plain string comparisons.
    """
    if rating not in ("again", "hard", "good", "easy"):
        raise InvalidInputError(f"Unknown review rating: {rating}")

    now = now or datetime.now(timezone.utc)
    ease = float(item.get("ease") or _SRS_DEFAULT_EASE)
    interval = int(item.get("interval") or 0)
    reps = int(item.get("reps") or 0)

    if rating == "again":
        # Forgot it: restart the learning steps and resurface it today.
        reps = 0
        interval = 0
        ease = max(_SRS_MIN_EASE, ease - 0.2)
    elif rating == "hard":
        ease = max(_SRS_MIN_EASE, ease - 0.15)
        interval = max(1, round((interval or 1) * 1.2))
        reps += 1
    elif rating == "good":
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ease))
        reps += 1
    else:  # easy
        ease = ease + 0.15
        if reps == 0:
            interval = 3
        elif reps == 1:
            interval = 7
        else:
            interval = max(1, round(interval * ease * 1.3))
        reps += 1

    due_date = (now + timedelta(days=interval)).date().isoformat()
    updated = dict(item)
    updated.update(
        ease=round(ease, 2),
        interval=interval,
        reps=reps,
        due=due_date,
        last_reviewed=now.isoformat(),
    )
    return updated


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

    def review_stats(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Count items due for review now, and when the next one comes due.

        Only flashcards carry spaced-repetition state (see
        score_flashcard_review docstring) - quiz sets always report
        due_count=0 rather than showing a misleading "due" badge for a kind
        that has no review UI/endpoint.
        """
        if self.kind != "flashcards":
            return {"due_count": 0, "next_due": None}

        today = (now or datetime.now(timezone.utc)).date().isoformat()
        due_count = 0
        next_due: Optional[str] = None
        for item in self.items:
            due = item.get("due")
            if not due or due <= today:
                due_count += 1
            elif next_due is None or due < next_due:
                next_due = due
        return {"due_count": due_count, "next_due": next_due}

    async def review_flashcard(self, item_index: int, rating: str) -> Dict[str, Any]:
        """Record a self-graded recall outcome for one flashcard and persist
        its next due date (retrieval practice + spaced repetition)."""
        if self.kind != "flashcards":
            raise InvalidInputError(
                "Only flashcard study sets support spaced-repetition review"
            )
        if item_index < 0 or item_index >= len(self.items):
            raise InvalidInputError(f"Invalid item index: {item_index}")

        updated_item = score_flashcard_review(self.items[item_index], rating)
        self.items[item_index] = updated_item
        await self.save()
        return updated_item

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
