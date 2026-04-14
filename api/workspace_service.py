"""
Business logic for workspace operations.

Handles create, update, delete, list, invite, remove member, and discover.
All authorization checks happen in the RBAC layer before these functions
are called — service functions assume the caller is authorized.
"""

from typing import List, Optional

from loguru import logger

from open_notebook.database.repository import repo_query
from open_notebook.domain.workspace import Workspace, WorkspaceMember


async def create_workspace(
    name: str,
    visibility: str,
    owner_id: str,
    org_id: Optional[str] = None,
    description: Optional[str] = None,
) -> Workspace:
    """Create a workspace and auto-add the creator as owner."""
    workspace = Workspace(
        name=name,
        description=description,
        visibility=visibility,
        owner_id=owner_id,
        org_id=org_id,
    )
    await workspace.save()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=owner_id,
        role="owner",
    )
    try:
        await member.save()
    except Exception:
        await workspace.delete()
        raise

    logger.info(f"Workspace {workspace.id} created by {owner_id}")
    return workspace


async def list_workspaces_for_user(user_id: str) -> List[Workspace]:
    """Return all workspaces the user is a member of."""
    memberships = await WorkspaceMember.get_for_user(user_id)
    workspaces = []
    for membership in memberships:
        try:
            workspace = await Workspace.get(membership.workspace_id)
            workspaces.append(workspace)
        except Exception as error:
            logger.warning(
                f"Could not load workspace {membership.workspace_id}: {error}"
            )
    return workspaces


async def get_workspace(workspace_id: str) -> Workspace:
    """Return a single workspace by ID."""
    return await Workspace.get(workspace_id)


async def update_workspace(
    workspace_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    visibility: Optional[str] = None,
) -> Workspace:
    """Update workspace fields. Only provided values are changed."""
    workspace = await Workspace.get(workspace_id)

    if name is not None:
        workspace.name = name
    if description is not None:
        workspace.description = description
    if visibility is not None:
        workspace.visibility = visibility

    await workspace.save()
    return workspace


async def delete_workspace(workspace_id: str) -> bool:
    """Delete a workspace with cascade deletion."""
    workspace = await Workspace.get(workspace_id)
    return await workspace.delete()


async def invite_member(
    workspace_id: str,
    user_id: str,
    role: str,
) -> WorkspaceMember:
    """
    Add a user to a workspace with the given role.

    Raises if the user is already a member.
    """
    existing = await WorkspaceMember.get_for_workspace(workspace_id)
    for member in existing:
        if member.user_id == user_id:
            raise ValueError(f"User {user_id} is already a member of this workspace")

    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )
    await member.save()

    logger.info(f"User {user_id} invited to {workspace_id} as {role}")
    return member


async def remove_member(workspace_id: str, target_user_id: str) -> bool:
    """Remove a member from a workspace."""
    members = await WorkspaceMember.get_for_workspace(workspace_id)
    for member in members:
        if member.user_id == target_user_id:
            if member.role == "owner":
                owner_count = sum(1 for m in members if m.role == "owner")
                if owner_count <= 1:
                    raise ValueError("Cannot remove the last owner of a workspace")
            await member.delete()
            logger.info(f"User {target_user_id} removed from {workspace_id}")
            return True
    return False


async def discover_community_workspaces(org_id: str) -> List[dict]:
    """Return community-visible workspaces in the given org."""
    if not org_id:
        return []

    results = await repo_query(
        "SELECT * FROM workspace WHERE visibility = 'community' AND org_id = $org_id",
        {"org_id": org_id},
    )
    return results or []
