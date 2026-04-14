"""
Workspace API endpoints.

CRUD for workspaces, member management, and community discovery.
All workspace-scoped endpoints enforce RBAC via dependency functions.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger

from api.models import (
    CreateWorkspaceRequest,
    InviteMemberRequest,
    UpdateWorkspaceRequest,
    WorkspaceDeleteResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)
from api.rbac import require_editor, require_owner, require_viewer
from api.workspace_service import (
    create_workspace,
    delete_workspace,
    discover_community_workspaces,
    get_workspace,
    invite_member,
    list_workspaces_for_user,
    remove_member,
    update_workspace,
)

router = APIRouter()


def _to_workspace_response(workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        description=workspace.description,
        visibility=workspace.visibility,
        owner_id=workspace.owner_id,
        org_id=workspace.org_id,
        created=str(workspace.created),
        updated=str(workspace.updated),
    )


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace_endpoint(body: CreateWorkspaceRequest, request: Request):
    """Create a new workspace. The authenticated user becomes the owner."""
    try:
        workspace = await create_workspace(
            name=body.name,
            description=body.description,
            visibility=body.visibility,
            owner_id=request.state.user_id,
            org_id=getattr(request.state, "org_id", None),
        )
        return _to_workspace_response(workspace)
    except Exception as error:
        logger.error(f"Error creating workspace: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces_endpoint(request: Request):
    """List workspaces the authenticated user has access to."""
    try:
        workspaces = await list_workspaces_for_user(request.state.user_id)
        return [_to_workspace_response(ws) for ws in workspaces]
    except Exception as error:
        logger.error(f"Error listing workspaces: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workspaces/discover", response_model=List[WorkspaceResponse])
async def discover_workspaces_endpoint(request: Request):
    """Discover community workspaces in the authenticated user's org."""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        return []

    try:
        results = await discover_community_workspaces(org_id)
        return [
            WorkspaceResponse(
                id=str(row.get("id", "")),
                name=row.get("name", ""),
                description=row.get("description"),
                visibility=row.get("visibility", "community"),
                owner_id=row.get("owner_id", ""),
                org_id=row.get("org_id"),
                created=str(row.get("created", "")),
                updated=str(row.get("updated", "")),
            )
            for row in results
        ]
    except Exception as error:
        logger.error(f"Error discovering workspaces: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_endpoint(workspace_id: str, request: Request):
    """Get a workspace. Requires at least viewer role."""
    await require_viewer(workspace_id, request)

    try:
        workspace = await get_workspace(workspace_id)
        return _to_workspace_response(workspace)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error fetching workspace {workspace_id}: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace_endpoint(
    workspace_id: str, body: UpdateWorkspaceRequest, request: Request
):
    """Update a workspace. Requires owner role."""
    await require_owner(workspace_id, request)

    try:
        workspace = await update_workspace(
            workspace_id=workspace_id,
            name=body.name,
            description=body.description,
            visibility=body.visibility,
        )
        return _to_workspace_response(workspace)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error updating workspace {workspace_id}: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceDeleteResponse)
async def delete_workspace_endpoint(
    workspace_id: str,
    request: Request,
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
):
    """Delete a workspace with cascade. Requires owner role and confirm=true."""
    await require_owner(workspace_id, request)

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Deletion requires confirm=true query parameter",
        )

    try:
        await delete_workspace(workspace_id)
        return WorkspaceDeleteResponse(message="Workspace deleted successfully")
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error deleting workspace {workspace_id}: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=201,
)
async def invite_member_endpoint(
    workspace_id: str, body: InviteMemberRequest, request: Request
):
    """Invite a user to a workspace. Requires owner role."""
    await require_owner(workspace_id, request)

    try:
        member = await invite_member(
            workspace_id=workspace_id,
            user_id=body.user_id,
            role=body.role,
        )
        return WorkspaceMemberResponse(
            id=str(member.id),
            workspace_id=str(member.workspace_id),
            user_id=member.user_id,
            role=member.role,
            created=str(member.created),
            updated=str(member.updated),
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    except Exception as error:
        logger.error(f"Error inviting member to {workspace_id}: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_member_endpoint(workspace_id: str, user_id: str, request: Request):
    """Remove a member from a workspace. Requires owner role."""
    await require_owner(workspace_id, request)

    try:
        removed = await remove_member(workspace_id, user_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Member not found")
        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error removing member from {workspace_id}: {error}")
        logger.exception(error)
        raise HTTPException(status_code=500, detail="Internal server error")
