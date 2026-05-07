from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

from api.auth import current_user_from_request
from api.models import (
    NotebookCreate,
    NotebookDeletePreview,
    NotebookDeleteResponse,
    NotebookResponse,
    NotebookUpdate,
    NotebookVisibilityUpdate,
)
from api.services.share_service import can_read_resource
from api.services.workspace_capabilities import resolve_resource_capabilities
from api.services.workspace_service import resolve_workspace_id_for_user
from open_notebook.database.repositories.notebook_repository import NotebookRepository
from open_notebook.database.repositories.share_repository import (
    PUBLIC_TEAM_ID,
    ShareRepository,
)
from open_notebook.database.repositories.team_repository import TeamRepository
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


async def _notebook_to_response(nb: dict, request: Request | None = None) -> NotebookResponse:
    actor = current_user_from_request(request) if request else None
    capabilities = await resolve_resource_capabilities(
        actor=actor,
        resource_type="notebook",
        owner_id=str(nb.get("owner_id")) if nb.get("owner_id") else None,
        workspace_id=str(nb.get("workspace_id")) if nb.get("workspace_id") else None,
        visibility=nb.get("visibility", "private"),
    )
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
        creator_username=nb.get("creator_username"),
        owner_id=nb.get("owner_id"),
        workspace_id=str(nb.get("workspace_id")) if nb.get("workspace_id") else None,
        visibility=nb.get("visibility", "private"),
        capabilities=capabilities,
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


async def _notebook_capabilities_from_domain(
    notebook: Notebook,
    request: Request,
):
    workspace_id = _notebook_workspace_id(notebook)
    owner_id = _notebook_owner_id(notebook)
    return await resolve_resource_capabilities(
        actor=current_user_from_request(request),
        resource_type="notebook",
        owner_id=str(owner_id) if owner_id else None,
        workspace_id=str(workspace_id) if workspace_id else None,
        visibility=_notebook_visibility(notebook),
    )


def _notebook_workspace_id(notebook: Notebook) -> object | None:
    return getattr(notebook, "workspace_id", None)


def _notebook_owner_id(notebook: Notebook) -> object | None:
    return getattr(notebook, "owner_id", None)


def _notebook_visibility(notebook: Notebook) -> str:
    return getattr(notebook, "visibility", "private")


def _allow_legacy_owner_fallback(resource_workspace_id, request: Request) -> bool:
    return current_user_from_request(request) is None or not resource_workspace_id


def _visibility_for_workspace(requested_visibility: str, workspace_role: dict | None) -> str:
    if workspace_role and workspace_role.get("type") == "team":
        return "public" if requested_visibility == "public" else "team"
    return requested_visibility


async def _initial_notebook_workspace_role(
    *,
    actor_id: str | None,
    workspace_id: str | None,
) -> dict | None:
    if not actor_id or not workspace_id:
        return None
    return await WorkspaceRepository.current_user_role(
        workspace_id=workspace_id,
        user_id=actor_id,
    )


