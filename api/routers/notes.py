from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from loguru import logger

from api.models import NoteAttachment, NoteCreate, NoteResponse, NoteUpdate
from open_notebook.domain.notebook import Note
from open_notebook.exceptions import (
    InvalidInputError,
    NotFoundError,
    OpenNotebookError,
)
from open_notebook.utils.note_files import (
    ALLOWED_TYPES,
    classify_upload,
    extract_note_text,
    note_file_path,
    remove_note_file,
    store_note_file,
)

router = APIRouter()

MAX_NOTE_FILE_TITLE = 200
NO_TEXT_PLACEHOLDER = (
    "(No text could be extracted from this file. Open it to view the original.)"
)


def _note_response(note: Note, command_id=None) -> NoteResponse:
    attachment = (
        NoteAttachment(
            name=note.attachment_name,
            type=note.attachment_mime or "application/octet-stream",
            size=note.attachment_size or 0,
        )
        if note.attachment_name and note.attachment_file
        else None
    )
    return NoteResponse(
        id=note.id or "",
        title=note.title,
        content=note.content,
        note_type=note.note_type,
        created=str(note.created),
        updated=str(note.updated),
        command_id=str(command_id) if command_id else None,
        attachment=attachment,
    )


@router.get("/notes", response_model=List[NoteResponse])
async def get_notes(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
):
    """Get all notes with optional notebook filtering."""
    try:
        if notebook_id:
            # Get notes for a specific notebook
            from open_notebook.domain.notebook import Notebook

            notebook = await Notebook.get(notebook_id)
            notes = await notebook.get_notes()
        else:
            # Get all notes
            notes = await Note.get_all(order_by="updated desc")

        return [_note_response(note) for note in notes]
    except HTTPException:
        raise
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching notes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}")


@router.post("/notes", response_model=NoteResponse)
async def create_note(note_data: NoteCreate):
    """Create a new note."""
    try:
        # Auto-generate title if not provided and it's an AI note
        title = note_data.title
        if not title and note_data.note_type == "ai" and note_data.content:
            from open_notebook.graphs.prompt import graph as prompt_graph

            prompt = "Based on the Note below, please provide a Title for this content, with max 15 words"
            # LangGraph accepts a partial state dict at runtime, but its typed
            # overloads require the full state type (langgraph typing limitation).
            result = await prompt_graph.ainvoke(  # type: ignore[call-overload]
                {
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
        )
        command_id = await new_note.save()

        # Add to notebook if specified
        if note_data.notebook_id:
            from open_notebook.domain.notebook import Notebook

            # Verify the notebook exists (raises NotFoundError -> 404)
            await Notebook.get(note_data.notebook_id)
            await new_note.add_to_notebook(note_data.notebook_id)

        return _note_response(new_note, command_id)
    except HTTPException:
        raise
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error creating note: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}")


@router.post("/notes/upload", response_model=NoteResponse)
async def upload_note_file(
    file: UploadFile = File(...),
    notebook_id: str = Form(...),
):
    """Create a note from a dropped file (PDF, HTML, DOCX, TXT, Markdown).

    The original is kept (download/preview via ``GET /notes/{id}/file``) and
    the text extracted from it becomes the note content, so it is searchable
    and usable as chat context like any other note.
    """
    from open_notebook.domain.notebook import Notebook

    stored: Optional[str] = None
    note: Optional[Note] = None
    try:
        # Verify the notebook first (raises NotFoundError -> 404).
        await Notebook.get(notebook_id)

        filename = Path((file.filename or "").replace("\\", "/")).name
        data = await file.read()
        if not data:
            raise InvalidInputError("The file is empty")
        _, mime = classify_upload(filename, data[:8192])
        ext = Path(filename).suffix.lower()

        stored = await store_note_file(data, ext)
        text = await extract_note_text(note_file_path(stored))

        note = Note(
            title=filename[:MAX_NOTE_FILE_TITLE],
            content=text or NO_TEXT_PLACEHOLDER,
            note_type="human",
            attachment_name=filename[:MAX_NOTE_FILE_TITLE],
            attachment_file=stored,
            attachment_mime=mime,
            attachment_size=len(data),
        )
        command_id = await note.save()
        await note.add_to_notebook(notebook_id)
        return _note_response(note, command_id)
    except NotFoundError:
        await _discard_upload(note, stored)
        raise HTTPException(status_code=404, detail="Notebook not found")
    except InvalidInputError as e:
        await _discard_upload(note, stored)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        await _discard_upload(note, stored)
        raise
    except OpenNotebookError:
        await _discard_upload(note, stored)
        raise
    except Exception as e:
        await _discard_upload(note, stored)
        logger.error(f"Error uploading note file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


async def _discard_upload(note: Optional[Note], stored: Optional[str]) -> None:
    """Undo a failed upload: remove a saved-but-unlinked note and the stored file."""
    if note is not None and note.id:
        try:
            await note.delete()
        except Exception as e:
            logger.warning(f"Failed to remove orphan note {note.id}: {e}")
    if stored:
        remove_note_file(stored)


@router.get("/notes/{note_id}/file")
async def get_note_file(
    note_id: str,
    download: bool = Query(False, description="Send as an attachment"),
):
    """Serve the original file of a note created from a dropped file."""
    try:
        note = await Note.get(note_id)
        if not isinstance(note, Note) or not note.attachment_file:
            raise HTTPException(status_code=404, detail="This note has no file")
        path = note_file_path(note.attachment_file)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="The file is no longer on disk")

        # Type comes from our allow-list (by extension), not from the upload.
        mime = ALLOWED_TYPES.get(path.suffix.lower(), "application/octet-stream")
        headers = {"X-Content-Type-Options": "nosniff"}
        if mime == "text/html":
            # Uploaded HTML must never run scripts in the app's origin.
            headers["Content-Security-Policy"] = "sandbox"
        return FileResponse(
            path,
            media_type=mime,
            filename=note.attachment_name or path.name,
            content_disposition_type="attachment" if download else "inline",
            headers=headers,
        )
    except HTTPException:
        raise
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error serving file for note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str):
    """Get a specific note by ID."""
    try:
        note = await Note.get(note_id)

        return _note_response(note)
    except HTTPException:
        raise
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found")
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching note: {str(e)}")


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, note_update: NoteUpdate):
    """Update a note."""
    try:
        note = await Note.get(note_id)

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

        return _note_response(note, command_id)
    except HTTPException:
        raise
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error updating note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}")


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a note."""
    try:
        note = await Note.get(note_id)

        await note.delete()

        return {"message": "Note deleted successfully"}
    except HTTPException:
        raise
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found")
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}")
