from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.auth import CurrentUser, get_current_user
from api.models import (
    WorkspaceListResponse,
    WorkspacePermissionPolicy,
    WorkspacePolicyResponse,
    WorkspaceResourceMoveRequest,
    WorkspaceResourceMoveResponse,
    WorkspaceResponse,
    WorkspaceSystemPolicyResponse,
)
from api.services.workspace_policy_service import (
    get_system_policy_use_case,
    get_workspace_policy_use_case,
    update_system_policy_use_case,
    update_workspace_policy_use_case,
)
from api.services.workspace_service import (
    get_workspace_use_case,
    list_workspaces_use_case,
    move_resource_to_workspace_use_case,
)
from open_notebook.exceptions import InvalidInputError, NotFoundError

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(actor: CurrentUser = Depends(get_current_user)):
    return await list_workspaces_use_case(actor=actor)


@router.get("/system-policy", response_model=WorkspaceSystemPolicyResponse)
async def get_system_policy(actor: CurrentUser = Depends(get_current_user)):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return await get_system_policy_use_case()


@router.patch("/system-policy", response_model=WorkspaceSystemPolicyResponse)
async def update_system_policy(
    request: WorkspacePermissionPolicy,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await update_system_policy_use_case(request, actor=actor)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await get_workspace_use_case(workspace_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{workspace_id}/policy", response_model=WorkspacePolicyResponse)
async def get_workspace_policy(
    workspace_id: str,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await get_workspace_policy_use_case(workspace_id, actor=actor)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.patch("/{workspace_id}/policy", response_model=WorkspacePolicyResponse)
async def update_workspace_policy(
    workspace_id: str,
    request: WorkspacePermissionPolicy,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await update_workspace_policy_use_case(
            workspace_id,
            request,
            actor=actor,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{workspace_id}/resources/move", response_model=WorkspaceResourceMoveResponse)
async def move_resource_to_workspace(
    workspace_id: str,
    request: WorkspaceResourceMoveRequest,
    actor: CurrentUser = Depends(get_current_user),
):
    try:
        return await move_resource_to_workspace_use_case(
            workspace_id,
            request,
            actor=actor,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
