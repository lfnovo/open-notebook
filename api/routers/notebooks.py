from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

from api.models import (
    NotebookCreate,
    NotebookDeletePreview,
    NotebookDeleteResponse,
    NotebookResponse,
    NotebookUpdate,
    NotebookVisibilityUpdate,
)
from api.services.share_service import can_read_resource
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.database.repositories.notebook_repository import NotebookRepository
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


def _notebook_to_response(nb: dict) -> NotebookResponse:
    return NotebookResponse(
        id=str(nb.get("id", "")),
        name=nb.get("name", ""),
        description=nb.get("description", ""),
        archived=nb.get("archived", False),
        created=str(nb.get("created", "")),
        updated=str(nb.get("updated", "")),
        source_count=nb.get("source_count", 0),
        note_count=nb.get("note_count", 0),
        password=nb.get("password"),
        creator_name=nb.get("creator_name"),
        owner_id=nb.get("owner_id"),
        visibility=nb.get("visibility", "private"),
    )


def _check_notebook_access(
    nb: dict, user_id: Optional[str], require_owner: bool = False
) -> bool:
    """Check notebook access.

    - Read access: public notebooks or owner-only private notebooks.
    - Write access (require_owner=True): owner only, even if public.
    """
    owner_id = nb.get("owner_id")
    is_owner = user_id is not None and owner_id is not None and str(owner_id) == user_id
    if require_owner:
        return is_owner

    visibility = nb.get("visibility", "private")
    if visibility == "public":
        return True
    if visibility == "private":
        return is_owner
    return False


def _validate_notebook_order_by(order_by: str) -> str:
    allowed_fields = {"name", "created", "updated"}
    allowed_directions = {"asc", "desc"}

    parts = order_by.strip().lower().split()
    if len(parts) == 1:
        if parts[0] not in allowed_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order_by field: '{order_by}'. Allowed fields: {', '.join(sorted(allowed_fields))}",
            )
        return parts[0]
    if len(parts) == 2:
        if parts[0] not in allowed_fields or parts[1] not in allowed_directions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order_by: '{order_by}'. Allowed fields: {', '.join(sorted(allowed_fields))}. Allowed directions: asc, desc",
            )
        return f"{parts[0]} {parts[1]}"
    raise HTTPException(
        status_code=400,
        detail=f"Invalid order_by format: '{order_by}'. Expected 'field' or 'field direction'",
    )


@router.get("/notebooks", response_model=List[NotebookResponse])
async def get_notebooks(
    request: Request,
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
):
    """Get all notebooks with optional filtering and ordering.

    Returns notebooks owned by the user (private + public) plus all public notebooks.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    team_ids = await TeamRepository.user_team_ids(user_id) if user_id else []

    try:
        validated_order_by = _validate_notebook_order_by(order_by)
        result = await NotebookRepository.list_notebooks(
            user_id=user_id,
            team_ids=team_ids,
            archived=archived,
            order_by=validated_order_by,
        )

        return [_notebook_to_response(nb) for nb in result]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notebooks: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching notebooks: {str(e)}"
        )


@router.get("/notebooks/public", response_model=List[NotebookResponse])
async def get_public_notebooks(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
):
    """Browse public notebooks without authentication."""
    try:
        validated_order_by = _validate_notebook_order_by(order_by)
        result = await NotebookRepository.list_notebooks(
            user_id=None,
            archived=archived,
            order_by=validated_order_by,
            public_only=True,
        )

        return [_notebook_to_response(nb) for nb in result]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching public notebooks: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching public notebooks: {str(e)}"
        )


@router.post("/notebooks", response_model=NotebookResponse)
async def create_notebook(request: Request, notebook: NotebookCreate):
    """Create a new notebook. Sets owner_id from authenticated user."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        new_notebook = Notebook(
            name=notebook.name,
            description=notebook.description,
            password=notebook.password,
            creator_name=notebook.creator_name,
            owner_id=user_id,
            visibility=notebook.visibility,
        )
        await new_notebook.save()

        return NotebookResponse(
            id=new_notebook.id or "",
            name=new_notebook.name,
            description=new_notebook.description,
            archived=new_notebook.archived or False,
            created=str(new_notebook.created),
            updated=str(new_notebook.updated),
            source_count=0,  # New notebook has no sources
            note_count=0,  # New notebook has no notes
            password=new_notebook.password,
            creator_name=new_notebook.creator_name,
            owner_id=new_notebook.owner_id,
            visibility=new_notebook.visibility,
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating notebook: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating notebook: {str(e)}"
        )


