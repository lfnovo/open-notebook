"""
Authentication router for Open Notebook API.
Provides endpoints to check authentication status and handle login.
"""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    message: str
    token: str | None = None


@router.get("/status")
async def get_auth_status():
    """
    Check if authentication is enabled.
    Returns whether a password is required to access the API.
    """
    auth_enabled = bool(os.environ.get("OPEN_NOTEBOOK_PASSWORD"))

    return {
        "auth_enabled": auth_enabled,
        "message": "Authentication is required" if auth_enabled else "Authentication is disabled"
    }


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """
    Authenticate user with username and password.
    Validates both username and password against environment variables.
    Returns a token (password) on success.
    """
    expected_password = os.environ.get("OPEN_NOTEBOOK_PASSWORD")
    expected_username = os.environ.get("OPEN_NOTEBOOK_USERNAME")
    
    # If no password is set, authentication is disabled
    if not expected_password:
        return LoginResponse(
            success=True,
            message="Authentication is disabled",
            token="not-required"
        )
    
    # Validate username (case-insensitive for email addresses)
    if expected_username:
        # Compare emails/usernames case-insensitively
        if login_request.username.strip().lower() != expected_username.strip().lower():
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )
    
    # Validate password
    if login_request.password != expected_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    # Both username and password are correct - return success with token (password)
    # In the future, this could return a JWT token instead
    return LoginResponse(
        success=True,
        message="Login successful",
        token=login_request.password
    )
