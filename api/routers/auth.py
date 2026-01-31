"""
Authentication router for Open Notebook API.
Provides endpoints to check authentication status.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_secret_from_env(var_name: str) -> Optional[str]:
    """
    Get a secret from environment, supporting Docker secrets pattern.

    Checks for VAR_FILE first (Docker secrets), then falls back to VAR.
    """
    # Check for _FILE variant first (Docker secrets)
    file_path = os.environ.get(f"{var_name}_FILE")
    if file_path:
        path = Path(file_path)
        if path.exists() and path.is_file():
            secret = path.read_text().strip()
            if secret:
                return secret

    # Fall back to direct environment variable
    return os.environ.get(var_name)


@router.get("/status")
async def get_auth_status():
    """
    Check if authentication is enabled.
    Returns whether a password is required to access the API.
    Supports Docker secrets via OPEN_NOTEBOOK_PASSWORD_FILE.
    """
    auth_enabled = bool(_get_secret_from_env("OPEN_NOTEBOOK_PASSWORD"))

    return {
        "auth_enabled": auth_enabled,
        "message": "Authentication is required"
        if auth_enabled
        else "Authentication is disabled",
    }