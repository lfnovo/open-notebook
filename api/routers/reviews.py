"""Repo-review endpoints.

POST   /reviews        — start a review (validates path, creates record, submits job)
GET    /reviews        — list reviews (optionally by notebook)
GET    /reviews/{id}   — review status + result
DELETE /reviews/{id}   — delete a review record
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.command_service import CommandService
from api.models import ReviewCreate, ReviewResponse
from open_notebook.domain.review import Review
from open_notebook.exceptions import (
    ConfigurationError,
    InvalidInputError,
    NotFoundError,
)
from open_notebook.utils.repo_scan import validate_repo_path

router = APIRouter()


def _to_response(review: Review) -> ReviewResponse:
    return ReviewResponse(
        id=review.id or "",
        theme=review.theme,
        repo_path=review.repo_path,
        notebook_id=review.notebook_id,
        status=review.status,
        command_id=review.command_id,
        report_note_id=review.report_note_id,
        summary=review.summary,
        error_message=review.error_message,
        created=str(review.created) if review.created else None,
        updated=str(review.updated) if review.updated else None,
    )


@router.post("/reviews", response_model=ReviewResponse)
async def create_review(review_data: ReviewCreate):
    """Validate the path, create a queued Review, and submit the async job."""
    try:
        # Validate the repo path up-front so the user gets an immediate, clear error
        # (rather than a job that fails in the background).
        resolved = validate_repo_path(review_data.repo_path)

        # Verify the notebook exists if provided.
        if review_data.notebook_id:
            from open_notebook.domain.notebook import Notebook

            await Notebook.get(review_data.notebook_id)

        review = Review(
            theme=review_data.theme,
            repo_path=str(resolved),
            notebook_id=review_data.notebook_id,
            status="queued",
        )
        await review.save()

        # Ensure the command is registered in this process before submitting.
        try:
            import commands.review_commands  # noqa: F401
        except ImportError as import_err:
            logger.error(f"Failed to import review command: {import_err}")
            raise HTTPException(status_code=500, detail="Review command not available")

        command_id = await CommandService.submit_command_job(
            "open_notebook",
            "repo_review",
            {
                "review_id": str(review.id),
                "theme": review_data.theme,
                "repo_path": str(resolved),
                "notebook_id": review_data.notebook_id,
                "strategy_model": review_data.strategy_model,
                "answer_model": review_data.answer_model,
                "final_answer_model": review_data.final_answer_model,
            },
        )
        review.command_id = command_id
        await review.save()

        return _to_response(review)
    except HTTPException:
        raise
    except ConfigurationError as e:
        # Feature not configured (no allowed roots) -> 422 to match the global handler.
        raise HTTPException(status_code=422, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating review: {e}")


@router.get("/reviews", response_model=List[ReviewResponse])
async def list_reviews(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
):
    try:
        reviews = await Review.get_recent(notebook_id=notebook_id)
        return [_to_response(r) for r in reviews]
    except Exception as e:
        logger.error(f"Error listing reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing reviews: {e}")


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str):
    try:
        review = await Review.get(review_id)
        return _to_response(review)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Review not found")
    except Exception as e:
        logger.error(f"Error fetching review {review_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching review: {e}")


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    try:
        review = await Review.get(review_id)
        await review.delete()
        return {"message": "Review deleted successfully"}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Review not found")
    except Exception as e:
        logger.error(f"Error deleting review {review_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting review: {e}")
