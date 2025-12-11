import os
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from open_notebook.database.repository import repo_query
from open_notebook.domain.user import User


class PasswordAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check password authentication for all API requests.
    Supports both legacy password-based auth and user-based auth.
    """
    
    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.legacy_password = os.environ.get("OPEN_NOTEBOOK_PASSWORD")
        self.excluded_paths = excluded_paths or ["/", "/health", "/docs", "/openapi.json", "/redoc"]
        self._has_users_cache = None
    
    async def _has_users_in_database(self) -> bool:
        """Check if there are any users in the database."""
        if self._has_users_cache is not None:
            return self._has_users_cache
        
        try:
            users = await repo_query("SELECT * FROM user LIMIT 1")
            has_users = len(users) > 0 if users else False
            self._has_users_cache = has_users
            return has_users
        except Exception as e:
            logger.error(f"Error checking for users: {str(e)}")
            self._has_users_cache = False
            return False
    
    async def _validate_user_password(self, password: str) -> bool:
        """
        Validate password against any user in the database.
        Returns True if password matches any user's password.
        """
        try:
            users = await repo_query("SELECT * FROM user")
            if not users:
                return False
            
            # Check if password matches any user's password
            for user_data in users:
                user = User(**user_data)
                if user.verify_password(password):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error validating user password: {str(e)}")
            return False
    
    async def dispatch(self, request: Request, call_next):
        # Check if authentication is required
        has_users = await self._has_users_in_database()
        legacy_auth_enabled = bool(self.legacy_password)
        
        # Skip authentication if neither legacy password nor users exist
        if not legacy_auth_enabled and not has_users:
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
                headers={"WWW-Authenticate": "Bearer"}
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
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate credentials
        is_valid = False
        
        # Check legacy password if enabled
        if legacy_auth_enabled and credentials == self.legacy_password:
            is_valid = True
        
        # Check user passwords if users exist
        if not is_valid and has_users:
            is_valid = await self._validate_user_password(credentials)
        
        if not is_valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid password"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Authentication successful, proceed with the request
        response = await call_next(request)
        return response


# Optional: HTTPBearer security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


def check_api_password(credentials: Optional[HTTPAuthorizationCredentials] = None) -> bool:
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