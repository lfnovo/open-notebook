import time
from typing import Literal, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.jwt_auth import validate_jwt_token
from open_notebook.database.repository import db_connection
from open_notebook.utils.encryption import get_secret_from_env

# Cache for "has users" check (avoids DB query on every request)
_has_users_cache: Optional[bool] = None
_cache_time: float = 0
_CACHE_TTL = 30  # seconds


class CurrentUser(BaseModel):
    id: str
    username: str
    role: Literal["admin", "user"] = "user"
    status: Literal["active", "disabled"] = "active"
    display_name: Optional[str] = None
    email: Optional[str] = None


def invalidate_has_users_cache() -> None:
    """Clear the cached result for user existence checks."""
    global _has_users_cache, _cache_time
    _has_users_cache = None
    _cache_time = 0


async def _check_has_users() -> bool:
    """Check if any users exist in the database (with caching)."""
    global _has_users_cache, _cache_time
    now = time.time()
    if _has_users_cache is not None and (now - _cache_time) < _CACHE_TTL:
        return _has_users_cache

    try:
        async with db_connection() as conn:
            result = await conn.query("SELECT count() FROM app_user GROUP ALL")
            if isinstance(result, list) and result:
                # Flatten nested result
                row = result[0]
                if isinstance(row, list) and row:
                    row = row[0]
                if isinstance(row, dict) and row.get("count", 0) > 0:
                    _has_users_cache = True
                    _cache_time = now
                    return True
            _has_users_cache = False
            _cache_time = now
            return False
    except Exception as e:
        logger.debug(f"Failed to check users: {e}")
        return False


class PasswordAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for password authentication with dual-mode support:
    - none mode: no authentication, for local development only
    - Legacy mode: OPEN_NOTEBOOK_PASSWORD env var (plain text comparison)
    - Database mode: JWT tokens validated against app_user table
    - auto mode: legacy password if configured, otherwise JWT if users exist

    Configure with OPEN_NOTEBOOK_AUTH_MODE=none|password|jwt|auto.
    The default is auto for backward compatibility.
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
        self.auth_mode = self._get_auth_mode()
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    def _get_auth_mode(self) -> str:
        import os

        auth_mode = os.getenv("OPEN_NOTEBOOK_AUTH_MODE", "auto").strip().lower()
        if auth_mode not in {"none", "password", "jwt", "auto"}:
            logger.warning(
                f"Invalid OPEN_NOTEBOOK_AUTH_MODE={auth_mode!r}; falling back to auto"
            )
            return "auto"
        return auth_mode

    async def dispatch(self, request: Request, call_next):
        # Skip for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Skip for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip for auth endpoints (they handle their own auth)
        if request.url.path.startswith("/api/auth/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if self.auth_mode == "none":
            request.state.user_id = None
            request.state.username = None
            return await call_next(request)

        # --- Legacy mode: env var password ---
        if self.auth_mode == "password" or (
            self.auth_mode == "auto" and self.legacy_password
        ):
            if self.auth_mode == "password" and not self.legacy_password:
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "OPEN_NOTEBOOK_AUTH_MODE=password requires OPEN_NOTEBOOK_PASSWORD"
                    },
                )

            if not auth_header:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing authorization header"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                scheme, credentials = auth_header.split(" ", 1)
                if scheme.lower() != "bearer":
                    raise ValueError("Invalid authentication scheme")
            except ValueError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid authorization header format"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if credentials == self.legacy_password:
                request.state.user_id = None
                request.state.username = None
                request.state.user_role = None
                request.state.user_status = None
                return await call_next(request)

            payload = await validate_jwt_token(credentials)
            if payload:
                request.state.user_id = payload.get("sub")
                request.state.username = payload.get("username")
                request.state.user_role = payload.get("role", "user")
                request.state.user_status = payload.get("status", "active")
                request.state.display_name = payload.get("display_name")
                request.state.email = payload.get("email")
                return await call_next(request)

            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid password or token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # --- Database mode: JWT validation ---
        has_users = True if self.auth_mode == "jwt" else await _check_has_users()
        if self.auth_mode == "auto" and not has_users:
            # No users and no legacy password = no auth required
            request.state.user_id = None
            request.state.username = None
            request.state.user_role = None
            request.state.user_status = None
            return await call_next(request)

        # Users exist - require JWT
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = await validate_jwt_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract user identity for downstream route use
        request.state.user_id = payload.get("sub")
        request.state.username = payload.get("username")
        request.state.user_role = payload.get("role", "user")
        request.state.user_status = payload.get("status", "active")
        request.state.display_name = payload.get("display_name")
        request.state.email = payload.get("email")

        return await call_next(request)


# Optional: HTTPBearer security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


async def check_api_password(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> bool:
    """
    Utility function to check API password for route-level auth.
    Supports both legacy password and JWT tokens.
    """
    legacy_password = get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")

    if not credentials:
        # No credentials - check if auth is even required
        if legacy_password:
            raise HTTPException(
                status_code=401,
                detail="Missing authorization",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return True

    # Try legacy password first
    if legacy_password and credentials.credentials == legacy_password:
        return True

    # Try JWT
    payload = await validate_jwt_token(credentials.credentials)
    if payload:
        return True

    raise HTTPException(
        status_code=401,
        detail="Invalid authorization",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(request: Request) -> CurrentUser:
    """Return the authenticated database user from middleware state."""
    user_id = getattr(request.state, "user_id", None)
    username = getattr(request.state, "username", None)
    if not user_id or not username:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    status = getattr(request.state, "user_status", "active") or "active"
    if status != "active":
        raise HTTPException(status_code=403, detail="User is disabled")

    return CurrentUser(
        id=str(user_id),
        username=str(username),
        role=getattr(request.state, "user_role", "user") or "user",
        status=status,
        display_name=getattr(request.state, "display_name", None),
        email=getattr(request.state, "email", None),
    )


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Require a system admin user."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
