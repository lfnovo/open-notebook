from __future__ import annotations

from typing import Optional

from api.auth import CurrentUser
from api.models import (
    WorkspaceListResponse,
    WorkspaceResourceMoveRequest,
    WorkspaceResourceMoveResponse,
    WorkspaceResponse,
)
from api.services.workspace_capabilities import resolve_resource_capabilities
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import InvalidInputError, NotFoundError


def _workspace_response(row: dict) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=str(row.get("id", "")),
        name=row.get("name", ""),
        type=row.get("type", "personal"),
        owner_id=str(row.get("owner_id")) if row.get("owner_id") else None,
        team_id=str(row.get("team_id")) if row.get("team_id") else None,
        created_by=str(row.get("created_by")) if row.get("created_by") else None,
        created=str(row.get("created", "")),
        updated=str(row.get("updated", "")),
        current_user_role=row.get("current_user_role"),
        can_manage=bool(row.get("can_manage", False)),
    )


async def ensure_personal_workspace_for_user(
    *,
    user_id: str,
    display_name: Optional[str] = None,
) -> dict:
    row = await WorkspaceRepository.ensure_personal_workspace(
        user_id=user_id,
        display_name=display_name,
    )
    if not row:
        raise InvalidInputError("Failed to create personal workspace")
    return row


async def ensure_team_workspace_for_team(
    *,
    team_id: str,
    name: str,
    created_by: Optional[str] = None,
) -> dict:
    row = await WorkspaceRepository.ensure_team_workspace(
        team_id=team_id,
        name=name,
        created_by=created_by,
    )
    if not row:
        raise InvalidInputError("Failed to create team workspace")
    return row


async def resolve_workspace_id_for_user(
    *,
    user_id: str | None,
    requested_workspace_id: str | None,
) -> str | None:
    if requested_workspace_id:
        return requested_workspace_id
    if not user_id:
        return None
    row = await ensure_personal_workspace_for_user(user_id=user_id)
    return str(row.get("id")) if row.get("id") else None


async def list_workspaces_use_case(*, actor: CurrentUser) -> WorkspaceListResponse:
    rows = await WorkspaceRepository.list_for_user(
        user_id=actor.id,
        include_all_for_admin=actor.role == "admin",
    )
    return WorkspaceListResponse(
        items=[_workspace_response(row) for row in rows],
        total=len(rows),
    )


async def get_workspace_use_case(
    workspace_id: str,
    *,
    actor: CurrentUser,
) -> WorkspaceResponse:
    row = await WorkspaceRepository.get_workspace(workspace_id)
    if not row:
        raise NotFoundError("Workspace not found")

    can_access = await WorkspaceRepository.user_can_access(
        workspace_id=workspace_id,
        user_id=actor.id,
        include_all_for_admin=actor.role == "admin",
    )
    if not can_access:
        raise PermissionError("Workspace access denied")

    if "current_user_role" not in row:
        row = {
            **row,
            "current_user_role": "owner" if row.get("owner_id") and str(row.get("owner_id")) == actor.id else None,
            "can_manage": actor.role == "admin"
            or (row.get("owner_id") and str(row.get("owner_id")) == actor.id),
        }
    return _workspace_response(row)


async def _actor_can_manage_workspace(
    *,
    workspace_id: str,
    actor: CurrentUser,
) -> bool:
    if actor.role == "admin":
        return True
    role = await WorkspaceRepository.current_user_role(
        workspace_id=workspace_id,
        user_id=actor.id,
    )
    return bool(role and role.get("current_user_role") in {"owner", "admin"})


async def move_resource_to_workspace_use_case(
    workspace_id: str,
    request: WorkspaceResourceMoveRequest,
    *,
    actor: CurrentUser,
) -> WorkspaceResourceMoveResponse:
    target_workspace = await WorkspaceRepository.get_workspace(workspace_id)
    if not target_workspace:
        raise NotFoundError("Workspace not found")
    if not await _actor_can_manage_workspace(workspace_id=workspace_id, actor=actor):
        raise PermissionError("Workspace management permission required")

    if request.resource_type != "notebook" or request.mode != "move":
        raise InvalidInputError("Only notebook move is supported")

    notebook = await Notebook.get(request.resource_id)
    if not notebook:
        raise NotFoundError("Notebook not found")

    source_workspace_id = str(notebook.workspace_id) if notebook.workspace_id else None
    capabilities = await resolve_resource_capabilities(
        actor=actor,
        resource_type="notebook",
        owner_id=str(notebook.owner_id) if notebook.owner_id else None,
        workspace_id=source_workspace_id,
        visibility=notebook.visibility,
    )
    if not capabilities.can_manage:
        raise PermissionError("Notebook management permission required")

    await WorkspaceRepository.move_notebook_to_workspace(
        notebook_id=request.resource_id,
        workspace_id=workspace_id,
    )
    await AuditLogRepository.create(
        action="resource.moved_to_workspace",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type=request.resource_type,
        target_id=request.resource_id,
        metadata={
            "source_workspace_id": source_workspace_id,
            "target_workspace_id": workspace_id,
            "mode": request.mode,
        },
    )

    return WorkspaceResourceMoveResponse(
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        source_workspace_id=source_workspace_id,
        target_workspace_id=workspace_id,
        mode=request.mode,
        message="Resource moved to workspace",
    )
