import asyncio
import os
import time
import tomllib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from loguru import logger

from open_notebook.database.repository import repo_query
from open_notebook.utils.version_utils import (
    compare_versions,
    get_version_from_github,
)

router = APIRouter()

# In-memory cache for version check results
_version_cache: dict = {
    "latest_version": None,
    "has_update": False,
    "timestamp": 0,
    "check_failed": False,
}


def get_version() -> str:
    """Read version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
            return pyproject.get("project", {}).get("version", "unknown")
    except Exception as e:
        logger.warning(f"Could not read version from pyproject.toml: {e}")
        return "unknown"


def get_latest_version_cached(current_version: str) -> tuple[Optional[str], bool]:
    """
    Check for the latest version from GitHub with caching.

    Returns:
        tuple: (latest_version, has_update)
        - latest_version: str or None if check failed
        - has_update: bool indicating if update is available
    """
    global _version_cache

    # Use cache if available (lives for entire API process lifetime)
    if _version_cache["timestamp"] > 0:
        logger.debug("Using cached version check result")
        return _version_cache["latest_version"], _version_cache["has_update"]

    # Perform version check with strict error handling
    try:
        logger.info("Checking for latest version from GitHub...")

        # Fetch latest version from GitHub with 10-second timeout
        latest_version = get_version_from_github(
            "https://github.com/lfnovo/open-notebook",
            "main"
        )

        logger.info(f"Latest version from GitHub: {latest_version}, Current version: {current_version}")

        # Compare versions
        has_update = compare_versions(current_version, latest_version) < 0

        # Cache the result
        _version_cache["latest_version"] = latest_version
        _version_cache["has_update"] = has_update
        _version_cache["timestamp"] = time.time()
        _version_cache["check_failed"] = False

        logger.info(f"Version check complete. Update available: {has_update}")

        return latest_version, has_update

    except Exception as e:
        logger.warning(f"Version check failed: {e}")

        # Cache the failure to avoid repeated attempts
        _version_cache["latest_version"] = None
        _version_cache["has_update"] = False
        _version_cache["timestamp"] = time.time()
        _version_cache["check_failed"] = True

        return None, False


async def check_database_health() -> dict:
    """
    Check if database is reachable using a lightweight query.

    Returns:
        dict with 'status' ("online" | "offline") and optional 'error'
    """
    try:
        # 2-second timeout for database health check
        result = await asyncio.wait_for(
            repo_query("RETURN 1"),
            timeout=2.0
        )
        if result:
            return {"status": "online"}
        return {"status": "offline", "error": "Empty result"}
    except asyncio.TimeoutError:
        logger.warning("Database health check timed out after 2 seconds")
        return {"status": "offline", "error": "Health check timeout"}
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return {"status": "offline", "error": str(e)}


@router.get("/config")
async def get_config(request: Request):
    """
    Get frontend configuration.
    This endpoint provides runtime configuration to the frontend,
    allowing the same Docker image to work in different environments.

    Auto-detection logic:
    1. If API_URL env var is set, use it (explicit override)
    2. Otherwise, detect from incoming HTTP request (zero-config)

    Also checks for version updates from GitHub (with caching and error handling).
    """
    # Check if API_URL is explicitly set
    env_api_url = os.getenv("API_URL")

    if env_api_url:
        logger.debug(f"Using API_URL from environment: {env_api_url}")
        api_url = env_api_url
    else:
        # Auto-detect from request
        # Get the protocol (http or https)
        # Check X-Forwarded-Proto first (for reverse proxies), then fallback to request scheme
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)

        # Get the host (includes port if non-standard)
        host = request.headers.get("host", f"{request.client.host}:5055")

        # Construct the API URL
        api_url = f"{proto}://{host}"
        logger.info(f"Auto-detected API URL from request: {api_url} (proto={proto}, host={host})")

    # Get current version
    current_version = get_version()

    # Check for updates (with caching and error handling)
    # This MUST NOT break the endpoint - wrapped in try-except as extra safety
    latest_version = None
    has_update = False

    try:
        latest_version, has_update = get_latest_version_cached(current_version)
    except Exception as e:
        # Extra safety: ensure version check never breaks the config endpoint
        logger.error(f"Unexpected error during version check: {e}")

    # Check database health
    db_health = await check_database_health()
    db_status = db_health["status"]

    if db_status == "offline":
        logger.warning(f"Database offline: {db_health.get('error', 'Unknown error')}")

    return {
        "apiUrl": api_url,
        "version": current_version,
        "latestVersion": latest_version,
        "hasUpdate": has_update,
        "dbStatus": db_status,
    }
