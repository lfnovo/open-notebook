from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models import UsageSummaryResponse
from api.usage_service import get_usage_summary
from open_notebook.exceptions import OpenNotebookError

router = APIRouter()


@router.get("/usage/summary", response_model=UsageSummaryResponse)
async def usage_summary(
    period: Literal["month", "year"] = Query(
        "month", description="Aggregation period (rolling 30 or 365 days)"
    ),
):
    """Get aggregated LLM usage/cost for the given period."""
    try:
        summary = await get_usage_summary(period)
        return UsageSummaryResponse(**summary)
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching usage summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch usage summary")
