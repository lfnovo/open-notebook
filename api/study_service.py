from typing import Any, Dict, List, Optional

from ai_prompter import Prompter
from fastapi import HTTPException
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from loguru import logger
from surreal_commands import get_command_status, submit_command

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import InvalidInputError
from open_notebook.study.models import FlashcardGradeResult, StudySet
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.text_utils import extract_text_content


class StudyService:
    """Service layer for study tools (flashcards + quiz) operations.

    Mirrors api/podcast_service.py::PodcastService: submission is
    fire-and-forget via submit_command(), status is polled via
    surreal-commands, and study sets are plain CRUD on top of StudySet.
    """

    @staticmethod
    async def _submit_generation_job(
        command_name: str,
        notebook_id: str,
        name: str,
        item_count: int,
        model_id: Optional[str],
    ) -> str:
        try:
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise ValueError(f"Notebook '{notebook_id}' not found")

            command_args = {
                "notebook_id": notebook_id,
                "name": name,
                "item_count": item_count,
                "model_id": model_id,
            }

            # Ensure command modules are imported before submitting - needed
            # because submit_command validates against local registry (same
            # reasoning as PodcastService.submit_generation_job).
            try:
                import commands.study_commands  # noqa: F401
            except ImportError as import_err:
                logger.error(f"Failed to import study commands: {import_err}")
                raise ValueError("Study commands not available")

            job_id = submit_command("open_notebook", command_name, command_args)
            if not job_id:
                raise ValueError("Failed to get job_id from submit_command")
            job_id_str = str(job_id)
            logger.info(
                f"Submitted {command_name} job: {job_id_str} for notebook '{notebook_id}'"
            )
            return job_id_str

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to submit {command_name} job: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to submit {command_name} job"
            )

    @staticmethod
    async def submit_flashcards_job(
        notebook_id: str,
        name: str,
        item_count: int = 10,
        model_id: Optional[str] = None,
    ) -> str:
        """Submit a flashcards generation job for background processing."""
        return await StudyService._submit_generation_job(
            "generate_flashcards", notebook_id, name, item_count, model_id
        )

    @staticmethod
    async def submit_quiz_job(
        notebook_id: str,
        name: str,
        item_count: int = 10,
        model_id: Optional[str] = None,
    ) -> str:
        """Submit a quiz generation job for background processing."""
        return await StudyService._submit_generation_job(
            "generate_quiz", notebook_id, name, item_count, model_id
        )

    @staticmethod
    async def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get status of a study set generation job.

        Mirrors PodcastService.get_job_status's response shape exactly - the
        StudySet row (like PodcastEpisode) is only created partway through
        the command, so the frontend needs this to poll an in-flight
        generation before that row exists.
        """
        try:
            status = await get_command_status(job_id)
            return {
                "job_id": job_id,
                "status": status.status if status else "unknown",
                "result": status.result if status else None,
                "error_message": getattr(status, "error_message", None)
                if status
                else None,
                "created": str(status.created)
                if status and hasattr(status, "created") and status.created
                else None,
                "updated": str(status.updated)
                if status and hasattr(status, "updated") and status.updated
                else None,
                "progress": getattr(status, "progress", None) if status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get study job status: {e}")
            raise HTTPException(status_code=500, detail="Failed to get job status")

    @staticmethod
    async def list_study_sets(notebook_id: str) -> List[StudySet]:
        """List all study sets for a notebook."""
        try:
            return await StudySet.get_for_notebook(notebook_id)
        except Exception as e:
            logger.error(f"Failed to list study sets for notebook {notebook_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to list study sets")

    @staticmethod
    async def get_study_set(study_set_id: str) -> StudySet:
        """Get a specific study set."""
        try:
            return await StudySet.get(study_set_id)
        except Exception as e:
            logger.error(f"Failed to get study set {study_set_id}: {e}")
            raise HTTPException(status_code=404, detail="Study set not found")

    @staticmethod
    async def review_flashcard(
        study_set_id: str, item_index: int, rating: str
    ) -> Dict[str, Any]:
        """Record a self-graded recall outcome for one flashcard (retrieval
        practice) and persist its next spaced-repetition due date."""
        study_set = await StudyService.get_study_set(study_set_id)
        try:
            updated_item = await study_set.review_flashcard(item_index, rating)
        except InvalidInputError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(
                f"Failed to review flashcard {study_set_id}[{item_index}]: {e}"
            )
            raise HTTPException(status_code=500, detail="Failed to record review")
        return {
            "item": updated_item,
            "due_count": study_set.review_stats()["due_count"],
        }

    # After this many unsuccessful attempts on the same card in one guided
    # session, force-reveal the answer instead of looping forever.
    MAX_GRADING_ATTEMPTS = 3

    @staticmethod
    async def _grade_answer(
        front: str, back: str, answer: str, attempt: int
    ) -> FlashcardGradeResult:
        """Run the grade_flashcard LLM call and parse its structured output.

        Follows the exact Prompter + PydanticOutputParser pattern used by
        commands/study_commands.py::_generate_study_set(). This call is
        synchronous (the student is waiting live in the UI for one short
        flashcard grading), unlike the flashcards/quiz generation commands
        which run as background surreal-commands jobs.
        """
        try:
            parser: PydanticOutputParser = PydanticOutputParser(
                pydantic_object=FlashcardGradeResult
            )
            prompt = Prompter(prompt_template="study/grade_flashcard", parser=parser).render(  # type: ignore[arg-type]
                data={"front": front, "back": back, "answer": answer, "attempt": attempt}
            )
            chain = await provision_langchain_model(prompt, None, "transformation")
            response = await chain.ainvoke(prompt)
            response_content = extract_text_content(response.content)
            cleaned_content = clean_thinking_content(response_content)
            return parser.parse(cleaned_content)
        except Exception as e:
            # A malformed/failed grading call shouldn't crash the student's
            # study session - fall back to a neutral, non-punishing rating
            # with generic feedback instead of raising 500 into their face.
            logger.warning(
                f"Flashcard grading failed, falling back to neutral rating: {e}"
            )
            return FlashcardGradeResult(
                correct=False,
                feedback=(
                    "No pude evaluar tu respuesta automáticamente esta vez, "
                    "intenta de nuevo."
                ),
                rating="hard",
            )

    @staticmethod
    async def grade_flashcard_answer(
        study_set_id: str, item_index: int, answer: str, attempt: int
    ) -> Dict[str, Any]:
        """AI-grade a student's free-text answer to one flashcard, then
        persist the resulting spaced-repetition rating via the existing
        review flow (guided study mode - "Modo guiado con IA").

        After MAX_GRADING_ATTEMPTS unsuccessful attempts on the same card in
        one sitting, force-reveal the reference answer rather than looping
        forever: rating is forced to "again" (they didn't learn it this
        pass) and the response includes `revealed_answer` so the frontend
        can show it plainly instead of asking for another attempt.
        """
        study_set = await StudyService.get_study_set(study_set_id)

        if study_set.kind != "flashcards":
            raise HTTPException(
                status_code=400,
                detail="Only flashcard study sets support AI-graded review",
            )
        if item_index < 0 or item_index >= len(study_set.items):
            raise HTTPException(
                status_code=400, detail=f"Invalid item index: {item_index}"
            )

        item = study_set.items[item_index]
        front = item.get("front", "")
        back = item.get("back", "")

        parsed = await StudyService._grade_answer(front, back, answer, attempt)

        revealed_answer: Optional[str] = None
        rating: str = parsed.rating
        if attempt >= StudyService.MAX_GRADING_ATTEMPTS and not parsed.correct:
            rating = "again"
            revealed_answer = back

        try:
            updated_item = await study_set.review_flashcard(item_index, rating)
        except InvalidInputError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(
                f"Failed to record guided review {study_set_id}[{item_index}]: {e}"
            )
            raise HTTPException(status_code=500, detail="Failed to record review")

        return {
            "correct": parsed.correct,
            "feedback": parsed.feedback,
            "rating": rating,
            "attempt": attempt,
            "revealed_answer": revealed_answer,
            "item": updated_item,
            "due_count": study_set.review_stats()["due_count"],
        }

    @staticmethod
    async def delete_study_set(study_set_id: str) -> None:
        """Delete a study set."""
        study_set = await StudyService.get_study_set(study_set_id)
        try:
            await study_set.delete()
        except Exception as e:
            logger.error(f"Failed to delete study set {study_set_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete study set")
