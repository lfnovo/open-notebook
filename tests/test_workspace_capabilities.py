from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import WorkspacePermissionPolicy
from api.services.workspace_capabilities import resolve_resource_capabilities


def actor(user_id: str = "app_user:user", role: str = "user") -> CurrentUser:
    return CurrentUser(id=user_id, username=user_id.rsplit(":", 1)[-1], role=role)


@pytest.fixture(autouse=True)
def default_workspace_policy(monkeypatch):
    monkeypatch.setattr(
        "api.services.workspace_capabilities.WorkspacePolicyRepository.get_effective_policy",
        AsyncMock(return_value=WorkspacePermissionPolicy()),
    )


@pytest.mark.asyncio
async def test_system_admin_can_manage_any_workspace_resource():
    caps = await resolve_resource_capabilities(
        actor=actor("app_user:admin", "admin"),
        resource_type="notebook",
        owner_id="app_user:owner",
        workspace_id="workspace:team",
        visibility="private",
    )

    assert caps.can_read is True
    assert caps.can_update is True
    assert caps.can_delete is True
    assert caps.can_share is True
    assert caps.can_manage is True


@pytest.mark.asyncio
@patch("api.services.workspace_capabilities.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_team_manager_can_manage_team_notebook(mock_role):
    mock_role.return_value = {
        "type": "team",
        "current_user_role": "owner",
    }

    caps = await resolve_resource_capabilities(
        actor=actor("app_user:manager"),
        resource_type="notebook",
        owner_id="app_user:creator",
        workspace_id="workspace:team",
        visibility="private",
    )

    assert caps.can_read is True
    assert caps.can_update is True
    assert caps.can_delete is True
    assert caps.can_create_source is True
    assert caps.can_remove_source is True
    assert caps.can_create_note is True


@pytest.mark.asyncio
@patch("api.services.workspace_capabilities.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_team_member_can_contribute_but_not_delete_team_notebook(mock_role):
    mock_role.return_value = {
        "type": "team",
        "current_user_role": "member",
    }

    caps = await resolve_resource_capabilities(
        actor=actor("app_user:member"),
        resource_type="notebook",
        owner_id="app_user:creator",
        workspace_id="workspace:team",
        visibility="private",
    )

    assert caps.can_read is True
    assert caps.can_update is False
    assert caps.can_delete is False
    assert caps.can_share is False
    assert caps.can_create_source is True
    assert caps.can_remove_source is False
    assert caps.can_create_note is True


@pytest.mark.asyncio
@patch("api.services.workspace_capabilities.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_team_member_can_update_own_source_but_not_delete_it(mock_role):
    mock_role.return_value = {
        "type": "team",
        "current_user_role": "member",
    }

    caps = await resolve_resource_capabilities(
        actor=actor("app_user:member"),
        resource_type="source",
        owner_id="app_user:member",
        workspace_id="workspace:team",
        visibility="private",
    )

    assert caps.can_read is True
    assert caps.can_update is True
    assert caps.can_process is True
    assert caps.can_delete is False
    assert caps.can_share is False


@pytest.mark.asyncio
@patch("api.services.workspace_capabilities.WorkspacePolicyRepository.get_effective_policy", new_callable=AsyncMock)
@patch("api.services.workspace_capabilities.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_team_member_capabilities_are_clamped_by_workspace_policy(
    mock_role,
    mock_policy,
):
    mock_role.return_value = {
        "type": "team",
        "current_user_role": "member",
    }
    mock_policy.return_value = WorkspacePermissionPolicy(
        member_can_create_source=False,
        member_can_create_note=False,
        member_can_update_own_note=False,
        member_can_delete_own_note=False,
    )

    notebook_caps = await resolve_resource_capabilities(
        actor=actor("app_user:member"),
        resource_type="notebook",
        owner_id="app_user:creator",
        workspace_id="workspace:team",
        visibility="private",
    )
    note_caps = await resolve_resource_capabilities(
        actor=actor("app_user:member"),
        resource_type="note",
        owner_id="app_user:member",
        workspace_id="workspace:team",
        visibility="private",
    )

    assert notebook_caps.can_read is True
    assert notebook_caps.can_create_source is False
    assert notebook_caps.can_create_note is False
    assert note_caps.can_update is False
    assert note_caps.can_delete is False


@pytest.mark.asyncio
@patch("api.services.workspace_capabilities.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_personal_workspace_owner_can_manage_own_resource(mock_role):
    mock_role.return_value = {
        "type": "personal",
        "current_user_role": "owner",
    }

    caps = await resolve_resource_capabilities(
        actor=actor("app_user:owner"),
        resource_type="source",
        owner_id="app_user:owner",
        workspace_id="workspace:personal",
        visibility="private",
    )

    assert caps.can_read is True
    assert caps.can_update is True
    assert caps.can_process is True
    assert caps.can_delete is True
    assert caps.can_share is True


@pytest.mark.asyncio
async def test_anonymous_user_can_only_read_public_resources():
    public_caps = await resolve_resource_capabilities(
        actor=None,
        resource_type="source",
        owner_id="app_user:owner",
        workspace_id="workspace:personal",
        visibility="public",
    )
    private_caps = await resolve_resource_capabilities(
        actor=None,
        resource_type="source",
        owner_id="app_user:owner",
        workspace_id="workspace:personal",
        visibility="private",
    )

    assert public_caps.can_read is True
    assert public_caps.can_update is False
    assert private_caps.can_read is False
