"""
Tests for AI-graded guided flashcard study mode ("Modo guiado con IA") -
api/study_service.py::StudyService.grade_flashcard_answer /
StudyService._grade_answer.

Covers: correct answer, incorrect answer with attempt < MAX (no reveal),
incorrect on the 3rd attempt (forced "again" + revealed_answer), and the
malformed-LLM-response fallback path (graceful "hard" rating instead of a
500 into the student's face).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.study_service import StudyService
from open_notebook.study.models import FlashcardGradeResult, StudySet


def _study_set(items=None) -> StudySet:
    return StudySet(
        id="study_set:1",
        notebook="notebook:1",
        kind="flashcards",
        name="Test Set",
        content="content",
        items=items if items is not None else [{"front": "Q1", "back": "A1"}],
    )


class TestGradeFlashcardAnswer:
    @pytest.mark.asyncio
    async def test_correct_answer_records_matching_rating_no_reveal(self):
        study_set = _study_set()
        graded = FlashcardGradeResult(correct=True, feedback="Great job!", rating="good")

        with (
            patch.object(
                StudyService, "get_study_set", new=AsyncMock(return_value=study_set)
            ),
            patch.object(
                StudyService, "_grade_answer", new=AsyncMock(return_value=graded)
            ),
            patch.object(
                StudySet,
                "review_flashcard",
                new=AsyncMock(return_value={"front": "Q1", "back": "A1", "reps": 1}),
            ) as mock_review,
        ):
            result = await StudyService.grade_flashcard_answer(
                "study_set:1", 0, "a correct answer", 1
            )

        assert result["correct"] is True
        assert result["feedback"] == "Great job!"
        assert result["rating"] == "good"
        assert result["attempt"] == 1
        assert result["revealed_answer"] is None
        mock_review.assert_awaited_once_with(0, "good")

    @pytest.mark.asyncio
    async def test_incorrect_answer_below_max_attempts_does_not_reveal(self):
        study_set = _study_set()
        graded = FlashcardGradeResult(correct=False, feedback="Not quite.", rating="again")

        with (
            patch.object(
                StudyService, "get_study_set", new=AsyncMock(return_value=study_set)
            ),
            patch.object(
                StudyService, "_grade_answer", new=AsyncMock(return_value=graded)
            ),
            patch.object(
                StudySet,
                "review_flashcard",
                new=AsyncMock(return_value={"front": "Q1", "back": "A1"}),
            ) as mock_review,
        ):
            result = await StudyService.grade_flashcard_answer(
                "study_set:1", 0, "a wrong answer", 2
            )

        assert result["correct"] is False
        assert result["rating"] == "again"
        assert result["attempt"] == 2
        assert result["revealed_answer"] is None
        mock_review.assert_awaited_once_with(0, "again")

    @pytest.mark.asyncio
    async def test_third_failed_attempt_forces_again_and_reveals_answer(self):
        study_set = _study_set(items=[{"front": "Q1", "back": "The reference answer"}])
        # Even if the model rated it "hard" (partial credit), a still-wrong
        # 3rd attempt must be forced to "again" and reveal the card.
        graded = FlashcardGradeResult(correct=False, feedback="Still missing it.", rating="hard")

        with (
            patch.object(
                StudyService, "get_study_set", new=AsyncMock(return_value=study_set)
            ),
            patch.object(
                StudyService, "_grade_answer", new=AsyncMock(return_value=graded)
            ),
            patch.object(
                StudySet,
                "review_flashcard",
                new=AsyncMock(return_value={"front": "Q1", "back": "The reference answer"}),
            ) as mock_review,
        ):
            result = await StudyService.grade_flashcard_answer(
                "study_set:1", 0, "still wrong", 3
            )

        assert result["rating"] == "again"
        assert result["revealed_answer"] == "The reference answer"
        mock_review.assert_awaited_once_with(0, "again")

    @pytest.mark.asyncio
    async def test_third_attempt_correct_does_not_reveal(self):
        """A correct answer on the 3rd attempt is still a win - no reveal."""
        study_set = _study_set(items=[{"front": "Q1", "back": "The reference answer"}])
        graded = FlashcardGradeResult(correct=True, feedback="Got it!", rating="hard")

        with (
            patch.object(
                StudyService, "get_study_set", new=AsyncMock(return_value=study_set)
            ),
            patch.object(
                StudyService, "_grade_answer", new=AsyncMock(return_value=graded)
            ),
            patch.object(
                StudySet,
                "review_flashcard",
                new=AsyncMock(return_value={"front": "Q1", "back": "The reference answer"}),
            ) as mock_review,
        ):
            result = await StudyService.grade_flashcard_answer(
                "study_set:1", 0, "finally right", 3
            )

        assert result["correct"] is True
        assert result["rating"] == "hard"
        assert result["revealed_answer"] is None
        mock_review.assert_awaited_once_with(0, "hard")

    @pytest.mark.asyncio
    async def test_quiz_set_rejected_with_400(self):
        from fastapi import HTTPException

        quiz_set = StudySet(
            id="study_set:2",
            notebook="notebook:1",
            kind="quiz",
            name="Quiz Set",
            content="content",
            items=[{"question": "Q1", "options": ["a", "b"], "correct_index": 0, "explanation": ""}],
        )

        with patch.object(
            StudyService, "get_study_set", new=AsyncMock(return_value=quiz_set)
        ):
            with pytest.raises(HTTPException) as exc_info:
                await StudyService.grade_flashcard_answer("study_set:2", 0, "answer", 1)

        assert exc_info.value.status_code == 400


class TestGradeAnswerLlmFallback:
    @pytest.mark.asyncio
    async def test_malformed_llm_response_falls_back_to_neutral_hard_rating(self):
        def _raise_parse_error(_content):
            raise ValueError("bad json")

        fake_parser = SimpleNamespace(parse=_raise_parse_error)

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(
            return_value=SimpleNamespace(content="not valid structured json")
        )

        with (
            patch("api.study_service.PydanticOutputParser", return_value=fake_parser),
            patch("api.study_service.Prompter") as mock_prompter_cls,
            patch(
                "api.study_service.provision_langchain_model",
                new=AsyncMock(return_value=mock_chain),
            ),
        ):
            mock_prompter_cls.return_value.render.return_value = "rendered prompt"
            result = await StudyService._grade_answer("Q1", "A1", "my answer", 1)

        assert result.correct is False
        assert result.rating == "hard"
        assert "intenta de nuevo" in result.feedback
        mock_chain.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_call_exception_falls_back_gracefully(self):
        with (
            patch("api.study_service.PydanticOutputParser"),
            patch("api.study_service.Prompter") as mock_prompter_cls,
            patch(
                "api.study_service.provision_langchain_model",
                new=AsyncMock(side_effect=RuntimeError("provider down")),
            ),
        ):
            mock_prompter_cls.return_value.render.return_value = "rendered prompt"
            result = await StudyService._grade_answer("Q1", "A1", "my answer", 1)

        assert result.correct is False
        assert result.rating == "hard"
