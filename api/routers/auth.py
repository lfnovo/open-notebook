"""
Authentication router for Lumina API.

Provides endpoints for username/password login, password change, and first-time setup.
Uses bcrypt for password hashing and JWT for session tokens.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from api.auth import invalidate_has_users_cache
from api.jwt_auth import create_jwt_token, find_user_by_username, validate_jwt_token
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from api.models import (
    AuthStatusResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SendCodeRequest,
    SendCodeResponse,
    SetupRequest,
    UserResponse,
)
from api.password_utils import hash_password, verify_password
from api.verification import (
    ALLOW_PUBLIC_REGISTRATION,
    CODE_TTL_SECONDS,
    check_user_exists,
    send_code,
    verify_code,
)
from open_notebook.database.repository import (
    db_connection,
    parse_record_ids,
    repo_update,
)
from open_notebook.utils.encryption import get_secret_from_env

router = APIRouter(prefix="/auth", tags=["auth"])

# JWT configuration shared in api.jwt_auth
JWT_EXPIRY_SECONDS = 86400  # 24 hours


async def _get_db_users() -> List[Dict[str, Any]]:
    """Query all users from the database."""
    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query("SELECT * FROM app_user ORDER BY created ASC")
            )
            if isinstance(result, list):
                # Flatten nested result structure from SurrealDB
                if result and isinstance(result[0], list):
                    return result[0]
                return result
            return []
    except Exception as e:
        logger.debug(f"Failed to query users: {e}")
        return []


def _get_user_id(user: Dict[str, Any]) -> str:
    """Extract user ID from user record."""
    user_id = user.get("id", "")
    # Convert RecordID to string if needed
    if hasattr(user_id, "__str__"):
        return str(user_id)
    return str(user_id)


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status():
    """
    Check authentication status.
    Returns whether auth is enabled, the auth method, and if users exist.
    """
    legacy_password = bool(get_secret_from_env("OPEN_NOTEBOOK_PASSWORD"))
    users = await _get_db_users()
    has_users = len(users) > 0

    if legacy_password:
        return AuthStatusResponse(
            auth_enabled=True,
            auth_method="legacy",
            has_users=has_users,
            message="Legacy password authentication is active",
        )
    elif has_users:
        return AuthStatusResponse(
            auth_enabled=True,
            auth_method="database",
            has_users=True,
            message="Database authentication is active",
        )
    else:
        return AuthStatusResponse(
            auth_enabled=False,
            auth_method="disabled",
            has_users=False,
            message="No authentication configured. Use /auth/setup to create an admin user.",
        )


@router.post("/setup", response_model=UserResponse)
async def setup_admin(request: SetupRequest, http_request: Request):
    """
    Create the first admin user. Only works when no users exist in the database.
    """
    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    if legacy_password:
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != legacy_password:
            raise HTTPException(status_code=401, detail="Unauthorized")

    if len(await _get_db_users()) > 0:
        raise HTTPException(
            status_code=400,
            detail="Setup already completed. Users exist in the database.",
        )

    if len(request.password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters long",
        )

    hashed = hash_password(request.password)

    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query(
                    """
                    CREATE app_user SET
                        username = $username,
                        display_name = $username,
                        role = 'admin',
                        status = 'active',
                        hashed_password = $hashed,
                        password_changed_at = time::now(),
                        created = time::now(),
                        updated = time::now()
                    """,
                    {
                        "username": request.username,
                        "hashed": hashed,
                    },
                )
            )
            # Flatten result
            if isinstance(result, list) and result:
                if isinstance(result[0], list):
                    user = result[0][0]
                else:
                    user = result[0]
            else:
                raise HTTPException(status_code=500, detail="Failed to create user")

            invalidate_has_users_cache()
            return UserResponse(
                id=str(user.get("id", "")),
                username=user.get("username", request.username),
                display_name=user.get("display_name"),
                role=user.get("role", "admin"),
                status=user.get("status", "active"),
                created=str(user.get("created", "")),
                updated=str(user.get("updated", "")),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate with username and password. Returns a JWT token on success.
    """
    # Check legacy password first
    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    if legacy_password and request.password == legacy_password:
        # Legacy auth: return the shared password itself so protected routes
        # and auth-store revalidation continue to work in legacy mode.
        token = legacy_password
        return LoginResponse(
            success=True,
            token=token,
            username=request.username,
            message="Login successful",
        )

    # Database auth
    user = await find_user_by_username(request.username)
    if not user:
        await AuditLogRepository.create(
            action="auth.login.failed",
            actor_username=request.username,
            target_type="app_user",
            target_id=request.username,
            metadata={"reason": "user_not_found"},
        )
        return LoginResponse(
            success=False,
            message="Invalid username or password",
        )

    if not verify_password(request.password, user.get("hashed_password", "")):
        await AuditLogRepository.create(
            action="auth.login.failed",
            actor_username=request.username,
            target_type="app_user",
            target_id=str(user.get("id", request.username)),
            metadata={"reason": "invalid_password"},
        )
        return LoginResponse(
            success=False,
            message="Invalid username or password",
        )

    if user.get("status", "active") != "active":
        await AuditLogRepository.create(
            action="auth.login.failed",
            actor_username=request.username,
            target_type="app_user",
            target_id=str(user.get("id", request.username)),
            metadata={"reason": "disabled"},
        )
        return LoginResponse(
            success=False,
            message="Account is disabled",
        )

    user_id = _get_user_id(user)
    token = create_jwt_token(request.username, user_id, user)
    try:
        await repo_update(
            "app_user",
            user_id,
            {"last_login_at": datetime.now(timezone.utc)},
        )
        await AuditLogRepository.create(
            action="auth.login.success",
            actor_id=user_id,
            actor_username=request.username,
            target_type="app_user",
            target_id=user_id,
        )
    except Exception as e:
        logger.warning(f"Failed to record login metadata for {request.username}: {e}")

    return LoginResponse(
        success=True,
        token=token,
        username=request.username,
        message="Login successful",
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(request: ChangePasswordRequest, http_request: Request):
    """
    Change the current user's password. Requires authentication.
    """
    # Get JWT token from Authorization header
    auth_header = http_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Try legacy password as token
        token = auth_header

    # If no auth header, try the token from the request itself
    # (the legacy middleware might have already authenticated)
    payload = None
    if token:
        payload = await validate_jwt_token(token)

    # Also check legacy password
    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    is_legacy = legacy_password and request.old_password == legacy_password

    if not payload and not is_legacy:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if is_legacy:
        # Legacy mode: update the env var password is not possible
        # Instead, create/update a user in the database
        users = await _get_db_users()
        if users:
            # Update first user's password
            user = users[0]
            user_id = _get_user_id(user)
            username = user.get("username", "admin")
        else:
            # Create admin user
            username = "admin"
            user_id = "app_user:admin"

        if len(request.new_password) < 4:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 4 characters long",
            )

        hashed = hash_password(request.new_password)

        try:
            await repo_update(
                "app_user",
                user_id,
                {
                    "username": username,
                    "hashed_password": hashed,
                    "password_changed_at": datetime.now(timezone.utc),
                },
            )
            return ChangePasswordResponse(
                success=True,
                message="Password changed. Future logins should use username + new password.",
            )
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")

    # Database auth mode
    username = payload.get("username", "")
    user = await find_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_password(request.old_password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(request.new_password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 4 characters long",
        )

    hashed = hash_password(request.new_password)
    user_id = _get_user_id(user)

    try:
        await repo_update(
            "app_user",
            user_id,
            {
                "hashed_password": hashed,
                "password_changed_at": datetime.now(timezone.utc),
            },
        )
        try:
            await AuditLogRepository.create(
                action="auth.password.changed",
                actor_id=user_id,
                actor_username=username,
                target_type="app_user",
                target_id=user_id,
            )
        except Exception as audit_error:
            logger.warning(f"Failed to write password-change audit log: {audit_error}")
        return ChangePasswordResponse(
            success=True,
            message="Password changed successfully",
        )
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(http_request: Request):
    """
    Get current authenticated user info. Requires JWT token.
    """
    auth_header = http_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        raise HTTPException(status_code=401, detail="Missing authorization")

    payload = await validate_jwt_token(token)
    if not payload:
        legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
        if legacy_password and token == legacy_password:
            return UserResponse(username="legacy", created="", updated="")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("username", "")
    user = await find_user_by_username(username)
    if not user:
        return UserResponse(
            username=username,
            created="",
            updated="",
        )

    return UserResponse(
        id=str(user.get("id", "")),
        username=user.get("username", username),
        email=user.get("email"),
        display_name=user.get("display_name"),
        role=user.get("role", "user"),
        status=user.get("status", "active"),
        locale=user.get("locale"),
        theme=user.get("theme"),
        created=str(user.get("created", "")),
        updated=str(user.get("updated", "")),
        last_login_at=str(user.get("last_login_at", "")) if user.get("last_login_at") else None,
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(request: ProfileUpdateRequest, http_request: Request):
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")
    payload = await validate_jwt_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("username", "")
    user = await find_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = _get_user_id(user)
    updates = {}
    if request.display_name is not None:
        updates["display_name"] = request.display_name
    if request.locale is not None:
        updates["locale"] = request.locale
    if request.theme is not None:
        updates["theme"] = request.theme
    if updates:
        updated = await repo_update("app_user", user_id, updates)
        user = updated[0] if updated else {**user, **updates}
    return UserResponse(
        id=str(user.get("id", "")),
        username=user.get("username", username),
        email=user.get("email"),
        display_name=user.get("display_name"),
        role=user.get("role", "user"),
        status=user.get("status", "active"),
        locale=user.get("locale"),
        theme=user.get("theme"),
        created=str(user.get("created", "")),
        updated=str(user.get("updated", "")),
        last_login_at=str(user.get("last_login_at", ""))
        if user.get("last_login_at")
        else None,
    )


@router.post("/send-code", response_model=SendCodeResponse)
async def auth_send_code(request: SendCodeRequest):
    """
    Send a verification code to an email address.
    Used for both registration and password reset.
    """
    if request.purpose == "reset_password" and not await check_user_exists(request.email):
        return SendCodeResponse(
            success=True,
            message="If an account exists for this email, a verification code has been sent",
            expires_in_seconds=CODE_TTL_SECONDS,
        )

    ok, msg = await send_code(request.email, request.purpose, request.language)
    return SendCodeResponse(
        success=ok,
        message=msg,
        expires_in_seconds=CODE_TTL_SECONDS,
    )


@router.post("/register", response_model=RegisterResponse)
async def auth_register(request: RegisterRequest):
    """
    Register a new account with email + verification code + password.
    Public registration must be enabled via ALLOW_PUBLIC_REGISTRATION env var.
    """
    # Check if registration is allowed
    if not ALLOW_PUBLIC_REGISTRATION:
        return RegisterResponse(
            success=False,
            message="Public registration is disabled",
            username=None,
        )

    if await check_user_exists(request.email):
        return RegisterResponse(
            success=False,
            message="An account with this email already exists",
            username=None,
        )

    # Verify the code
    ok, msg = await verify_code(request.email, request.code, "register")
    if not ok:
        return RegisterResponse(
            success=False,
            message=msg,
            username=None,
        )

    # Create the user
    hashed = hash_password(request.password)
    try:
        async with db_connection() as conn:
            result = parse_record_ids(
                await conn.query(
                    """
                    CREATE app_user SET
                        username = $username,
                        email = $username,
                        display_name = $username,
                        role = 'user',
                        status = 'active',
                        hashed_password = $hashed,
                        password_changed_at = time::now(),
                        created = time::now(),
                        updated = time::now()
                    """,
                    {
                        "username": request.email,
                        "hashed": hashed,
                    },
                )
            )
            if isinstance(result, list) and result:
                if isinstance(result[0], list):
                    user = result[0][0]
                else:
                    user = result[0]
            else:
                raise Exception("Failed to create user record")

            logger.info(f"New user registered: {request.email}")
            invalidate_has_users_cache()
            return RegisterResponse(
                success=True,
                message="Account created successfully",
                username=request.email,
            )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def auth_reset_password(request: ResetPasswordRequest):
    """
    Reset a user's password using email + verification code + new password.
    """
    # Check user exists
    if not await check_user_exists(request.email):
        # Don't reveal whether the email exists
        return ResetPasswordResponse(
            success=False,
            message="Invalid or expired code",
        )

    # Verify the code
    ok, msg = await verify_code(request.email, request.code, "reset_password")
    if not ok:
        return ResetPasswordResponse(
            success=False,
            message=msg,
        )

    # Update the password
    hashed = hash_password(request.new_password)
    user = await find_user_by_username(request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = _get_user_id(user)

    try:
        await repo_update(
            "app_user",
            user_id,
            {
                "hashed_password": hashed,
                "password_changed_at": datetime.now(timezone.utc),
            },
        )
        await AuditLogRepository.create(
            action="auth.password.reset",
            actor_id=user_id,
            actor_username=request.email,
            target_type="app_user",
            target_id=user_id,
        )
        logger.info(f"Password reset for user: {request.email}")
        return ResetPasswordResponse(
            success=True,
            message="Password reset successfully",
        )
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Password reset failed: {str(e)}")
