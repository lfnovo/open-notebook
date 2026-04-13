"""
MCP API key validation.

Validates plain-text API keys against SHA-256 hashes stored in the
mcp_api_key table. Rejects revoked and expired keys.
"""

import hashlib
import hmac
from datetime import datetime, timezone

from open_notebook.database.repository import repo_query
from open_notebook.domain.mcp_api_key import McpApiKey


def hash_api_key(plain_key: str) -> str:
    """SHA-256 hash with prefix salt. Deterministic and non-reversible."""
    return hashlib.sha256(f"kbase-mcp:{plain_key}".encode()).hexdigest()


async def validate_api_key(plain_key: str) -> McpApiKey:
    """
    Validate an MCP API key.

    Returns the McpApiKey record if valid.
    Raises ValueError for invalid, expired, or revoked keys.
    """
    key_hash = hash_api_key(plain_key)

    results = await repo_query(
        "SELECT * FROM mcp_api_key WHERE key_hash = $key_hash",
        {"key_hash": key_hash},
    )

    if not results:
        raise ValueError("Invalid API key")

    key_record = McpApiKey(**results[0])

    if key_record.revoked:
        raise ValueError("API key has been revoked")

    if key_record.is_expired():
        raise ValueError("API key has expired")

    return key_record
