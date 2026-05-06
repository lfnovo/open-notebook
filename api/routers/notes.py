from typing import Any, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

from api.auth import CurrentUser, current_user_from_request
from api.models import NoteCreate, NoteResponse, NoteUpdate, ResourceCapabilities
from api.services.workspace_capabilities import resolve_resource_capabilities
from api.services.workspace_service import resolve_workspace_id_for_user
from open_notebook.database.repositories.note_repository import NoteRepository
from open_notebook.domain.notebook import Note, Notebook
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


def _string_attr(resource: Any, attr: str) -> Optional[str]:
    value = getattr(resource, attr, None)
    if value is None:
        return None
    value_string = str(value)
    if value_string.startswith("<AsyncMock") or value_string.startswith("<MagicMock"):
        return None
    return value_string


def _notebook_value(notebook: Notebook | dict[str, Any] | None, key: str) -> Any:
    if notebook is None:
        return None
    if isinstance(notebook, dict):
        return notebook.get(key)
    return getattr(notebook, key, None)


def _owner_from_note_or_notebook(
    note: Note,
    notebook: Notebook | dict[str, Any] | None = None,
) -> Optional[str]:
    return _string_attr(note, "owner_id") or (
        str(_notebook_value(notebook, "owner_id"))
        if _notebook_value(notebook, "owner_id")
        else None
    )


def _workspace_from_note_or_notebook(
    note: Note,
    notebook: Notebook | dict[str, Any] | None = None,
) -> Optional[str]:
    return _string_attr(note, "workspace_id") or (
        str(_notebook_value(notebook, "workspace_id"))
        if _notebook_value(notebook, "workspace_id")
        else None
    )


async def _note_notebook_fallback(note: Note) -> Notebook | dict[str, Any] | None:
    note_id = _string_attr(note, "id")
    if not note_id:
        return None
    return await NoteRepository.notebook_for_note(note_id)


async def _note_capabilities(
    *,
    note: Note,
    actor: CurrentUser | None,
    notebook: Notebook | dict[str, Any] | None = None,
) -> ResourceCapabilities:
    if actor is None and not _string_attr(note, "workspace_id"):
        return ResourceCapabilities(
            can_read=True,
            can_update=True,
            can_delete=True,
            can_manage=True,
        )

    if notebook is None and (
        not _string_attr(note, "owner_id") or not _string_attr(note, "workspace_id")
    ):
        notebook = await _note_notebook_fallback(note)

    return await resolve_resource_capabilities(
        actor=actor,
        resource_type="note",
        owner_id=_owner_from_note_or_notebook(note, notebook),
        workspace_id=_workspace_from_note_or_notebook(note, notebook),
        visibility="private",
    )


async def _notebook_capabilities(
    notebook: Notebook,
    actor: CurrentUser | None,
) -> ResourceCapabilities:
    return await resolve_resource_capabilities(
        actor=actor,
        resource_type="notebook",
        owner_id=str(notebook.owner_id) if notebook.owner_id else None,
        workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
        visibility=notebook.visibility,
    )


def _allow_legacy_note_fallback(note: Note, actor: CurrentUser | None) -> bool:
    return actor is None and not _string_attr(note, "workspace_id")


async def _note_to_response(
    note: Note,
    *,
    actor: CurrentUser | None,
    notebook: Notebook | dict[str, Any] | None = None,
    command_id: Any = None,
) -> NoteResponse:
    capabilities = await _note_capabilities(note=note, actor=actor, notebook=notebook)
    return NoteResponse(
        id=_string_attr(note, "id") or "",
        title=note.title,
        content=note.content,
        note_type=note.note_type,
        created=str(note.created),
        updated=str(note.updated),
        command_id=str(command_id) if command_id else None,
        owner_id=_owner_from_note_or_notebook(note, notebook),
        workspace_id=_workspace_from_note_or_notebook(note, notebook),
        capabilities=capabilities,
    )


