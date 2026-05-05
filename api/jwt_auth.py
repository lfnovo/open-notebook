from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import jwt
from loguru import logger

from open_notebook.database.repository import db_connection, parse_record_ids
from open_notebook.utils.encryption import get_secret_from_env

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 86400  # 24 hours


def get_jwt_secret() -> str:
    """Return the configured JWT secret.

    Priority:
    1. OPEN_NOTEBOOK_ENCRYPTION_KEY
    2. OPEN_NOTEBOOK_PASSWORD (legacy compatibility only)

    Raises RuntimeError if neither is configured.
    """
    encryption_key = get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY")
    if encryption_key:
        return encryption_key

    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    if legacy_password:
        return legacy_password

    raise RuntimeError(
        "JWT secret is not configured. Set OPEN_NOTEBOOK_ENCRYPTION_KEY "
        "(preferred) or OPEN_NOTEBOOK_PASSWORD (legacy fallback)."
    )


def _normalize_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def get_user_auth_version(user: Dict[str, Any]) -> str:
    """Convert the user's latest auth-relevant timestamp into a stable version string."""
    password_changed_at = _normalize_datetime(user.get("password_changed_at"))
    updated_at = _normalize_datetime(user.get("updated"))
    created_at = _normalize_datetime(user.get("created"))
    basis = password_changed_at or updated_at or created_at or datetime.now(timezone.utc)
    return basis.astimezone(timezone.utc).isoformat(timespec="microseconds")


def create_jwt_token(username: str, user_id: str, user: Dict[str, Any]) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "auth_version": get_user_auth_version(user),
        "exp": now + JWT_EXPIRY_SECONDS,
        "iat": now,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except RuntimeError as e:
        logger.error(str(e))
        return None
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid JWT token: {e}")
        return None


async def find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query(
                    "SELECT * FROM app_user WHERE username = $username LIMIT 1",
                    {"username": username},
                )
            )
            if isinstance(result, list):
                users = result[0] if result and isinstance(result[0], list) else result
                return users[0] if users else None
            return None
    except Exception as e:
        logger.debug(f"Failed to find user for JWT validation: {e}")
        return None


async def validate_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    payload = decode_jwt_token(token)
    if not payload:
        return None

    username = payload.get("username")
    if not username:
        logger.debug("JWT token missing username claim")
        return None

    user = await find_user_by_username(username)
    if not user:
        logger.debug("JWT token user no longer exists")
        return None

    if user.get("status", "active") != "active":
        logger.info(f"JWT token rejected for inactive user={username}")
        return None

    token_auth_version = payload.get("auth_version")
    current_auth_version = get_user_auth_version(user)
    if token_auth_version != current_auth_version:
        logger.info(
            f"JWT token invalidated for user={username}: token version {token_auth_version} != current {current_auth_version}"
        )
        return None

    payload["sub"] = str(user.get("id", payload.get("sub")))
    payload["role"] = user.get("role", "user")
    payload["status"] = user.get("status", "active")
    payload["display_name"] = user.get("display_name")
    payload["email"] = user.get("email")
    return payload
