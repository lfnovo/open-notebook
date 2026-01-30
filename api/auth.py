import os
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import bcrypt
from loguru import logger


def verify_password(provided: str, stored: str) -> bool:
    """
    Verify a provided plaintext password against the stored value.

    - If `stored` looks like a bcrypt hash (starts with "$2"), use bcrypt.checkpw.
    - Otherwise treat `stored` as a plaintext secret and compare directly.

    Returns True if the password is valid, False otherwise.
    """
    if not stored:
        return False

    # bcrypt-style hashes begin with "$2b$", "$2a$", "$2y$", etc.
    if isinstance(stored, str) and stored.startswith("$2"):
        try:
            return bcrypt.checkpw(provided.encode("utf-8"), stored.encode("utf-8"))
        except Exception as e:
            # Any error in bcrypt verification should be treated as an invalid password
            logger.error(f"bcrypt verification failed: {e}")
            return False

    # Plaintext comparison
    return secrets.compare_digest(provided, stored)


class PasswordAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check password authentication for all API requests.
    Active when OPEN_NOTEBOOK_PASSWORD environment variable is set.

    Behavior:
    - If OPEN_NOTEBOOK_PASSWORD starts with "$2" it's treated as a bcrypt hash and
      incoming Bearer tokens are verified using verify_password().
    - Otherwise the value is treated as a plaintext secret and compared directly.
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
        # No auth configured
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
                raise ValueError()
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password via helper
        if not verify_password(credentials, self.password):
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
    Dependency utility to verify the API password for individual routes.
    Uses verify_password() for the actual check.
    """
    password_env = os.environ.get("OPEN_NOTEBOOK_PASSWORD")
    if not password_env:
        return True

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.credentials, password_env):
        raise HTTPException(
            status_code=401,
            detail="Invalid password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
