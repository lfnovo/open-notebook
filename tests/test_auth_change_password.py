from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.models import (
    ChangePasswordRequest,
    CompleteProfileRequest,
    ProfileUpdateRequest,
)
from api.routers.auth import (
    change_password,
    complete_current_user_profile,
    update_current_user,
)


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


@pytest.mark.asyncio
@patch("api.routers.auth.create_jwt_token")
@patch("api.routers.auth.verify_code", new_callable=AsyncMock)
@patch("api.routers.auth.UserRepository.delete_user", new_callable=AsyncMock)
@patch("api.routers.auth.UserRepository.update_user", new_callable=AsyncMock)
@patch("api.routers.auth.UserRepository.get_user_by_email", new_callable=AsyncMock)
@patch("api.routers.auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.routers.auth.validate_jwt_token", new_callable=AsyncMock)
async def test_complete_profile_binds_wechat_identity_to_existing_email_user(
    mock_validate_token,
    mock_find_user,
    mock_get_by_email,
    mock_update_user,
    mock_delete_user,
    mock_verify_code,
    mock_create_token,
):
    current_user = {
        "id": "app_user:wx_openid",
        "username": "wx_openid",
        "email": None,
        "display_name": "WeChat User",
        "avatar_url": "https://example.com/wx.jpg",
        "login_provider": "wechat",
        "wechat_openid": "openid-1",
        "wechat_unionid": "unionid-1",
        "role": "user",
        "status": "active",
        "created": "2026-05-05T00:00:00Z",
        "updated": "2026-05-05T00:00:00Z",
    }
    existing_user = {
        "id": "app_user:email_user",
        "username": "user@example.com",
        "email": "user@example.com",
        "display_name": "Email User",
        "role": "user",
        "status": "active",
        "created": "2026-05-01T00:00:00Z",
        "updated": "2026-05-01T00:00:00Z",
    }
    bound_user = {
        **existing_user,
        "avatar_url": "https://example.com/wx.jpg",
        "login_provider": "wechat",
        "wechat_openid": "openid-1",
        "wechat_unionid": "unionid-1",
    }
    mock_validate_token.return_value = {"username": "wx_openid"}
    mock_find_user.return_value = current_user
    mock_verify_code.return_value = (True, "Code verified")
    mock_get_by_email.return_value = existing_user
    mock_update_user.return_value = [bound_user]
    mock_create_token.return_value = "existing-user-token"

    request = CompleteProfileRequest(
        email="USER@example.com",
        verification_code="123456",
    )
    http_request = SimpleNamespace(headers={"Authorization": "Bearer test-token"})

    response = await complete_current_user_profile(request, http_request)

    assert response.success is True
    assert response.bound_existing_user is True
    assert response.token == "existing-user-token"
    assert response.user.username == "user@example.com"
    assert response.user.email == "user@example.com"
    mock_verify_code.assert_awaited_once_with(
        "user@example.com",
        "123456",
        "profile_email",
    )
    mock_update_user.assert_awaited_once()
    assert mock_update_user.await_args.args[0] == "app_user:email_user"
    assert mock_update_user.await_args.args[1]["wechat_openid"] == "openid-1"
    assert mock_update_user.await_args.args[1]["wechat_unionid"] == "unionid-1"
    mock_delete_user.assert_awaited_once_with("app_user:wx_openid")
    mock_create_token.assert_called_once_with(
        "user@example.com",
        "app_user:email_user",
        bound_user,
    )


@pytest.mark.asyncio
@patch("api.routers.auth.create_jwt_token")
@patch("api.routers.auth.verify_code", new_callable=AsyncMock)
@patch("api.routers.auth.UserRepository.update_user", new_callable=AsyncMock)
@patch("api.routers.auth.UserRepository.get_user_by_email", new_callable=AsyncMock)
@patch("api.routers.auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.routers.auth.validate_jwt_token", new_callable=AsyncMock)
async def test_complete_profile_sets_email_for_new_wechat_user(
    mock_validate_token,
    mock_find_user,
    mock_get_by_email,
    mock_update_user,
    mock_verify_code,
    mock_create_token,
):
    current_user = {
        "id": "app_user:wx_openid",
        "username": "wx_openid",
        "email": None,
        "display_name": "WeChat User",
        "login_provider": "wechat",
        "wechat_openid": "openid-1",
        "wechat_unionid": None,
        "role": "user",
        "status": "active",
        "created": "2026-05-05T00:00:00Z",
        "updated": "2026-05-05T00:00:00Z",
    }
    completed_user = {
        **current_user,
        "email": "new@example.com",
    }
    mock_validate_token.return_value = {"username": "wx_openid"}
    mock_find_user.return_value = current_user
    mock_verify_code.return_value = (True, "Code verified")
    mock_get_by_email.return_value = None
    mock_update_user.return_value = [completed_user]
    mock_create_token.return_value = "wechat-user-token"

    request = CompleteProfileRequest(
        email="new@example.com",
        verification_code="654321",
    )
    http_request = SimpleNamespace(headers={"Authorization": "Bearer test-token"})

    response = await complete_current_user_profile(request, http_request)

    assert response.success is True
    assert response.bound_existing_user is False
    assert response.token == "wechat-user-token"
    assert response.user.username == "wx_openid"
    assert response.user.email == "new@example.com"
    mock_update_user.assert_awaited_once_with(
        "app_user:wx_openid",
        {"email": "new@example.com"},
    )
