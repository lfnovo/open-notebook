from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.models import LoginRequest, RegisterRequest, SendCodeRequest, SetupRequest
from api.routers.auth import auth_register, auth_send_code, login, setup_admin


@pytest.mark.asyncio
@patch("api.routers.auth.get_secret_from_env", return_value="legacy-secret")
async def test_legacy_login_returns_shared_password_token(mock_get_secret):
    request = LoginRequest(username="legacy-user", password="legacy-secret")

    response = await login(request)

    assert response.success is True
    assert response.token == "legacy-secret"


@pytest.mark.asyncio
@patch("api.routers.auth.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.routers.auth.repo_update", new_callable=AsyncMock)
@patch("api.routers.auth.create_jwt_token", return_value="jwt-token")
@patch("api.routers.auth.verify_password", return_value=True)
@patch("api.routers.auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.routers.auth.get_secret_from_env", return_value=None)
async def test_database_login_with_email_returns_canonical_username(
    mock_get_secret,
    mock_find_user,
    mock_verify_password,
    mock_create_jwt_token,
    mock_repo_update,
    mock_audit_log,
):
    user = {
        "id": "app_user:wangz",
        "username": "wangz",
        "email": "wangz@yinhour.com",
        "hashed_password": "hashed",
        "status": "active",
    }
    mock_find_user.return_value = user

    response = await login(LoginRequest(username="wangz@yinhour.com", password="Welcome1"))

    assert response.success is True
    assert response.token == "jwt-token"
    assert response.username == "wangz"
    mock_find_user.assert_awaited_once_with("wangz@yinhour.com")
    mock_create_jwt_token.assert_called_once_with("wangz", "app_user:wangz", user)


@pytest.mark.asyncio
@patch("api.routers.auth.ALLOW_PUBLIC_REGISTRATION", False)
async def test_register_rejects_when_public_registration_disabled():
    request = RegisterRequest(
        email="user@example.com",
        code="123456",
        password="ResetPass123!",
    )

    response = await auth_register(request)

    assert response.success is False
    assert response.message == "Public registration is disabled"


@pytest.mark.asyncio
@patch("api.routers.auth._get_db_users", new_callable=AsyncMock, return_value=[])
@patch("api.routers.auth.get_secret_from_env", return_value="legacy-secret")
async def test_setup_requires_legacy_password_when_legacy_mode_enabled(
    mock_get_secret,
    mock_get_users,
):
    request = SetupRequest(username="admin", password="admin123")
    http_request = SimpleNamespace(headers={})

    with pytest.raises(HTTPException) as exc_info:
        await setup_admin(request, http_request)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@patch("api.routers.auth.send_code", new_callable=AsyncMock)
@patch("api.routers.auth.check_user_exists", new_callable=AsyncMock, return_value=False)
async def test_reset_password_send_code_masks_unknown_email_without_sending(
    mock_check_user_exists,
    mock_send_code,
):
    request = SendCodeRequest(email="unknown@example.com", purpose="reset_password")

    response = await auth_send_code(request)

    assert response.success is True
    assert response.message == "If an account exists for this email, a verification code has been sent"
    assert response.expires_in_seconds > 0
    mock_check_user_exists.assert_awaited_once_with("unknown@example.com")
    mock_send_code.assert_not_awaited()
