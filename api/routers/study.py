from typing import List

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import (
    GenerateFlashcardsRequest,
    GenerateQuizRequest,
    ReviewFlashcardRequest,
    ReviewFlashcardResponse,
    StudySetGenerationResponse,
    StudySetListResponse,
    StudySetResponse,
)
from api.study_service import StudyService
from open_notebook.exceptions import OpenNotebookError
from open_notebook.study.models import StudySet

router = APIRouter()


@router.post("/study/flashcards", response_model=StudySetGenerationResponse)
async def generate_flashcards(request: GenerateFlashcardsRequest):
    """Generate a flashcard study set for a notebook. Returns immediately with a job ID."""
    try:
        job_id = await StudyService.submit_flashcards_job(
            notebook_id=request.notebook_id,
            name=request.name,
            item_count=request.item_count,
            model_id=request.model_id,
        )
        return StudySetGenerationResponse(
            job_id=job_id,
            status="submitted",
            message=f"Flashcard generation started for '{request.name}'",
            notebook_id=request.notebook_id,
            name=request.name,
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error generating flashcards: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate flashcards")


@router.post("/study/quiz", response_model=StudySetGenerationResponse)
async def generate_quiz(request: GenerateQuizRequest):
    """Generate a quiz study set for a notebook. Returns immediately with a job ID."""
    try:
        job_id = await StudyService.submit_quiz_job(
            notebook_id=request.notebook_id,
            name=request.name,
            item_count=request.item_count,
            model_id=request.model_id,
        )
        return StudySetGenerationResponse(
            job_id=job_id,
            status="submitted",
            message=f"Quiz generation started for '{request.name}'",
            notebook_id=request.notebook_id,
            name=request.name,
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz")


@router.get("/study/jobs/{job_id}")
async def get_study_job_status(job_id: str):
    """Get the status of a study set (flashcards/quiz) generation job"""
    try:
        status_data = await StudyService.get_job_status(job_id)
        return status_data

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching study job status: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch job status"
        )


@router.get("/notebooks/{notebook_id}/study", response_model=List[StudySetListResponse])
async def list_notebook_study_sets(notebook_id: str):
    """List all study sets (flashcards + quizzes) for a notebook."""
    try:
        study_sets = await StudyService.list_study_sets(notebook_id)

        # Batch-fetch job status for every study set with a command in one
        # query instead of one round trip per study set (see
        # StudySet.get_job_details_for_commands docstring).
        try:
            details_by_command = await StudySet.get_job_details_for_commands(
                [s.command for s in study_sets if s.command]
            )
        except Exception as e:
            logger.warning(f"Error batch-fetching study set job statuses: {str(e)}")
            details_by_command = {}

        response_sets = []
        for study_set in study_sets:
            job_status = None
            error_message = None
            if study_set.command:
                detail = details_by_command.get(str(study_set.command))
                if detail is not None:
                    job_status = detail["status"]
                    error_message = detail["error_message"]
                else:
                    job_status = "unknown"
            else:
                job_status = "completed" if study_set.items else "unknown"

            response_sets.append(
                StudySetListResponse(
                    id=str(study_set.id),
                    notebook=str(study_set.notebook),
                    kind=study_set.kind,
                    name=study_set.name,
                    item_count=len(study_set.items or []),
                    model_id=str(study_set.model_id) if study_set.model_id else None,
                    created=str(study_set.created) if study_set.created else None,
                    updated=str(study_set.updated) if study_set.updated else None,
                    job_status=job_status,
                    error_message=error_message,
                    due_count=study_set.review_stats()["due_count"],
                )
            )

        return response_sets

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error listing study sets: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list study sets")


@router.get("/study/{study_set_id}", response_model=StudySetResponse)
async def get_study_set(study_set_id: str):
    """Get a specific study set."""
    try:
        study_set = await StudyService.get_study_set(study_set_id)

        job_status = None
        error_message = None
        if study_set.command:
            try:
                detail = await study_set.get_job_detail()
                job_status = detail["status"]
                error_message = detail["error_message"]
            except Exception:
                job_status = "unknown"
        else:
            job_status = "completed" if study_set.items else "unknown"

        return StudySetResponse(
            id=str(study_set.id),
            notebook=str(study_set.notebook),
            kind=study_set.kind,
            name=study_set.name,
            items=study_set.items,
            model_id=str(study_set.model_id) if study_set.model_id else None,
            created=str(study_set.created) if study_set.created else None,
            updated=str(study_set.updated) if study_set.updated else None,
            job_status=job_status,
            error_message=error_message,
            due_count=study_set.review_stats()["due_count"],
        )

    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching study set: {str(e)}")
        raise HTTPException(status_code=404, detail="Study set not found")


@router.post(
    "/study/{study_set_id}/items/{item_index}/review",
    response_model=ReviewFlashcardResponse,
)
async def review_flashcard_item(
    study_set_id: str, item_index: int, request: ReviewFlashcardRequest
):
    """Record a self-graded recall outcome for one flashcard.

    Drives the spaced-repetition schedule (distributed practice testing) -
    see open_notebook/study/models.py::score_flashcard_review. Only valid
    for flashcard study sets; quiz sets return 400.
    """
    try:
        result = await StudyService.review_flashcard(
            study_set_id, item_index, request.rating
        )
        return ReviewFlashcardResponse(
            study_set_id=study_set_id,
            item_index=item_index,
            item=result["item"],
            due_count=result["due_count"],
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error reviewing flashcard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record review")


@router.delete("/study/{study_set_id}")
async def delete_study_set(study_set_id: str):
    """Delete a study set."""
    try:
        await StudyService.delete_study_set(study_set_id)
        logger.info(f"Deleted study set: {study_set_id}")
        return {
            "message": "Study set deleted successfully",
            "study_set_id": study_set_id,
        }
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting study set: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete study set")
