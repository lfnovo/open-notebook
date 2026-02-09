import os
from typing import Optional, Set

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.user_context import current_user

# Track which users have been migrated (in-memory cache, resets on restart)
_migrated_users: Set[str] = set()


async def ensure_user_migrated(user: str):
    """Run DB migrations for a user's database if not already done."""
    if user in _migrated_users:
        return
    manager = AsyncMigrationManager()
    if await manager.needs_migration():
        logger.info(f"Running migrations for user database: {user}")
        await manager.run_migration_up()
    _migrated_users.add(user)


class ProxyAuthMiddleware:
    """
    Pure ASGI middleware that reads X-Forwarded-User header (set by OAuth2 Proxy
    or any auth proxy) and sets the current_user contextvar for per-user DB routing.

    Uses pure ASGI (not BaseHTTPMiddleware) so contextvars propagate correctly
    to all async handlers and database connections.
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        self.app = app
        self.excluded_paths: Set[str] = set(excluded_paths or [
            "/", "/health", "/docs", "/openapi.json", "/redoc",
        ])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.excluded_paths:
            await self.app(scope, receive, send)
            return

        # Skip CORS preflight
        method = scope.get("method", "")
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Extract X-Forwarded-User from ASGI headers (list of byte tuples)
        headers = dict(scope.get("headers", []))
        user = headers.get(b"x-forwarded-user", b"").decode().strip()

        if not user:
            response = JSONResponse(
                status_code=401,
                content={"detail": "Missing X-Forwarded-User header"},
            )
            await response(scope, receive, send)
            return

        # Set contextvar for this request — db_connection() reads it
        token = current_user.set(user)
        try:
            await ensure_user_migrated(user)
            await self.app(scope, receive, send)
        finally:
            current_user.reset(token)


class PasswordAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check password authentication for all API requests.
    Only active when OPEN_NOTEBOOK_PASSWORD environment variable is set.
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.password = os.environ.get("OPEN_NOTEBOOK_PASSWORD")
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip authentication if no password is set
        if not self.password:
            return await call_next(request)

        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Skip authentication for CORS preflight requests (OPTIONS)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Expected format: "Bearer {password}"
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

        # Check password
        if credentials != self.password:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid password"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Password is correct, proceed with the request
        response = await call_next(request)
        return response


# Optional: HTTPBearer security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


def check_api_password(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> bool:
    """
    Utility function to check API password.
    Can be used as a dependency in individual routes if needed.
    """
    password = os.environ.get("OPEN_NOTEBOOK_PASSWORD")

    # No password set, allow access
    if not password:
        return True

    # No credentials provided
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check password
    if credentials.credentials != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
