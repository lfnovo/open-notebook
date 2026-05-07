from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from api.auth import current_user_from_request
from api.models import ContextRequest, ContextResponse
from api.services.workspace_capabilities import resolve_resource_capabilities
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils import token_count

router = APIRouter()


def _record_id(table: str, record_id: str) -> str:
    return record_id if record_id.startswith(f"{table}:") else f"{table}:{record_id}"


@router.post("/notebooks/{notebook_id}/context", response_model=ContextResponse)
async def get_notebook_context(
    notebook_id: str,
    context_request: ContextRequest,
    http_request: Request,
):
    """Get context for a notebook based on configuration."""
    try:
        # Verify notebook exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        actor = current_user_from_request(http_request)
        notebook_capabilities = await resolve_resource_capabilities(
            actor=actor,
            resource_type="notebook",
            owner_id=str(notebook.owner_id) if notebook.owner_id else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
        )
        if not notebook_capabilities.can_read:
            raise HTTPException(status_code=403, detail="Access denied")

        context_data: dict[str, list[dict[str, str]]] = {"note": [], "source": []}
        total_content = ""
        notebook_sources = await notebook.get_sources()
        notebook_notes = await notebook.get_notes()
        sources_by_id = {
            str(source.id): source for source in notebook_sources if getattr(source, "id", None)
        }
        notes_by_id = {
            str(note.id): note for note in notebook_notes if getattr(note, "id", None)
        }

        # Process context configuration if provided
        if context_request.context_config:
            # Process sources
            for source_id, status in context_request.context_config.sources.items():
                if "not in" in status:
                    continue

                try:
                    # Add table prefix if not present
                    full_source_id = _record_id("source", source_id)
                    source = sources_by_id.get(full_source_id)
                    if not source:
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
                    full_note_id = _record_id("note", note_id)
                    note = notes_by_id.get(full_note_id)
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
            for source in notebook_sources:
                try:
                    source_context = await source.get_context(context_size="short")
                    context_data["source"].append(source_context)
                    total_content += str(source_context)
                except Exception as e:
                    logger.warning(f"Error processing source {source.id}: {str(e)}")
                    continue

            for note in notebook_notes:
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
            notebook_id=notebook_id,
            sources=context_data["source"],
            notes=context_data["note"],
            total_tokens=estimated_tokens,
        )

    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting context for notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting context: {str(e)}")
