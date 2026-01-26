from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import ContextRequest, ContextResponse
from backpack.domain.module import Note, Module, Source
from backpack.exceptions import InvalidInputError
from backpack.utils import token_count

router = APIRouter()


@router.post("/modules/{module_id}/context", response_model=ContextResponse)
async def get_module_context(module_id: str, context_request: ContextRequest):
    """Get context for a module based on configuration."""
    try:
        # Verify module exists
        module = await Module.get(module_id)
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")

        context_data: dict[str, list[dict[str, str]]] = {"note": [], "source": []}
        total_content = ""

        # Process context configuration if provided
        if context_request.context_config:
            # Process sources
            for source_id, status in context_request.context_config.sources.items():
                if "not in" in status:
                    continue

                try:
                    # Add table prefix if not present
                    full_source_id = (
                        source_id
                        if source_id.startswith("source:")
                        else f"source:{source_id}"
                    )

                    try:
                        source = await Source.get(full_source_id)
                    except Exception:
                        continue

                    if "insights" in status:
                        source_context = await source.get_context(context_size="short")
                        context_data["source"].append(source_context)
                        total_content += str(source_context)
                    elif "full content" in status:
                        source_context = await source.get_context(context_size="long")
                        context_data["source"].append(source_context)
                        total_content += str(source_context)
                except Exception as e:
                    logger.warning(f"Error processing source {source_id}: {str(e)}")
                    continue

            # Process notes
            for note_id, status in context_request.context_config.notes.items():
                if "not in" in status:
                    continue

                try:
                    # Add table prefix if not present
                    full_note_id = (
                        note_id if note_id.startswith("note:") else f"note:{note_id}"
                    )
                    note = await Note.get(full_note_id)
                    if not note:
                        continue

                    if "full content" in status:
                        note_context = note.get_context(context_size="long")
                        context_data["note"].append(note_context)
                        total_content += str(note_context)
                except Exception as e:
                    logger.warning(f"Error processing note {note_id}: {str(e)}")
                    continue
        else:
            # Default behavior - include all sources and notes with short context
            sources = await module.get_sources()
            for source in sources:
                try:
                    source_context = await source.get_context(context_size="short")
                    context_data["source"].append(source_context)
                    total_content += str(source_context)
                except Exception as e:
                    logger.warning(f"Error processing source {source.id}: {str(e)}")
                    continue

            notes = await module.get_notes()
            for note in notes:
                try:
                    note_context = note.get_context(context_size="short")
                    context_data["note"].append(note_context)
                    total_content += str(note_context)
                except Exception as e:
                    logger.warning(f"Error processing note {note.id}: {str(e)}")
                    continue

        # Calculate estimated token count
        estimated_tokens = token_count(total_content) if total_content else 0

        return ContextResponse(
            module_id=module_id,
            sources=context_data["source"],
            notes=context_data["note"],
            total_tokens=estimated_tokens,
        )

    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting context for module {module_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting context: {str(e)}")
