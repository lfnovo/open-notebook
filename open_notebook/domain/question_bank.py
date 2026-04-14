from typing import ClassVar, List, Optional

from loguru import logger

from open_notebook.database.repository import repo_create, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError


class QuestionRecord(ObjectModel):
    """A single question stored in the persistent question bank."""

    table_name: ClassVar[str] = "question_bank"
    nullable_fields: ClassVar[set] = {"options", "embedding"}

    topic: str
    question: str
    type: str  # mcq | short | scenario | calculation | definition
    difficulty: str  # easy | medium | hard
    answer: str
    explanation: str
    options: Optional[List[str]] = None
    embedding: Optional[List[float]] = None

    @classmethod
    async def save_batch(cls, questions: List[dict]) -> List["QuestionRecord"]:
        """Save a batch of question dicts to the bank and return saved records."""
        saved = []
        for q in questions:
            try:
                data = {k: v for k, v in q.items() if k != "id"}
                raw = await repo_create("question_bank", data)
                record = raw[0] if isinstance(raw, list) else raw
                if record:
                    saved.append(cls(**record))
            except Exception as e:
                logger.error(f"Failed to save question to bank: {e}")
        return saved

    @classmethod
    async def search_similar(cls, question_text: str, limit: int = 5) -> List[dict]:
        """
        Text-based search for similar questions in the bank.
        Returns raw dicts for deduplication comparison.
        """
        try:
            words = [w.strip() for w in question_text.split() if len(w.strip()) > 4][:5]
            if not words:
                return []
            search_term = " ".join(words)
            results = await repo_query(
                "SELECT id, question, topic, type, difficulty FROM question_bank "
                "WHERE string::contains(string::lowercase(question), string::lowercase($term)) "
                "LIMIT $limit",
                {"term": search_term, "limit": limit},
            )
            return results or []
        except Exception as e:
            logger.error(f"Error searching question bank: {e}")
            return []


class QuestionPaper(ObjectModel):
    """A generated question paper record with job tracking."""

    table_name: ClassVar[str] = "question_paper"
    nullable_fields: ClassVar[set] = {
        "final_paper",
        "answer_key",
        "coverage_gaps",
        "error_message",
        "command",
    }

    topic: str
    difficulty: str
    target_marks: int
    section_config: dict
    final_paper: Optional[dict] = None
    answer_key: Optional[List[dict]] = None
    coverage_gaps: Optional[List[str]] = None
    status: str = "pending"
    error_message: Optional[str] = None
    command: Optional[str] = None

    async def update_status(self, status: str, error_message: Optional[str] = None) -> None:
        """Update paper status and optional error message."""
        from open_notebook.database.repository import repo_update
        update_data: dict = {"status": status}
        if error_message is not None:
            update_data["error_message"] = error_message
        try:
            await repo_update("question_paper", self.id, update_data)
            self.status = status
            if error_message is not None:
                self.error_message = error_message
        except Exception as e:
            logger.error(f"Failed to update paper status: {e}")
            raise DatabaseOperationError(e)

    async def save_result(self, final_paper: dict, answer_key: List[dict], coverage_gaps: List[str]) -> None:
        """Persist the completed paper result."""
        from open_notebook.database.repository import repo_update
        try:
            await repo_update(
                "question_paper",
                self.id,
                {
                    "final_paper": final_paper,
                    "answer_key": answer_key,
                    "coverage_gaps": coverage_gaps,
                    "status": "completed",
                },
            )
            self.final_paper = final_paper
            self.answer_key = answer_key
            self.coverage_gaps = coverage_gaps
            self.status = "completed"
        except Exception as e:
            logger.error(f"Failed to save paper result: {e}")
            raise DatabaseOperationError(e)
