from __future__ import annotations

from typing import Literal

from api.auth import CurrentUser
from api.models import ResourceCapabilities, WorkspacePermissionPolicy
from open_notebook.database.repositories.workspace_policy_repository import (
    WorkspacePolicyRepository,
)
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository

ResourceType = Literal["notebook", "source", "note", "chat_session"]

MANAGER_ROLES = {"owner", "admin"}
MEMBER_ROLES = {"owner", "admin", "member", "viewer"}


def _same_user(left: str | None, right: str | None) -> bool:
    return bool(left and right and str(left) == str(right))


def _policy_flag(policy: WorkspacePermissionPolicy | dict, field: str) -> bool:
    if isinstance(policy, WorkspacePermissionPolicy):
        return bool(getattr(policy, field))
    return bool(policy.get(field))


async def resolve_resource_capabilities(
    *,
    actor: CurrentUser | None,
    resource_type: ResourceType,
    owner_id: str | None,
    workspace_id: str | None,
    visibility: str = "private",
) -> ResourceCapabilities:
    """Resolve effective resource actions for the current actor.

    This is the first workspace-aware permission boundary. It intentionally uses
    conservative defaults for team workspaces: members can contribute, but
    destructive lifecycle operations stay with workspace managers and system admins.
    """
    if actor is None:
        return ResourceCapabilities(can_read=visibility == "public")

    if actor.role == "admin":
        return ResourceCapabilities(
            can_read=True,
            can_update=True,
            can_delete=True,
            can_share=True,
            can_manage=True,
            can_create_source=True,
            can_remove_source=True,
            can_create_note=True,
            can_process=True,
        )

    is_creator = _same_user(owner_id, actor.id)
    workspace_type: str | None = None
    workspace_role: str | None = None

    if workspace_id:
        role_row = await WorkspaceRepository.current_user_role(
            workspace_id=workspace_id,
            user_id=actor.id,
        )
        if role_row:
            workspace_type = role_row.get("type")
            workspace_role = role_row.get("current_user_role")

    is_workspace_manager = workspace_role in MANAGER_ROLES
    is_workspace_member = workspace_role in MEMBER_ROLES
    is_personal_workspace = workspace_type == "personal" or not workspace_id
    can_read = visibility == "public" or is_creator or is_workspace_member
    policy: WorkspacePermissionPolicy | dict | None = None
    if workspace_id and workspace_type == "team" and is_workspace_member:
        policy = await WorkspacePolicyRepository.get_effective_policy(workspace_id)

    if resource_type == "notebook":
        if is_personal_workspace:
            can_manage = is_creator or is_workspace_manager
            return ResourceCapabilities(
                can_read=can_read,
                can_update=can_manage,
                can_delete=can_manage,
                can_share=can_manage,
                can_manage=can_manage,
                can_create_source=can_manage,
                can_remove_source=can_manage,
                can_create_note=can_manage,
            )

        return ResourceCapabilities(
            can_read=can_read and (
                is_workspace_manager
                or not policy
                or _policy_flag(policy, "member_can_read")
            ),
            can_update=is_workspace_manager
            or (
                is_workspace_member
                and bool(policy)
                and _policy_flag(policy, "member_can_update_notebook")
                and is_creator
            ),
            can_delete=is_workspace_manager,
            can_share=is_workspace_manager,
            can_manage=is_workspace_manager,
            can_create_source=is_workspace_member
            and (not policy or _policy_flag(policy, "member_can_create_source")),
            can_remove_source=is_workspace_manager
            or (
                is_workspace_member
                and bool(policy)
                and _policy_flag(policy, "member_can_remove_source")
            ),
            can_create_note=is_workspace_member
            and (not policy or _policy_flag(policy, "member_can_create_note")),
        )

    if resource_type == "source":
        if is_personal_workspace:
            can_manage = is_creator or is_workspace_manager
            return ResourceCapabilities(
                can_read=can_read,
                can_update=can_manage,
                can_delete=can_manage,
                can_share=can_manage,
                can_manage=can_manage,
                can_process=can_manage,
            )

        can_update = is_workspace_manager or (
            is_workspace_member
            and is_creator
            and (not policy or _policy_flag(policy, "member_can_update_own_source"))
        )
        return ResourceCapabilities(
            can_read=can_read and (
                is_workspace_manager
                or not policy
                or _policy_flag(policy, "member_can_read")
            ),
            can_update=can_update,
            can_delete=is_workspace_manager
            or (
                is_workspace_member
                and is_creator
                and bool(policy)
                and _policy_flag(policy, "member_can_delete_own_source")
            ),
            can_share=is_workspace_manager,
            can_manage=is_workspace_manager,
            can_process=is_workspace_manager
            or (
                is_workspace_member
                and is_creator
                and (not policy or _policy_flag(policy, "member_can_process_own_source"))
            ),
        )

    can_manage = is_workspace_manager or (is_personal_workspace and is_creator)
    can_update_own_note = (
        is_workspace_member
        and is_creator
        and (not policy or _policy_flag(policy, "member_can_update_own_note"))
    )
    can_delete_own_note = (
        is_workspace_member
        and is_creator
        and (not policy or _policy_flag(policy, "member_can_delete_own_note"))
    )
    if resource_type == "chat_session":
        can_update_own_note = False
        can_delete_own_note = (
            is_workspace_member
            and is_creator
            and bool(policy)
            and _policy_flag(policy, "member_can_delete_chat")
        )
    return ResourceCapabilities(
        can_read=can_read and (
            can_manage or not policy or _policy_flag(policy, "member_can_read")
        ),
        can_update=can_manage or can_update_own_note,
        can_delete=can_manage or can_delete_own_note,
        can_share=can_manage,
        can_manage=can_manage,
    )
