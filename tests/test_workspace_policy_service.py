from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import WorkspacePermissionPolicy
from api.services import workspace_policy_service
from open_notebook.exceptions import NotFoundError


def actor(name: str = "user") -> CurrentUser:
    return CurrentUser(id=f"app_user:{name}", username=name, role="user")


def admin() -> CurrentUser:
    return CurrentUser(id="app_user:admin", username="admin", role="admin")


@pytest.mark.asyncio
@patch("api.services.workspace_policy_service.get_effective_workspace_policy", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspacePolicyRepository.get_workspace_policy", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspaceRepository.user_can_access", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_get_workspace_policy_requires_workspace_access(
    mock_get_workspace,
    mock_can_access,
    mock_policy,
    mock_effective_policy,
):
    mock_get_workspace.return_value = {"id": "workspace:team", "type": "team"}
    mock_can_access.return_value = True
    mock_policy.return_value = None
    mock_effective_policy.return_value = WorkspacePermissionPolicy()

    response = await workspace_policy_service.get_workspace_policy_use_case(
        "workspace:team",
        actor=actor("member"),
    )

    assert response.workspace_id == "workspace:team"
    assert response.policy.member_can_create_source is True
    mock_can_access.assert_awaited_once_with(
        workspace_id="workspace:team",
        user_id="app_user:member",
        include_all_for_admin=False,
    )


@pytest.mark.asyncio
@patch("api.services.workspace_policy_service.get_effective_workspace_policy", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspacePolicyRepository.upsert_workspace_policy", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_update_workspace_policy_requires_workspace_manager(
    mock_get_workspace,
    mock_role,
    mock_upsert,
    mock_audit,
    mock_effective_policy,
):
    mock_get_workspace.return_value = {"id": "workspace:team", "type": "team"}
    mock_role.return_value = {"current_user_role": "owner"}
    mock_upsert.return_value = {"member_can_create_note": False}
    mock_effective_policy.return_value = WorkspacePermissionPolicy(
        member_can_create_note=False
    )

    response = await workspace_policy_service.update_workspace_policy_use_case(
        "workspace:team",
        WorkspacePermissionPolicy(member_can_create_note=False),
        actor=actor("owner"),
    )

    assert response.policy.member_can_create_note is False
    mock_upsert.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.services.workspace_policy_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_workspace_policy_raises_not_found(mock_get_workspace):
    mock_get_workspace.return_value = None

    with pytest.raises(NotFoundError):
        await workspace_policy_service.get_workspace_policy_use_case(
            "workspace:missing",
            actor=actor("member"),
        )


@pytest.mark.asyncio
@patch("api.services.workspace_policy_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.workspace_policy_service.WorkspacePolicyRepository.upsert_system_policy", new_callable=AsyncMock)
async def test_update_system_policy_requires_system_admin(mock_upsert, mock_audit):
    mock_upsert.return_value = {"member_can_delete_own_note": False}

    response = await workspace_policy_service.update_system_policy_use_case(
        WorkspacePermissionPolicy(member_can_delete_own_note=False),
        actor=admin(),
    )

    assert response.policy.member_can_delete_own_note is False
    mock_upsert.assert_awaited_once()
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_system_policy_rejects_regular_user():
    with pytest.raises(PermissionError):
        await workspace_policy_service.update_system_policy_use_case(
            WorkspacePermissionPolicy(member_can_create_note=False),
            actor=actor("member"),
        )