@router.get(
    "/notebooks/{notebook_id}/delete-preview", response_model=NotebookDeletePreview
)
async def get_notebook_delete_preview(request: Request, notebook_id: str):
    """Get a preview of what will be deleted when this notebook is deleted. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        if not _check_notebook_access(
            {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
            user_id,
            require_owner=True,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        preview = await notebook.get_delete_preview()

        return NotebookDeletePreview(
            notebook_id=str(notebook.id),
            notebook_name=notebook.name,
            note_count=preview["note_count"],
            exclusive_source_count=preview["exclusive_source_count"],
            shared_source_count=preview["shared_source_count"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delete preview for notebook {notebook_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching notebook deletion preview: {str(e)}",
        )


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(request: Request, notebook_id: str):
    """Get a specific notebook by ID. Requires ownership (private) or public."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        nb = await NotebookRepository.get_with_counts(notebook_id)
        if not nb:
            raise HTTPException(status_code=404, detail="Notebook not found")

        if not await can_read_resource(
            resource_type="notebook",
            resource_id=str(nb.get("id", notebook_id)),
            user_id=user_id,
            owner_id=str(nb.get("owner_id")) if nb.get("owner_id") else None,
            visibility=nb.get("visibility", "private"),
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        return _notebook_to_response(nb)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notebook {notebook_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching notebook: {str(e)}"
        )


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    request: Request, notebook_id: str, notebook_update: NotebookUpdate
):
    """Update a notebook. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Ownership check
        if not _check_notebook_access(
            {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
            user_id,
            require_owner=True,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        # Update only provided fields
        if notebook_update.name is not None:
            notebook.name = notebook_update.name
        if notebook_update.description is not None:
            notebook.description = notebook_update.description
        if notebook_update.archived is not None:
            notebook.archived = notebook_update.archived
        if notebook_update.password is not None:
            notebook.password = notebook_update.password
        if notebook_update.creator_name is not None:
            notebook.creator_name = notebook_update.creator_name
        if notebook_update.visibility is not None:
            notebook.visibility = notebook_update.visibility

        await notebook.save()

        nb = await NotebookRepository.get_with_counts(notebook_id)
        if nb:
            return _notebook_to_response(nb)

        # Fallback if query fails
        return NotebookResponse(
            id=notebook.id or "",
            name=notebook.name,
            description=notebook.description,
            archived=notebook.archived or False,
            created=str(notebook.created),
            updated=str(notebook.updated),
            source_count=0,
            note_count=0,
            password=notebook.password,
            creator_name=notebook.creator_name,
            owner_id=notebook.owner_id,
            visibility=notebook.visibility,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notebook {notebook_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error updating notebook: {str(e)}"
        )


@router.patch("/notebooks/{notebook_id}/visibility", response_model=NotebookResponse)
async def update_notebook_visibility(request: Request, notebook_id: str):
    """Make a private notebook public. One-way only — cannot revert to private.

    Requires ownership. Returns the updated notebook.
    """
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        if not _check_notebook_access(
            {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
            user_id,
            require_owner=True,
        ):
            raise HTTPException(
                status_code=403, detail="Access denied — you do not own this notebook"
            )

        if notebook.visibility == "public":
            raise HTTPException(
                status_code=400,
                detail="Notebook is already public. Making a notebook private is not supported.",
            )

        notebook.visibility = "public"
        await notebook.save()

        nb = await NotebookRepository.get_with_counts(notebook_id)
        if nb:
            return _notebook_to_response(nb)

        return NotebookResponse(
            id=notebook.id or "",
            name=notebook.name,
            description=notebook.description,
            archived=notebook.archived or False,
            created=str(notebook.created),
            updated=str(notebook.updated),
            source_count=0,
            note_count=0,
            password=notebook.password,
            creator_name=notebook.creator_name,
            owner_id=notebook.owner_id,
            visibility=notebook.visibility,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notebook visibility {notebook_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating notebook visibility: {str(e)}",
        )


@router.post("/notebooks/{notebook_id}/sources/{source_id}")
async def add_source_to_notebook(request: Request, notebook_id: str, source_id: str):
    """Add an existing source to a notebook (create the reference). Requires notebook ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        # Check if notebook exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Ownership check
        if not _check_notebook_access(
            {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
            user_id,
            require_owner=True,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not await can_read_resource(
            resource_type="source",
            resource_id=source.id or source_id,
            user_id=user_id,
            owner_id=str(source.owner_id) if source.owner_id else None,
            visibility=source.visibility,
        ):
            raise HTTPException(status_code=403, detail="Source access denied")

        await NotebookRepository.link_source(notebook_id, source_id)

        return {"message": "Source linked to notebook successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error linking source {source_id} to notebook {notebook_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error linking source to notebook: {str(e)}"
        )


@router.delete("/notebooks/{notebook_id}/sources/{source_id}")
async def remove_source_from_notebook(
    request: Request, notebook_id: str, source_id: str
):
    """Remove a source from a notebook (delete the reference). Requires notebook ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        # Check if notebook exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Ownership check
        if not _check_notebook_access(
            {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
            user_id,
            require_owner=True,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        await NotebookRepository.unlink_source(notebook_id, source_id)

        return {"message": "Source removed from notebook successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error removing source {source_id} from notebook {notebook_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error removing source from notebook: {str(e)}"
        )


@router.delete("/notebooks/{notebook_id}", response_model=NotebookDeleteResponse)
async def delete_notebook(
    request: Request,
    notebook_id: str,
    delete_exclusive_sources: bool = Query(
        False,
        description="Whether to delete sources that belong only to this notebook",
    ),
):
    """Delete a notebook with cascade deletion. Requires ownership."""
    user_id: Optional[str] = getattr(request.state, "user_id", None)
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Ownership check
        if not _check_notebook_access(
            {"owner_id": notebook.owner_id, "visibility": notebook.visibility},
            user_id,
            require_owner=True,
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        result = await notebook.delete(
            delete_exclusive_sources=delete_exclusive_sources
        )

        return NotebookDeleteResponse(
            message="Notebook deleted successfully",
            deleted_notes=result["deleted_notes"],
            deleted_sources=result["deleted_sources"],
            unlinked_sources=result["unlinked_sources"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notebook {notebook_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting notebook: {str(e)}"
        )
