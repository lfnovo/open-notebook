"""
Business logic for MCP API key management.

Handles key generation, listing, and revocation.
Authorization checks happen in the RBAC layer before these
functions are called — service functions assume the caller
is authorized.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from loguru import logger

from kbase_mcp.auth import hash_api_key
from open_notebook.domain.mcp_api_key import McpApiKey


async def generate_api_key(
    user_id: str,
    workspace_ids: List[str],
    label: Optional[str] = None,
    expires_in_days: Optional[int] = None,
) -> dict:
    """
    Generate a new MCP API key for a user.

    Returns a dict with the record fields and ``plain_key`` — the
    plain-text key value that is returned exactly once.
    """
    plain_key = secrets.token_urlsafe(32)
    key_hash = hash_api_key(plain_key)

    expires_at: Optional[str] = None
    if expires_in_days is not None:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        ).isoformat()

    key_record = McpApiKey(
        key_hash=key_hash,
        user_id=user_id,
        workspace_ids=workspace_ids,
        label=label,
        expires_at=expires_at,
    )
    await key_record.save()

    logger.info(f"MCP API key created for user {user_id} (id={key_record.id})")

    return {
        "id": str(key_record.id),
        "label": key_record.label,
        "workspace_ids": key_record.workspace_ids,
        "created": str(key_record.created),
        "expires_at": key_record.expires_at,
        "revoked": key_record.revoked,
        "plain_key": plain_key,
    }


async def list_api_keys(user_id: str) -> List[dict]:
    """List all MCP API keys for a user (never includes plain key)."""
    keys = await McpApiKey.get_by_user(user_id)
    return [
        {
            "id": str(k.id),
            "label": k.label,
            "workspace_ids": k.workspace_ids,
            "created": str(k.created),
            "expires_at": k.expires_at,
            "revoked": k.revoked,
        }
        for k in keys
    ]


async def revoke_api_key(key_id: str, user_id: str) -> bool:
    """
    Revoke an MCP API key.

    Returns True if the key was found and revoked.
    Raises ValueError if the key does not belong to the user.
    """
    key_record = await McpApiKey.get(key_id)

    if key_record.user_id != user_id:
        raise ValueError("API key does not belong to this user")

    key_record.revoked = True
    await key_record.save()

    logger.info(f"MCP API key {key_id} revoked by user {user_id}")
    return True
