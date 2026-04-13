"""
McpApiKey domain model.

Represents an API key that grants MCP clients access to
scoped workspaces. Keys are stored as SHA-256 hashes;
the plain-text value is returned exactly once at creation time.
"""

import hashlib
from datetime import datetime, timezone
from typing import ClassVar, List, Optional, Type, TypeVar

from loguru import logger
from pydantic import field_validator

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError

T = TypeVar("T", bound="McpApiKey")


class McpApiKey(ObjectModel):
    table_name: ClassVar[str] = "mcp_api_key"
    nullable_fields: ClassVar[set[str]] = {"expires_at", "label"}

    key_hash: str
    user_id: str
    workspace_ids: List[str]
    label: Optional[str] = None
    expires_at: Optional[str] = None  # ISO timestamp, None = never expires
    revoked: bool = False

    @field_validator("user_id")
    @classmethod
    def user_id_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise InvalidInputError("User ID cannot be empty")
        return value

    @field_validator("workspace_ids")
    @classmethod
    def workspace_ids_must_be_list_of_strings(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list):
            raise InvalidInputError("workspace_ids must be a list")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise InvalidInputError("Each workspace_id must be a non-empty string")
        return value

    def validate_key(self, plain_key: str) -> bool:
        """Constant-time comparison of a plain key against the stored hash."""
        candidate = hashlib.sha256(f"kbase-mcp:{plain_key}".encode()).hexdigest()
        return hmac_compare(candidate, self.key_hash)

    def is_expired(self) -> bool:
        """Return True if the key has a set expiration that is in the past."""
        if self.expires_at is None:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= exp
        except (ValueError, TypeError):
            return False

    @classmethod
    async def get_by_user(cls: Type[T], user_id: str) -> List[T]:
        """Return all MCP API keys belonging to a user."""
        if not user_id:
            raise InvalidInputError("User ID cannot be empty")
        try:
            results = await repo_query(
                "SELECT * FROM mcp_api_key WHERE user_id = $user_id",
                {"user_id": user_id},
            )
            return [cls(**row) for row in results] if results else []
        except Exception as error:
            logger.error(f"Error fetching MCP keys for user {user_id}: {error}")
            raise DatabaseOperationError(error)


def hmac_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    import hmac as _hmac

    return _hmac.compare_digest(a.encode(), b.encode())
