import asyncio
import os
from typing import Dict, Optional, Set

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from open_notebook.database.async_migrate import AsyncMigrationManager
from open_notebook.user_context import current_user

# Track which users have been migrated (in-memory cache, resets on restart)
_migrated_users: Set[str] = set()
# Per-user locks to prevent concurrent migration runs for the same user
_migration_locks: Dict[str, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def _get_user_lock(user: str) -> asyncio.Lock:
    """Get or create an asyncio.Lock for a specific user."""
    async with _locks_lock:
        if user not in _migration_locks:
            _migration_locks[user] = asyncio.Lock()
        return _migration_locks[user]


async def ensure_user_migrated(user: str):
    """Run DB migrations for a user's database if not already done."""
    if user in _migrated_users:
        return
    lock = await _get_user_lock(user)
    async with lock:
        # Double-check after acquiring lock
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

    SECURITY: X-Forwarded-User MUST be set by a trusted auth proxy that strips
    any client-provided X-Forwarded-User header. In production, ensure this app
    is only reachable through the proxy (network policy / firewall).
    Optionally set PROXY_AUTH_SECRET env var for shared-secret verification.
    """

    def __init__(self, app, excluded_paths: Optional[list] = None):
        self.app = app
        self.excluded_paths: Set[str] = set(excluded_paths or [
            "/", "/health", "/docs", "/openapi.json", "/redoc",
        ])
        # Optional shared secret: proxy must send X-Proxy-Auth-Secret header
        self.proxy_secret = os.environ.get("PROXY_AUTH_SECRET", "")

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

        # Extract headers from ASGI scope (list of byte tuples)
        headers = dict(scope.get("headers", []))

        # If PROXY_AUTH_SECRET is set, verify the proxy sent it
        if self.proxy_secret:
            provided_secret = headers.get(b"x-proxy-auth-secret", b"").decode().strip()
            if provided_secret != self.proxy_secret:
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "Invalid or missing proxy auth secret"},
                )
                await response(scope, receive, send)
                return

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
