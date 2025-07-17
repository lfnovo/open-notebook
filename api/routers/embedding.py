from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import EmbedRequest, EmbedResponse
from open_notebook.domain.models import model_manager
from open_notebook.domain.notebook import Note, Source

router = APIRouter()


@router.post("/embed", response_model=EmbedResponse)
async def embed_content(embed_request: EmbedRequest):
    """Embed content for vector search."""
    try:
        # Check if embedding model is available
        if not await model_manager.get_embedding_model():
            raise HTTPException(
                status_code=400,
                detail="No embedding model configured. Please configure one in the Models section.",
            )

        item_id = embed_request.item_id
        item_type = embed_request.item_type.lower()

        # Validate item type
        if item_type not in ["source", "note"]:
            raise HTTPException(
                status_code=400, detail="Item type must be either 'source' or 'note'"
            )

        # Get the item and embed it
        if item_type == "source":
            source_item = await Source.get(item_id)
            if not source_item:
                raise HTTPException(status_code=404, detail="Source not found")

            # Check if already embedded
            if await source_item.get_embedded_chunks() > 0:
                return EmbedResponse(
                    success=True,
                    message="Source is already embedded",
                    item_id=item_id,
                    item_type=item_type,
                )

            # Perform embedding
            await source_item.vectorize()
            message = "Source embedded successfully"

        elif item_type == "note":
            note_item = await Note.get(item_id)
            if not note_item:
                raise HTTPException(status_code=404, detail="Note not found")

            await note_item.vectorize()

        return EmbedResponse(
            success=True, message=message, item_id=item_id, item_type=item_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error embedding {embed_request.item_type} {embed_request.item_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error embedding content: {str(e)}"
        )
