from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
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
