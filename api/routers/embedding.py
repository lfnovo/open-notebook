from fastapi import APIRouter, HTTPException
from loguru import logger

from api.command_service import CommandService
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

        # Branch based on processing mode
        if embed_request.async_processing:
            # ASYNC PATH: Submit command for background processing
            logger.info(f"Using async processing for {item_type} {item_id}")

            try:
                # Import commands to ensure they're registered
                import commands.embedding_commands  # noqa: F401

                # Submit command
                command_id = await CommandService.submit_command_job(
                    "open_notebook",  # app name
                    "embed_single_item",  # command name
                    {"item_id": item_id, "item_type": item_type},
                )

                logger.info(f"Submitted async embedding command: {command_id}")

                return EmbedResponse(
                    success=True,
                    message="Embedding queued for background processing",
                    item_id=item_id,
                    item_type=item_type,
                    command_id=command_id,
                )

            except Exception as e:
                logger.error(f"Failed to submit async embedding command: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to queue embedding: {str(e)}"
                )

        else:
            # SYNC PATH: Submit job (returns immediately with command_id)
            # NOTE: "sync" here means "submit and return command_id" - actual processing
            # still happens asynchronously in the worker pool
            logger.info(f"Using sync processing for {item_type} {item_id}")

            command_id = None

            # Get the item and embed it
            if item_type == "source":
                source_item = await Source.get(item_id)
                if not source_item:
                    raise HTTPException(status_code=404, detail="Source not found")

                # Submit vectorization job (returns command_id for tracking)
                command_id = await source_item.vectorize()
                message = "Source vectorization job submitted"

            elif item_type == "note":
                note_item = await Note.get(item_id)
                if not note_item:
                    raise HTTPException(status_code=404, detail="Note not found")

                await note_item.save()  # Auto-embeds via ObjectModel.save()
                message = "Note embedded successfully"

            return EmbedResponse(
                success=True, message=message, item_id=item_id, item_type=item_type, command_id=command_id
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