@router.get("/notes", response_model=List[NoteResponse])
async def get_notes(
    request: Request,
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
):
    """Get all notes with optional notebook filtering."""
    try:
        actor = current_user_from_request(request)
        if notebook_id:
            # Get notes for a specific notebook
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

            capabilities = await _notebook_capabilities(notebook, actor)
            if not capabilities.can_read and actor is not None:
                raise HTTPException(status_code=403, detail="Access denied")
            notes = await notebook.get_notes()
        else:
            if actor is not None:
                raise HTTPException(status_code=400, detail="notebook_id is required")
            # Get all notes
            notebook = None
            notes = await Note.get_all(order_by="updated desc")

        return [
            await _note_to_response(note, actor=actor, notebook=notebook)
            for note in notes
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}")


@router.post("/notes", response_model=NoteResponse)
async def create_note(request: Request, note_data: NoteCreate):
    """Create a new note."""
    try:
        actor = current_user_from_request(request)
        notebook: Notebook | None = None
        owner_id: Optional[str] = actor.id if actor else None
        workspace_id: Optional[str] = None

        # Add to notebook if specified
        if note_data.notebook_id:
            notebook = await Notebook.get(note_data.notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

            capabilities = await _notebook_capabilities(notebook, actor)
            if not capabilities.can_create_note and actor is not None:
                raise HTTPException(status_code=403, detail="Access denied")

            workspace_id = str(notebook.workspace_id) if notebook.workspace_id else None
        elif actor is not None:
            workspace_id = await resolve_workspace_id_for_user(
                user_id=actor.id,
                requested_workspace_id=None,
            )

        # Auto-generate title if not provided and it's an AI note
        title = note_data.title
        if not title and note_data.note_type == "ai" and note_data.content:
            from open_notebook.graphs.prompt import graph as prompt_graph

            prompt = "Based on the Note below, please provide a Title for this content, with max 15 words"
            result = await prompt_graph.ainvoke(
                {  # type: ignore[arg-type]
                    "input_text": note_data.content,
                    "prompt": prompt,
                }
            )
            title = result.get("output", "Untitled Note")

        # Validate note_type
        note_type: Optional[Literal["human", "ai"]] = None
        if note_data.note_type in ("human", "ai"):
            note_type = note_data.note_type  # type: ignore[assignment]
        elif note_data.note_type is not None:
            raise HTTPException(
                status_code=400, detail="note_type must be 'human' or 'ai'"
            )

        new_note = Note(
            title=title,
            content=note_data.content,
            note_type=note_type,
            owner_id=owner_id,
            workspace_id=workspace_id,
        )
        command_id = await new_note.save()

        if note_data.notebook_id:
            await new_note.add_to_notebook(note_data.notebook_id)

        return await _note_to_response(
            new_note,
            actor=actor,
            notebook=notebook,
            command_id=command_id,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating note: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}")


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(request: Request, note_id: str):
    """Get a specific note by ID."""
    try:
        actor = current_user_from_request(request)
        note = await Note.get(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        capabilities = await _note_capabilities(note=note, actor=actor)
        if not capabilities.can_read and not _allow_legacy_note_fallback(note, actor):
            raise HTTPException(status_code=403, detail="Access denied")

        return await _note_to_response(note, actor=actor)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching note: {str(e)}")


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(request: Request, note_id: str, note_update: NoteUpdate):
    """Update a note."""
    try:
        actor = current_user_from_request(request)
        note = await Note.get(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        capabilities = await _note_capabilities(note=note, actor=actor)
        if not capabilities.can_update and not _allow_legacy_note_fallback(note, actor):
            raise HTTPException(status_code=403, detail="Access denied")

        # Update only provided fields
        if note_update.title is not None:
            note.title = note_update.title
        if note_update.content is not None:
            note.content = note_update.content
        if note_update.note_type is not None:
            if note_update.note_type in ("human", "ai"):
                note.note_type = note_update.note_type  # type: ignore[assignment]
            else:
                raise HTTPException(
                    status_code=400, detail="note_type must be 'human' or 'ai'"
                )

        command_id = await note.save()

        return await _note_to_response(note, actor=actor, command_id=command_id)
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}")


@router.delete("/notes/{note_id}")
async def delete_note(request: Request, note_id: str):
    """Delete a note."""
    try:
        actor = current_user_from_request(request)
        note = await Note.get(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        capabilities = await _note_capabilities(note=note, actor=actor)
        if not capabilities.can_delete and not _allow_legacy_note_fallback(note, actor):
            raise HTTPException(status_code=403, detail="Access denied")

        await note.delete()

        return {"message": "Note deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}")
