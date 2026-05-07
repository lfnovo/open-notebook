from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import ResourceCapabilities, WorkspaceResourceMoveRequest
from api.services import workspace_service
from open_notebook.exceptions import NotFoundError


def actor(role: str = "user") -> CurrentUser:
    return CurrentUser(id=f"app_user:{role}", username=role, role=role)


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.list_for_user", new_callable=AsyncMock)
async def test_list_workspaces_returns_workspace_responses(mock_list):
    mock_list.return_value = [
        {
            "id": "workspace:personal",
            "name": "Alice",
            "type": "personal",
            "owner_id": "app_user:user",
            "team_id": None,
            "created_by": "app_user:user",
            "created": "2026-05-06T00:00:00Z",
            "updated": "2026-05-06T00:00:00Z",
            "current_user_role": "owner",
            "can_manage": True,
        }
    ]

    response = await workspace_service.list_workspaces_use_case(actor=actor("user"))

    assert response.total == 1
    assert response.items[0].id == "workspace:personal"
    assert response.items[0].type == "personal"
    assert response.items[0].current_user_role == "owner"
    mock_list.assert_awaited_once_with(
        user_id="app_user:user",
        include_all_for_admin=False,
    )


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.user_can_access", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_get_workspace_rejects_inaccessible_workspace(mock_get, mock_can_access):
    mock_get.return_value = {"id": "workspace:team", "name": "Team", "type": "team"}
    mock_can_access.return_value = False

    with pytest.raises(PermissionError):
        await workspace_service.get_workspace_use_case(
            "workspace:team",
            actor=actor("user"),
        )


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_get_workspace_raises_not_found(mock_get):
    mock_get.return_value = None

    with pytest.raises(NotFoundError):
        await workspace_service.get_workspace_use_case(
            "workspace:missing",
            actor=actor("user"),
        )


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_resolve_workspace_id_rejects_requested_workspace_without_membership(
    mock_current_role,
):
    mock_current_role.return_value = {
        "type": "team",
        "current_user_role": None,
    }

    with pytest.raises(PermissionError, match="Workspace access denied"):
        await workspace_service.resolve_workspace_id_for_user(
            user_id="app_user:admin",
            requested_workspace_id="workspace:observed",
        )


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_resolve_workspace_id_allows_requested_workspace_for_active_member(
    mock_current_role,
):
    mock_current_role.return_value = {
        "type": "team",
        "current_user_role": "member",
    }

    workspace_id = await workspace_service.resolve_workspace_id_for_user(
        user_id="app_user:member",
        requested_workspace_id="workspace:team",
    )

    assert workspace_id == "workspace:team"


@pytest.mark.asyncio
@patch("api.services.workspace_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.move_notebook_to_workspace", new_callable=AsyncMock)
@patch("api.services.workspace_service.resolve_resource_capabilities", new_callable=AsyncMock)
@patch("api.services.workspace_service.Notebook")
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_move_notebook_to_workspace_requires_target_manager_and_moves_children(
    mock_get_workspace,
    mock_current_role,
    mock_notebook_cls,
    mock_capabilities,
    mock_move,
    mock_audit,
):
    mock_get_workspace.return_value = {"id": "workspace:team", "type": "team"}
    mock_current_role.return_value = {"current_user_role": "owner"}
    mock_notebook = type(
        "NotebookStub",
        (),
        {
            "owner_id": "app_user:user",
            "workspace_id": "workspace:personal",
            "visibility": "private",
        },
    )()
    mock_notebook_cls.get = AsyncMock(return_value=mock_notebook)
    mock_capabilities.return_value = ResourceCapabilities(can_manage=True)

    response = await workspace_service.move_resource_to_workspace_use_case(
        "workspace:team",
        WorkspaceResourceMoveRequest(
            resource_type="notebook",
            resource_id="notebook:abc",
        ),
        actor=actor("user"),
    )

    assert response.target_workspace_id == "workspace:team"
    assert response.source_workspace_id == "workspace:personal"
    mock_move.assert_awaited_once_with(
        notebook_id="notebook:abc",
        workspace_id="workspace:team",
    )
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_move_notebook_to_workspace_requires_workspace_management(
    mock_get_workspace,
    mock_current_role,
):
    mock_get_workspace.return_value = {"id": "workspace:team", "type": "team"}
    mock_current_role.return_value = {"current_user_role": "member"}

    with pytest.raises(PermissionError, match="Workspace management permission"):
        await workspace_service.move_resource_to_workspace_use_case(
            "workspace:team",
            WorkspaceResourceMoveRequest(
                resource_type="notebook",
                resource_id="notebook:abc",
            ),
            actor=actor("user"),
        )


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.get_workspace", new_callable=AsyncMock)
async def test_system_admin_cannot_move_resources_into_observed_workspace(
    mock_get_workspace,
    mock_current_role,
):
    mock_get_workspace.return_value = {"id": "workspace:team", "type": "team"}
    mock_current_role.return_value = {"current_user_role": None}

    with pytest.raises(PermissionError, match="Workspace management permission"):
        await workspace_service.move_resource_to_workspace_use_case(
            "workspace:team",
            WorkspaceResourceMoveRequest(
                resource_type="notebook",
                resource_id="notebook:abc",
            ),
            actor=actor("admin"),
        )
