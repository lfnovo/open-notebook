"""Notebook folders: simple one-level grouping of notebooks."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import FolderDeleteResponse, FolderRequest, FolderResponse
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import Folder
from open_notebook.exceptions import (
    InvalidInputError,
    NotFoundError,
    OpenNotebookError,
)

router = APIRouter()

MAX_FOLDER_NAME_LENGTH = 80


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise InvalidInputError("Folder name cannot be empty")
    if len(name) > MAX_FOLDER_NAME_LENGTH:
        raise InvalidInputError(
            f"Folder name cannot be longer than {MAX_FOLDER_NAME_LENGTH} characters"
        )
    return name


async def _assert_name_free(name: str, exclude_id: Optional[str] = None) -> None:
    rows = await repo_query("SELECT id, name FROM folder")
    wanted = name.casefold()
    for row in rows:
        if exclude_id and str(row.get("id")) == exclude_id:
            continue
        if str(row.get("name", "")).strip().casefold() == wanted:
            raise HTTPException(
                status_code=409, detail=f"A folder named '{name}' already exists"
            )


async def _get_folder(folder_id: str) -> Folder:
    # Folder.get() resolves by id prefix, so guard against ids of other tables.
    try:
        folder = await Folder.get(folder_id)
    except InvalidInputError:
        raise NotFoundError(f"folder {folder_id} not found") from None
    if not isinstance(folder, Folder):
        raise NotFoundError(f"folder {folder_id} not found")
    return folder


def _response(folder: Folder, notebook_count: int = 0) -> FolderResponse:
    return FolderResponse(
        id=folder.id or "",
        name=folder.name,
        created=str(folder.created),
        updated=str(folder.updated),
        notebook_count=notebook_count,
    )


async def _notebook_count(folder_id: str) -> int:
    rows = await repo_query(
        "SELECT count() AS n FROM notebook WHERE folder = $folder GROUP ALL",
        {"folder": ensure_record_id(folder_id)},
    )
    return int(rows[0].get("n", 0)) if rows else 0


@router.get("/folders", response_model=List[FolderResponse])
async def get_folders():
    """List folders sorted by name, with their notebook counts."""
    try:
        folders = await repo_query(
            "SELECT *, count(SELECT id FROM notebook WHERE folder = $parent.id) "
            "AS notebook_count FROM folder"
        )
        folders.sort(key=lambda f: (str(f.get("name", "")).casefold(), str(f["id"])))
        return [
            FolderResponse(
                id=str(f.get("id", "")),
                name=f.get("name", ""),
                created=str(f.get("created", "")),
                updated=str(f.get("updated", "")),
                notebook_count=f.get("notebook_count", 0),
            )
            for f in folders
        ]
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching folders: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching folders: {e}")


@router.post("/folders", response_model=FolderResponse)
async def create_folder(body: FolderRequest):
    """Create a folder. 409 if the name exists (case-insensitive)."""
    try:
        name = _clean_name(body.name)
        await _assert_name_free(name)
        folder = Folder(name=name)
        await folder.save()
        return _response(folder)
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating folder: {e}")


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def rename_folder(folder_id: str, body: FolderRequest):
    """Rename a folder. 409 if another folder has the name (case-insensitive)."""
    try:
        folder = await _get_folder(folder_id)
        name = _clean_name(body.name)
        await _assert_name_free(name, exclude_id=folder.id)
        folder.name = name
        await folder.save()
        return _response(folder, await _notebook_count(folder_id))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error renaming folder {folder_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error renaming folder: {e}")


@router.delete("/folders/{folder_id}", response_model=FolderDeleteResponse)
async def delete_folder(folder_id: str):
    """Delete a folder. Its notebooks are kept and become ungrouped."""
    try:
        folder = await _get_folder(folder_id)
        record = ensure_record_id(folder_id)
        ungrouped = await repo_query(
            "UPDATE notebook SET folder = NONE WHERE folder = $folder RETURN id",
            {"folder": record},
        )
        await folder.delete()
        return FolderDeleteResponse(
            message="Folder deleted successfully",
            notebooks_ungrouped=len(ungrouped),
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error deleting folder {folder_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting folder: {e}")
