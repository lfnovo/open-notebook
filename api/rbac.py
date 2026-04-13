"""
RBAC dependency functions for workspace-scoped endpoints.

Role hierarchy: owner > editor > viewer.
Each dependency resolves the caller's role from WorkspaceMember
records and raises HTTP 403 when access is insufficient.
"""

from fastapi import HTTPException, Request

from open_notebook.database.repository import repo_query
from open_notebook.domain.workspace import WorkspaceMember

ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2}


async def _get_user_role(workspace_id: str, user_id: str) -> str | None:
    """Return the user's role in the workspace, or None if not a member."""
    results = await repo_query(
        "SELECT role FROM workspace_member WHERE workspace_id = $workspace_id AND user_id = $user_id LIMIT 1",
        {"workspace_id": workspace_id, "user_id": user_id},
    )
    if results and len(results) > 0:
        return results[0].get("role")
    return None


async def _require_minimum_role(
    workspace_id: str, request: Request, minimum_role: str
) -> str:
    """
    Enforce that the authenticated user holds at least *minimum_role*.

    Returns the user's actual role on success.
    Raises HTTP 403 on insufficient access — never 404, to avoid
    leaking workspace existence.
    """
    user_id: str = request.state.user_id
    role = await _get_user_role(workspace_id, user_id)

    if role is None or ROLE_RANK.get(role, -1) < ROLE_RANK[minimum_role]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions for this workspace",
        )
    return role


async def require_viewer(workspace_id: str, request: Request) -> str:
    """Require at least viewer role."""
    return await _require_minimum_role(workspace_id, request, "viewer")


async def require_editor(workspace_id: str, request: Request) -> str:
    """Require at least editor role."""
    return await _require_minimum_role(workspace_id, request, "editor")


async def require_owner(workspace_id: str, request: Request) -> str:
    """Require owner role."""
    return await _require_minimum_role(workspace_id, request, "owner")
