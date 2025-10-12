
from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import NoteResponse, SaveAsNoteRequest, SourceInsightResponse
from open_notebook.domain.notebook import SourceInsight
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


@router.get("/insights/{insight_id}", response_model=SourceInsightResponse)
async def get_insight(insight_id: str):
    """Get a specific insight by ID."""
    try:
        insight = await SourceInsight.get(insight_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Get source ID from the insight relationship
        source = await insight.get_source()
        
        return SourceInsightResponse(
            id=insight.id or "",
            source_id=source.id or "",
            insight_type=insight.insight_type,
            content=insight.content,
            created=str(insight.created),
            updated=str(insight.updated),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insight {insight_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching insight: {str(e)}")


@router.delete("/insights/{insight_id}")
async def delete_insight(insight_id: str):
    """Delete a specific insight."""
    try:
        insight = await SourceInsight.get(insight_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        await insight.delete()
        
        return {"message": "Insight deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting insight {insight_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting insight: {str(e)}")


@router.post("/insights/{insight_id}/save-as-note", response_model=NoteResponse)
async def save_insight_as_note(insight_id: str, request: SaveAsNoteRequest):
    """Convert an insight to a note."""
    try:
        insight = await SourceInsight.get(insight_id)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Use the existing save_as_note method from the domain model
        note = await insight.save_as_note(request.notebook_id)
        
        return NoteResponse(
            id=note.id or "",
            title=note.title,
            content=note.content,
            note_type=note.note_type,
            created=str(note.created),
            updated=str(note.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving insight {insight_id} as note: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving insight as note: {str(e)}")