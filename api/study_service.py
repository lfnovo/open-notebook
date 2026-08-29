from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger
from surreal_commands import get_command_status, submit_command

from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import InvalidInputError
from open_notebook.study.models import StudySet


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

    @staticmethod
    async def delete_study_set(study_set_id: str) -> None:
        """Delete a study set."""
        study_set = await StudyService.get_study_set(study_set_id)
        try:
            await study_set.delete()
        except Exception as e:
            logger.error(f"Failed to delete study set {study_set_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete study set")
