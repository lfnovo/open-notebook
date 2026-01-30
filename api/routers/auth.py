"""
Authentication router for Open Notebook API.
Provides endpoints to check authentication status.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

# Default password for development/quick-start
DEFAULT_PASSWORD = "open-notebook-change-me"


def _get_secret_from_env(var_name: str) -> Optional[str]:
    """Get a secret supporting Docker secrets pattern (_FILE suffix)."""
    file_path = os.environ.get(f"{var_name}_FILE")
    if file_path:
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                secret = path.read_text().strip()
                if secret:
                    return secret
        except Exception:
            # Failed to read from file, fall back to environment variable
            pass
    return os.environ.get(var_name)


@router.get("/status")
async def get_auth_status():
    """
    Check if authentication is enabled.
    Returns whether a password is required to access the API.
    Supports Docker secrets via OPEN_NOTEBOOK_PASSWORD_FILE.
    Always returns auth_enabled=true (default password if not configured).
    """
    custom_password = _get_secret_from_env("OPEN_NOTEBOOK_PASSWORD")
    using_default = not custom_password

    return {
        "auth_enabled": True,  # Always enabled (default password if not set)
        "using_default_password": using_default,
        "message": "Authentication is required"
        + (" (using default password - change for production!)" if using_default else ""),
    }
