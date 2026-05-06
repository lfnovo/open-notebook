from __future__ import annotations

from api.auth import CurrentUser
from api.models import (
    WorkspacePermissionPolicy,
    WorkspacePolicyResponse,
    WorkspaceSystemPolicyResponse,
)
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.workspace_policy_repository import (
    POLICY_FIELDS,
    WorkspacePolicyRepository,
)
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository
from open_notebook.exceptions import NotFoundError

MANAGER_ROLES = {"owner", "admin"}


def default_workspace_policy() -> WorkspacePermissionPolicy:
    return WorkspacePermissionPolicy()


def _policy_from_row(row: dict | None) -> WorkspacePermissionPolicy:
    if not row:
        return default_workspace_policy()
    return WorkspacePermissionPolicy(
        **{field: row.get(field, getattr(default_workspace_policy(), field)) for field in POLICY_FIELDS}
    )


def _policy_dict(policy: WorkspacePermissionPolicy) -> dict[str, bool]:
    return {field: bool(getattr(policy, field)) for field in POLICY_FIELDS}


async def get_system_policy_use_case() -> WorkspaceSystemPolicyResponse:
    return WorkspaceSystemPolicyResponse(
        policy=_policy_from_row(await WorkspacePolicyRepository.get_system_policy())
    )


async def get_effective_workspace_policy(
    workspace_id: str,
) -> WorkspacePermissionPolicy:
    workspace_policy = _policy_from_row(
        await WorkspacePolicyRepository.get_workspace_policy(workspace_id)
    )
    system_policy = _policy_from_row(await WorkspacePolicyRepository.get_system_policy())
    return WorkspacePermissionPolicy(
        **{
            field: getattr(workspace_policy, field) and getattr(system_policy, field)
            for field in POLICY_FIELDS
        }
    )


async def _ensure_workspace_exists(workspace_id: str) -> dict:
    workspace = await WorkspaceRepository.get_workspace(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")
    return workspace


async def _ensure_workspace_manager(workspace_id: str, actor: CurrentUser) -> None:
    if actor.role == "admin":
        return
    role = await WorkspaceRepository.current_user_role(
        workspace_id=workspace_id,
        user_id=actor.id,
    )
    if not role or role.get("current_user_role") not in MANAGER_ROLES:
        raise PermissionError("Workspace management permission required")


async def get_workspace_policy_use_case(
    workspace_id: str,
    *,
    actor: CurrentUser,
) -> WorkspacePolicyResponse:
    await _ensure_workspace_exists(workspace_id)
    can_access = await WorkspaceRepository.user_can_access(
        workspace_id=workspace_id,
        user_id=actor.id,
        include_all_for_admin=actor.role == "admin",
    )
    if not can_access:
        raise PermissionError("Workspace access denied")

    policy = _policy_from_row(
        await WorkspacePolicyRepository.get_workspace_policy(workspace_id)
    )
    effective_policy = await get_effective_workspace_policy(workspace_id)
    return WorkspacePolicyResponse(
        workspace_id=workspace_id,
        policy=policy,
        effective_policy=effective_policy,
    )


async def update_workspace_policy_use_case(
    workspace_id: str,
    policy: WorkspacePermissionPolicy,
    *,
    actor: CurrentUser,
) -> WorkspacePolicyResponse:
    await _ensure_workspace_exists(workspace_id)
    await _ensure_workspace_manager(workspace_id, actor)
    row = await WorkspacePolicyRepository.upsert_workspace_policy(
        workspace_id=workspace_id,
        policy=_policy_dict(policy),
    )
    await AuditLogRepository.create(
        action="workspace.policy.updated",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="workspace",
        target_id=workspace_id,
        metadata={"policy": _policy_dict(policy)},
    )
    return WorkspacePolicyResponse(
        workspace_id=workspace_id,
        policy=_policy_from_row(row),
        effective_policy=await get_effective_workspace_policy(workspace_id),
    )


async def update_system_policy_use_case(
    policy: WorkspacePermissionPolicy,
    *,
    actor: CurrentUser,
) -> WorkspaceSystemPolicyResponse:
    if actor.role != "admin":
        raise PermissionError("Admin privileges required")
    row = await WorkspacePolicyRepository.upsert_system_policy(_policy_dict(policy))
    await AuditLogRepository.create(
        action="workspace.system_policy.updated",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="workspace_system_policy",
        target_id="workspace_system_policy:global",
        metadata={"policy": _policy_dict(policy)},
    )
    return WorkspaceSystemPolicyResponse(policy=_policy_from_row(row))
