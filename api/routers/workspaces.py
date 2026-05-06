from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.auth import CurrentUser, get_current_user
from api.models import (
    WorkspaceListResponse,
    WorkspaceResourceMoveRequest,
    WorkspaceResourceMoveResponse,
    WorkspaceResponse,
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
