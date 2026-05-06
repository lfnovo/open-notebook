from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import UserCreateRequest
from api.services import user_service


def admin_actor() -> CurrentUser:
    return CurrentUser(id="app_user:admin", username="admin", role="admin")


@pytest.mark.asyncio
@patch("api.services.user_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.user_service.ensure_personal_workspace_for_user", new_callable=AsyncMock)
@patch("api.services.user_service.UserRepository.create_user", new_callable=AsyncMock)
@patch("api.services.user_service.UserRepository.get_user_by_username", new_callable=AsyncMock)
async def test_create_user_ensures_personal_workspace(
    mock_get_user_by_username,
    mock_create_user,
    mock_ensure_workspace,
    mock_audit,
):
    mock_get_user_by_username.return_value = None
    mock_create_user.return_value = {
        "id": "app_user:alice",
        "username": "alice",
        "email": "alice@example.com",
        "display_name": "Alice",
        "role": "user",
        "status": "active",
        "created": "2026-05-06T00:00:00Z",
        "updated": "2026-05-06T00:00:00Z",
    }

    response = await user_service.create_user_use_case(
        UserCreateRequest(
            username="alice",
            email="alice@example.com",
            display_name="Alice",
            password="password",
        ),
        actor=admin_actor(),
    )

    assert response.id == "app_user:alice"
    mock_ensure_workspace.assert_awaited_once_with(
        user_id="app_user:alice",
        display_name="Alice",
    )
    mock_audit.assert_awaited_once()
