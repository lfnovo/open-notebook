from typing import Any, ClassVar, List, Optional

from loguru import logger

from open_notebook.database.repository import repo_create, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError


class QuestionRecord(ObjectModel):
    """A single question stored in the persistent question bank."""

    table_name: ClassVar[str] = "question_bank"
    nullable_fields: ClassVar[set] = {
        "options",
        "correct_indices",
        "section_ref",
        "embedding",
        "sub_topic",
        "grade",
        "chapter",
        "chapter_title",
        "answer_type",
        "target_difficulty",
        "validated_cognitive_difficulty",
        "difficulty_score",
        "difficulty_scores",
        "validation_status",
        "validation_reasons",
        "generation_attempts",
        "observed_facility",
        "observed_discrimination",
        "calibrated_difficulty",
        "calibration_status",
        "subject",
        "batch_id",
        "book_id",
        "source_chunk_index",
        "learning_outcome",
        "blind_solver_answer",
        "answer_agreement",
        "information_sufficient",
        "arithmetic_consistent",
        "no_unsupported_claims",
        "option_defensibility",
        "distractors_ok",
        "terminology_grounded",
    }

    topic: str
    question: str
    type: str  # mcq | multi_correct | ...
    difficulty: str  # legacy overall label; prefer target/validated fields
    answer: str
    explanation: str
    options: Optional[List[str]] = None
    correct_indices: Optional[List[int]] = None
    section_ref: Optional[str] = None
    embedding: Optional[List[float]] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[int] = None
    chapter_title: Optional[str] = None
    sub_topic: Optional[str] = None
    answer_type: Optional[str] = None  # single_correct | multiple_correct
    target_difficulty: Optional[str] = None
    validated_cognitive_difficulty: Optional[str] = None
    difficulty_score: Optional[int] = None
    difficulty_scores: Optional[dict] = None
    validation_status: Optional[str] = None
    validation_reasons: Optional[List[str]] = None
    generation_attempts: Optional[int] = None
    # Post-exam statistical fields — null until student response data exists.
    # Do not compute facility/discrimination during generation.
    observed_facility: Optional[float] = None
    observed_discrimination: Optional[float] = None
    calibrated_difficulty: Optional[str] = None
    calibration_status: Optional[str] = None
    # Bank batch metadata (optional; backward compatible with legacy records)
    batch_id: Optional[str] = None
    book_id: Optional[str] = None
    source_chunk_index: Optional[int] = None
    learning_outcome: Optional[str] = None
    blind_solver_answer: Optional[Any] = None
    answer_agreement: Optional[Any] = None
    information_sufficient: Optional[Any] = None
    arithmetic_consistent: Optional[Any] = None
    no_unsupported_claims: Optional[Any] = None
    option_defensibility: Optional[Any] = None
    distractors_ok: Optional[Any] = None
    terminology_grounded: Optional[Any] = None

    @classmethod
    async def save_one(cls, data: dict) -> Optional["QuestionRecord"]:
        """Save a single question dict to the bank."""
        try:
            payload = {k: v for k, v in data.items() if k != "id"}
            raw = await repo_create("question_bank", payload)
            record = raw[0] if isinstance(raw, list) else raw
            if record:
                return cls(**record)
        except Exception as e:
            logger.error(f"Failed to save question to bank: {e}")
        return None

    @classmethod
    async def fetch_scoped_for_duplicate_check(
        cls,
        *,
        grade: str,
        chapter: int,
        target_difficulty: str,
    ) -> List[dict]:
        """Load existing bank questions for grade/chapter/difficulty duplicate seeding."""
        from open_notebook.graphs.question_paper_blueprint import normalize_difficulty

        difficulty = normalize_difficulty(target_difficulty)
        try:
            results = await repo_query(
                "SELECT id, question, topic, sub_topic, chapter, grade, target_difficulty, "
                "source_chunk_index "
                "FROM question_bank "
                "WHERE grade = $grade "
                "AND chapter = $chapter "
                "AND target_difficulty = $difficulty",
                {"grade": str(grade), "chapter": int(chapter), "difficulty": difficulty},
            )
            return results or []
        except Exception as e:
            logger.warning(f"Scoped bank duplicate fetch failed: {e}")
            return []

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
        "grade",
        "subject",
        "language",
        "pass_percentage",
        "blueprint",
        "audit",
        "failed_slots",
        "covered_topics",
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
    grade: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    pass_percentage: Optional[int] = None
    blueprint: Optional[dict] = None
    audit: Optional[dict] = None
    failed_slots: Optional[List[dict]] = None
    covered_topics: Optional[List[str]] = None

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


class QuestionBankBatch(ObjectModel):
    """Async job record for bulk Question Bank pool generation."""

    table_name: ClassVar[str] = "question_bank_batch"
    nullable_fields: ClassVar[set] = {
        "audit",
        "error_message",
        "command",
        "failed_slots",
        "saved_question_ids",
        "failure_summary",
        "rejected_attempts",
    }

    book_id: str
    grade: str
    subject: str
    chapter: int
    difficulty: str
    total_questions: int
    single_correct: int
    multiple_correct: int
    language: str = "en"
    status: str = "pending"
    requested: Optional[int] = None
    accepted: Optional[int] = None
    failed: Optional[int] = None
    audit: Optional[dict] = None
    failed_slots: Optional[List[dict]] = None
    saved_question_ids: Optional[List[str]] = None
    failure_summary: Optional[dict] = None
    rejected_attempts: Optional[List[dict]] = None
    error_message: Optional[str] = None
    command: Optional[str] = None
    blueprint: Optional[dict] = None

    async def update_status(
        self, status: str, error_message: Optional[str] = None
    ) -> None:
        """Update bank batch status and optional error message."""
        from open_notebook.database.repository import repo_update

        update_data: dict = {"status": status}
        if error_message is not None:
            update_data["error_message"] = error_message
        try:
            await repo_update("question_bank_batch", self.id, update_data)
            self.status = status
            if error_message is not None:
                self.error_message = error_message
        except Exception as e:
            logger.error(f"Failed to update bank batch status: {e}")
            raise DatabaseOperationError(e)
