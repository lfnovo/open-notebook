"""
Authentication router for Open Notebook API.
Provides endpoints to check authentication status and handle login.
"""

import os

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from open_notebook.domain.user import User
from open_notebook.exceptions import InvalidInputError

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request model."""
    email: str  
    password: str


class SignupRequest(BaseModel):
    """Signup request model."""
    email: str
    password: str
    confirm_password: str


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    message: str
    token: str | None = None


class SignupResponse(BaseModel):
    """Signup response model."""
    success: bool
    message: str
    user_id: str | None = None


@router.get("/status")
async def get_auth_status():
    """
    Check if authentication is enabled.
    Returns whether authentication is required to access the API.
    Checks if there are any users in the database or if legacy env var is set.
    """
    # Check legacy environment variable for backward compatibility
    legacy_auth_enabled = bool(os.environ.get("OPEN_NOTEBOOK_PASSWORD"))
    
    # Check if there are any users in the database
    try:
        from open_notebook.database.repository import repo_query
        users = await repo_query("SELECT * FROM user LIMIT 1")
        has_users = len(users) > 0 if users else False
    except Exception as e:
        logger.error(f"Error checking for users: {str(e)}")
        has_users = False
    
    # Authentication is enabled if either legacy env var is set OR there are users in DB
    auth_enabled = legacy_auth_enabled or has_users

    return {
        "auth_enabled": auth_enabled,
        "message": "Authentication is required" if auth_enabled else "Authentication is disabled",
        "has_users": has_users,
        "legacy_auth": legacy_auth_enabled
    }


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """
    Authenticate user with email and password.
    Validates email and password against the user table in the database.
    Returns a token on success.
    """
    try:
        # Validate email format
        if not login_request.email or not login_request.email.strip():
            raise HTTPException(
                status_code=400,
                detail="Email is required"
        )
    
        # Look up user by email in the database
        user = await User.get_by_email(login_request.email)
        
        if not user:
            # User not found - return generic error to prevent email enumeration
            logger.warning(f"Login attempt with non-existent email: {login_request.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
    
        # Verify the password against the stored hash
        if not user.verify_password(login_request.password):
            # Password doesn't match - return generic error
            logger.warning(f"Failed login attempt for email: {login_request.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
    
        # Password is correct - update last login timestamp
        await user.update_last_login()
        
        logger.info(f"Successful login for user: {login_request.email}")
        
        # Return success with token (using password for now, can be upgraded to JWT later)
        return LoginResponse(
            success=True,
            message="Login successful",
            token=login_request.password  
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 401, 400)
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Failed to authenticate. Please try again."
    )


@router.post("/signup", response_model=SignupResponse)
async def signup(signup_request: SignupRequest):
    """
    Create a new user account.
    Validates email format, password match, and checks for existing users.
    """
    try:
        # Validate email format
        if not signup_request.email or not signup_request.email.strip():
            raise HTTPException(
                status_code=400,
                detail="Email is required"
            )

        # Validate password match
        if signup_request.password != signup_request.confirm_password:
            raise HTTPException(
                status_code=400,
                detail="Passwords do not match"
            )

        # Validate password length
        if len(signup_request.password) < 8:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters long"
            )

        # Create user
        user = await User.create(
            email=signup_request.email,
            password=signup_request.password
        )

        logger.info(f"New user signed up: {signup_request.email}")

        return SignupResponse(
            success=True,
            message="Account created successfully",
            user_id=str(user.id)
        )

    except InvalidInputError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Failed to create account. Please try again."
        )
