from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.models import ChangePasswordRequest, ProfileUpdateRequest
from api.routers.auth import change_password, update_current_user


@pytest.mark.asyncio
@patch("api.routers.auth.repo_update", new_callable=AsyncMock)
@patch("api.routers.auth.verify_password")
@patch("api.routers.auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.routers.auth.validate_jwt_token", new_callable=AsyncMock)
async def test_change_password_updates_app_user_via_repo_update(
    mock_validate_token,
    mock_find_user,
    mock_verify_password,
    mock_repo_update,
):
    mock_validate_token.return_value = {"username": "admin"}
    mock_find_user.return_value = {
        "id": "app_user:admin",
        "username": "admin",
        "hashed_password": "old-hash",
    }
    mock_verify_password.return_value = True

    request = ChangePasswordRequest(old_password="admin", new_password="admin2")
    http_request = SimpleNamespace(headers={"Authorization": "Bearer test-token"})

    response = await change_password(request, http_request)

    assert response.success is True
    mock_repo_update.assert_awaited_once()
    args = mock_repo_update.await_args.args
    assert args[0] == "app_user"
    assert args[1] == "app_user:admin"
    assert args[2]["hashed_password"]


@pytest.mark.asyncio
@patch("api.routers.auth.repo_update", new_callable=AsyncMock)
@patch("api.routers.auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.routers.auth.validate_jwt_token", new_callable=AsyncMock)
async def test_update_current_user_backfills_missing_required_user_fields(
    mock_validate_token,
    mock_find_user,
    mock_repo_update,
):
    mock_validate_token.return_value = {"username": "legacy@example.com"}
    mock_find_user.return_value = {
        "id": "app_user:legacy",
        "username": "legacy@example.com",
        "display_name": "Legacy",
        "role": None,
        "status": "active",
        "locale": "zh-CN",
        "theme": "dark",
        "created": "2026-05-05T00:00:00Z",
        "updated": "2026-05-05T00:00:00Z",
    }
    mock_repo_update.return_value = [
        {
            **mock_find_user.return_value,
            "display_name": "Updated",
            "role": "user",
            "locale": None,
            "theme": None,
        }
    ]

    request = ProfileUpdateRequest(display_name="Updated", locale="", theme="")
    http_request = SimpleNamespace(headers={"Authorization": "Bearer test-token"})

    response = await update_current_user(request, http_request)

    assert response.display_name == "Updated"
    assert response.role == "user"
    assert response.locale is None
    assert response.theme is None
    args = mock_repo_update.await_args.args
    assert args[0] == "app_user"
    assert args[1] == "app_user:legacy"
    assert args[2] == {
        "role": "user",
        "display_name": "Updated",
        "locale": None,
        "theme": None,
    }