async def _create_initial_notebook_grants(
    *,
    notebook_id: str,
    visibility: str,
    workspace_role: dict | None,
    actor_id: str | None,
) -> None:
    team_id = (
        str(workspace_role.get("team_id"))
        if workspace_role and workspace_role.get("team_id")
        else None
    )
    if team_id:
        await ShareRepository.create_grant(
            resource_type="notebook",
            resource_id=notebook_id,
            target_type="team",
            target_id=team_id,
            permission="read",
            created_by=actor_id,
        )
    if visibility == "public":
        await ShareRepository.create_grant(
            resource_type="notebook",
            resource_id=notebook_id,
            target_type="team",
            target_id=PUBLIC_TEAM_ID,
            permission="read",
            created_by=actor_id,
        )


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
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
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
            workspace_id=workspace_id,
        )

        return [await _notebook_to_response(nb, request) for nb in result]
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

        return [await _notebook_to_response(nb) for nb in result]
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
    username: Optional[str] = getattr(request.state, "username", None)
    actor = current_user_from_request(request)
    try:
        workspace_id = await resolve_workspace_id_for_user(
            user_id=user_id,
            requested_workspace_id=notebook.workspace_id,
        )
        workspace_role = await _initial_notebook_workspace_role(
            actor_id=actor.id if actor else None,
            workspace_id=workspace_id,
        )
        visibility = _visibility_for_workspace(notebook.visibility, workspace_role)
        new_notebook = Notebook(
            name=notebook.name,
            description=notebook.description,
            password=notebook.password,
            creator_name=notebook.creator_name,
            owner_id=user_id,
            workspace_id=workspace_id,
            visibility=visibility,
        )
        await new_notebook.save()
        await _create_initial_notebook_grants(
            notebook_id=str(new_notebook.id),
            visibility=new_notebook.visibility,
            workspace_role=workspace_role,
            actor_id=actor.id if actor else None,
        )
        capabilities = await resolve_resource_capabilities(
            actor=actor,
            resource_type="notebook",
            owner_id=str(new_notebook.owner_id) if new_notebook.owner_id else None,
            workspace_id=str(new_notebook.workspace_id)
            if new_notebook.workspace_id
            else None,
            visibility=new_notebook.visibility,
        )

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
            creator_username=username,
            owner_id=new_notebook.owner_id,
            workspace_id=str(new_notebook.workspace_id)
            if new_notebook.workspace_id
            else None,
            visibility=new_notebook.visibility,
            capabilities=capabilities,
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
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

        capabilities = await _notebook_capabilities_from_domain(notebook, request)
        if not capabilities.can_delete and not (
            _allow_legacy_owner_fallback(_notebook_workspace_id(notebook), request)
            and _check_notebook_access(
                {
                    "owner_id": _notebook_owner_id(notebook),
                    "visibility": _notebook_visibility(notebook),
                },
                user_id,
                require_owner=True,
            )
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

        capabilities = await resolve_resource_capabilities(
            actor=current_user_from_request(request),
            resource_type="notebook",
            owner_id=str(nb.get("owner_id")) if nb.get("owner_id") else None,
            workspace_id=str(nb.get("workspace_id")) if nb.get("workspace_id") else None,
            visibility=nb.get("visibility", "private"),
        )
        if not capabilities.can_read and not await can_read_resource(
            resource_type="notebook",
            resource_id=str(nb.get("id", notebook_id)),
            user_id=user_id,
            owner_id=str(nb.get("owner_id")) if nb.get("owner_id") else None,
            visibility=nb.get("visibility", "private"),
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        return await _notebook_to_response(nb, request)
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
    username: Optional[str] = getattr(request.state, "username", None)
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        capabilities = await _notebook_capabilities_from_domain(notebook, request)
        if not capabilities.can_update and not (
            _allow_legacy_owner_fallback(_notebook_workspace_id(notebook), request)
            and _check_notebook_access(
                {
                    "owner_id": _notebook_owner_id(notebook),
                    "visibility": _notebook_visibility(notebook),
                },
                user_id,
                require_owner=True,
            )
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
            return await _notebook_to_response(nb, request)

        # Fallback if query fails
        capabilities = await resolve_resource_capabilities(
            actor=current_user_from_request(request),
            resource_type="notebook",
            owner_id=str(notebook.owner_id) if notebook.owner_id else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
        )
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
            creator_username=username,
            owner_id=notebook.owner_id,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
            capabilities=capabilities,
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
    username: Optional[str] = getattr(request.state, "username", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        capabilities = await _notebook_capabilities_from_domain(notebook, request)
        if not capabilities.can_share and not (
            _allow_legacy_owner_fallback(_notebook_workspace_id(notebook), request)
            and _check_notebook_access(
                {
                    "owner_id": _notebook_owner_id(notebook),
                    "visibility": _notebook_visibility(notebook),
                },
                user_id,
                require_owner=True,
            )
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
            return await _notebook_to_response(nb, request)

        capabilities = await resolve_resource_capabilities(
            actor=current_user_from_request(request),
            resource_type="notebook",
            owner_id=str(notebook.owner_id) if notebook.owner_id else None,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
        )
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
            creator_username=username,
            owner_id=notebook.owner_id,
            workspace_id=str(notebook.workspace_id) if notebook.workspace_id else None,
            visibility=notebook.visibility,
            capabilities=capabilities,
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

        capabilities = await _notebook_capabilities_from_domain(notebook, request)
        if not capabilities.can_create_source and not (
            _allow_legacy_owner_fallback(_notebook_workspace_id(notebook), request)
            and _check_notebook_access(
                {
                    "owner_id": _notebook_owner_id(notebook),
                    "visibility": _notebook_visibility(notebook),
                },
                user_id,
                require_owner=True,
            )
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        source_capabilities = await resolve_resource_capabilities(
            actor=current_user_from_request(request),
            resource_type="source",
            owner_id=str(source.owner_id) if source.owner_id else None,
            workspace_id=str(source.workspace_id) if source.workspace_id else None,
            visibility=source.visibility,
        )
        if not source_capabilities.can_read and not await can_read_resource(
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

        capabilities = await _notebook_capabilities_from_domain(notebook, request)
        if not capabilities.can_remove_source and not (
            _allow_legacy_owner_fallback(_notebook_workspace_id(notebook), request)
            and _check_notebook_access(
                {
                    "owner_id": _notebook_owner_id(notebook),
                    "visibility": _notebook_visibility(notebook),
                },
                user_id,
                require_owner=True,
            )
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

        capabilities = await _notebook_capabilities_from_domain(notebook, request)
        if not capabilities.can_delete and not (
            _allow_legacy_owner_fallback(_notebook_workspace_id(notebook), request)
            and _check_notebook_access(
                {
                    "owner_id": _notebook_owner_id(notebook),
                    "visibility": _notebook_visibility(notebook),
                },
                user_id,
                require_owner=True,
            )
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
