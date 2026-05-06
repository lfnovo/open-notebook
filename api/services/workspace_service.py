from __future__ import annotations

from typing import Optional

from api.auth import CurrentUser
from api.models import WorkspaceListResponse, WorkspaceResponse
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository
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
