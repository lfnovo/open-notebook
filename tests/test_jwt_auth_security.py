from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from api.jwt_auth import create_jwt_token, get_jwt_secret, validate_jwt_token
from api.verification import hash_verification_code, send_code, verify_code


@patch("api.jwt_auth.get_secret_from_env")
def test_get_jwt_secret_uses_legacy_password_when_encryption_key_missing(mock_get_secret):
    def fake_get_secret(name: str):
        if name == "OPEN_NOTEBOOK_ENCRYPTION_KEY":
            return None
        if name == "OPEN_NOTEBOOK_PASSWORD":
            return "legacy-shared-password"
        return None

    mock_get_secret.side_effect = fake_get_secret

    assert get_jwt_secret() == "legacy-shared-password"


@patch("api.jwt_auth.get_secret_from_env", return_value=None)
def test_get_jwt_secret_requires_configured_secret_when_no_fallback(mock_get_secret):
    with pytest.raises(RuntimeError, match="JWT secret is not configured"):
        get_jwt_secret()


@pytest.mark.asyncio
@patch("api.jwt_auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.jwt_auth.get_secret_from_env", return_value="test-jwt-secret-with-sufficient-length-32")
async def test_validate_jwt_token_rejects_stale_token_after_user_update(
    mock_get_secret,
    mock_find_user,
):
    original_user = {
        "id": "app_user:admin",
        "username": "admin",
        "updated": datetime(2026, 4, 24, 8, 0, 0, tzinfo=timezone.utc),
    }
    token = create_jwt_token("admin", "app_user:admin", original_user)

    mock_find_user.return_value = {
        **original_user,
        "updated": datetime(2026, 4, 24, 8, 5, 0, tzinfo=timezone.utc),
    }

    assert await validate_jwt_token(token) is None


@pytest.mark.asyncio
@patch("api.jwt_auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.jwt_auth.get_secret_from_env", return_value="test-jwt-secret-with-sufficient-length-32")
async def test_validate_jwt_token_accepts_current_user_version(
    mock_get_secret,
    mock_find_user,
):
    user = {
        "id": "app_user:admin",
        "username": "admin",
        "updated": datetime(2026, 4, 24, 8, 0, 0, tzinfo=timezone.utc),
    }
    token = create_jwt_token("admin", "app_user:admin", user)

    mock_find_user.return_value = user

    payload = await validate_jwt_token(token)
    assert payload is not None
    assert payload["username"] == "admin"


@pytest.mark.asyncio
@patch("api.jwt_auth.find_user_by_username", new_callable=AsyncMock)
@patch("api.jwt_auth.get_secret_from_env", return_value="test-jwt-secret-with-sufficient-length-32")
async def test_validate_jwt_token_rejects_disabled_user(
    mock_get_secret,
    mock_find_user,
):
    user = {
        "id": "app_user:admin",
        "username": "admin",
        "status": "active",
        "updated": datetime(2026, 4, 24, 8, 0, 0, tzinfo=timezone.utc),
    }
    token = create_jwt_token("admin", "app_user:admin", user)

    mock_find_user.return_value = {**user, "status": "disabled"}

    assert await validate_jwt_token(token) is None


@patch("api.verification.get_secret_from_env", return_value="verification-secret-with-sufficient-length")
def test_hash_verification_code_is_deterministic_and_not_plaintext(mock_get_secret):
    raw = "123456"
    hashed = hash_verification_code(raw)

    assert hashed != raw
    assert hashed == hash_verification_code(raw)
    assert len(hashed) == 64


@pytest.mark.asyncio
@patch("api.verification.get_secret_from_env", return_value="verification-secret-with-sufficient-length")
@patch("api.verification._increment_code_attempts", new_callable=AsyncMock)
@patch("api.verification._get_active_code", new_callable=AsyncMock)
async def test_verify_code_hashes_input_and_increments_attempts_on_mismatch(
    mock_get_active_code,
    mock_increment_code_attempts,
    mock_get_secret,
):
    mock_get_active_code.return_value = {
        "id": "verification_code:test",
        "email": "user@example.com",
        "purpose": "register",
        "code": hash_verification_code("654321"),
    }

    ok, message = await verify_code("user@example.com", "123456", "register")

    assert ok is False
    assert message == "Invalid code"
    mock_increment_code_attempts.assert_awaited_once_with("verification_code:test")
