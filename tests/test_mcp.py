"""
Tests for Phase 7 — MCP Server.

Covers API key management (create, validate, revoke, expire),
MCP tool dispatching (search_kb, list_workspaces, get_entity),
and hash consistency.

All tests mock DB and service operations — no running database,
MCP server, or API server required.
"""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def plain_key():
    """A deterministic plain API key for tests."""
    return "test_key_abc123_deterministic_value"


@pytest.fixture
def key_hash(plain_key):
    """The expected SHA-256 hash of the plain key."""
    from kbase_mcp.auth import hash_api_key

    return hash_api_key(plain_key)


@pytest.fixture
def mock_mcp_api_key(plain_key, key_hash):
    """A mock McpApiKey record with valid state."""
    from open_notebook.domain.mcp_api_key import McpApiKey

    return McpApiKey(
        id="mcp_api_key:test1",
        key_hash=key_hash,
        user_id="user_clerk_123",
        workspace_ids=["workspace:ws1", "workspace:ws2"],
        label="Test Key",
        expires_at=None,
        revoked=False,
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def expired_mcp_api_key(key_hash):
    """A mock McpApiKey record that is expired."""
    from open_notebook.domain.mcp_api_key import McpApiKey

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    return McpApiKey(
        id="mcp_api_key:expired1",
        key_hash=key_hash,
        user_id="user_clerk_456",
        workspace_ids=["workspace:ws1"],
        label="Expired Key",
        expires_at=past,
        revoked=False,
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def revoked_mcp_api_key(key_hash):
    """A mock McpApiKey record that is revoked."""
    from open_notebook.domain.mcp_api_key import McpApiKey

    return McpApiKey(
        id="mcp_api_key:revoked1",
        key_hash=key_hash,
        user_id="user_clerk_789",
        workspace_ids=["workspace:ws1"],
        label="Revoked Key",
        expires_at=None,
        revoked=True,
        created=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================


class TestSearchKbReturnsResults:
    """search_kb tool -> returns ranked results with content/source_name/confidence."""

    @pytest.mark.asyncio
    async def test_search_kb_returns_results(self, plain_key, mock_mcp_api_key):
        from kbase_mcp.server import search_kb
        from kbase_mcp.auth import hash_api_key

        mock_vector_results = [
            {
                "id": "source_embedding:emb1",
                "content": "Quantum computing primer",
                "source_name": "QC 101",
                "score": 0.95,
            },
            {
                "id": "source_embedding:emb2",
                "content": "Entanglement explained",
                "source_name": "Physics Today",
                "score": 0.82,
            },
        ]

        mock_graph_result = "Quantum computing uses qubits for parallel computation."

        with (
            patch("kbase_mcp.server._ensure_db", new_callable=AsyncMock),
            patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query,
            patch(
                "kbase_mcp.server.GraphService.query",
                new_callable=AsyncMock,
                return_value=mock_graph_result,
            ),
            patch(
                "kbase_mcp.server.vector_search",
                new_callable=AsyncMock,
                return_value=mock_vector_results,
            ),
        ):
            mock_query.return_value = [mock_mcp_api_key.model_dump()]

            results = await search_kb(
                query="quantum computing",
                workspace_ids=["workspace:ws1"],
                api_key=plain_key,
            )

        assert isinstance(results, list)
        assert len(results) > 0
        first = results[0]
        assert "content" in first
        assert "source_name" in first
        assert "confidence" in first


class TestListWorkspacesScopedToKey:
    """list_workspaces -> returns exactly the workspaces scoped in the key."""

    @pytest.mark.asyncio
    async def test_list_workspaces_scoped_to_key(self, plain_key, mock_mcp_api_key):
        from kbase_mcp.server import list_workspaces

        mock_ws1 = MagicMock()
        mock_ws1.id = "workspace:ws1"
        mock_ws1.name = "Research"
        mock_ws1.description = "Research workspace"
        mock_ws1.visibility = "private"

        mock_ws2 = MagicMock()
        mock_ws2.id = "workspace:ws2"
        mock_ws2.name = "Notes"
        mock_ws2.description = "Notes workspace"
        mock_ws2.visibility = "shared"

        with (
            patch("kbase_mcp.server._ensure_db", new_callable=AsyncMock),
            patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query,
            patch(
                "kbase_mcp.server.Workspace.get",
                new_callable=AsyncMock,
                side_effect=[mock_ws1, mock_ws2],
            ),
        ):
            mock_query.return_value = [mock_mcp_api_key.model_dump()]

            results = await list_workspaces(api_key=plain_key)

        assert len(results) == 2
        assert results[0]["id"] == "workspace:ws1"
        assert results[1]["id"] == "workspace:ws2"


class TestGetEntity:
    """get_entity -> returns entity with description/related_entities/sources."""

    @pytest.mark.asyncio
    async def test_get_entity(self, plain_key, mock_mcp_api_key):
        from kbase_mcp.server import get_entity

        graph_response = (
            "Quantum Entanglement is a phenomenon where particles become correlated. "
            "Related to: quantum computing, Bell's theorem. "
            "Sources: Physics Today, Nature."
        )

        with (
            patch("kbase_mcp.server._ensure_db", new_callable=AsyncMock),
            patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query,
            patch(
                "kbase_mcp.server.GraphService.query",
                new_callable=AsyncMock,
                return_value=graph_response,
            ),
        ):
            mock_query.return_value = [mock_mcp_api_key.model_dump()]

            result = await get_entity(
                name="Quantum Entanglement",
                workspace_id="workspace:ws1",
                api_key=plain_key,
            )

        assert "description" in result
        assert result["description"] != ""
        assert "entity_name" in result


class TestGenerateApiKey:
    """POST /mcp-keys -> returns plain_key once, stores key_hash."""

    @pytest.mark.asyncio
    async def test_generate_api_key(self):
        from api.mcp_keys_service import generate_api_key
        from kbase_mcp.auth import hash_api_key

        saved_data = {}

        async def mock_save(self_inner):
            self_inner.id = "mcp_api_key:new1"
            self_inner.created = datetime.now(timezone.utc)
            self_inner.updated = datetime.now(timezone.utc)
            saved_data["key_hash"] = self_inner.key_hash

        with patch(
            "api.mcp_keys_service.McpApiKey.save",
            new=mock_save,
        ):
            result = await generate_api_key(
                user_id="user_clerk_123",
                workspace_ids=["workspace:ws1", "workspace:ws2"],
                label="My Key",
                expires_in_days=None,
            )

        # plain_key is returned
        assert "plain_key" in result
        assert len(result["plain_key"]) > 20

        # stored hash matches
        expected_hash = hash_api_key(result["plain_key"])
        assert saved_data["key_hash"] == expected_hash

        # key record returned
        assert result["id"] == "mcp_api_key:new1"


class TestRevokeApiKey:
    """Create then revoke -> validation fails after revocation."""

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, plain_key, revoked_mcp_api_key):
        from kbase_mcp.auth import validate_api_key

        with patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [revoked_mcp_api_key.model_dump()]

            with pytest.raises(ValueError, match="revoked"):
                await validate_api_key(plain_key)


# =============================================================================
# ERROR CASES
# =============================================================================


class TestInvalidApiKeyReturnsError:
    """validate_api_key with bad key -> raises ValueError."""

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_error(self):
        from kbase_mcp.auth import validate_api_key

        with patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = []

            with pytest.raises(ValueError, match="Invalid"):
                await validate_api_key("completely_wrong_key_value")


class TestExpiredKeyReturnsError:
    """Key with expires_at in the past -> raises ValueError."""

    @pytest.mark.asyncio
    async def test_expired_key_returns_error(self, plain_key, expired_mcp_api_key):
        from kbase_mcp.auth import validate_api_key

        with patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [expired_mcp_api_key.model_dump()]

            with pytest.raises(ValueError, match="expired"):
                await validate_api_key(plain_key)


class TestWorkspaceNotInKeyScope:
    """search_kb with workspace_id not in scope -> raises ValueError."""

    @pytest.mark.asyncio
    async def test_workspace_not_in_key_scope(self, plain_key, mock_mcp_api_key):
        from kbase_mcp.server import search_kb

        with (
            patch("kbase_mcp.server._ensure_db", new_callable=AsyncMock),
            patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query,
        ):
            mock_query.return_value = [mock_mcp_api_key.model_dump()]

            result = await search_kb(
                query="test",
                workspace_ids=["workspace:ws_unauthorized"],
                api_key=plain_key,
            )

        assert isinstance(result, dict)
        assert "error" in result
        assert "not in" in result["error"].lower() or "scope" in result["error"].lower()


# =============================================================================
# ADVERSARIAL CASES
# =============================================================================


class TestApiKeyHashIsConsistent:
    """Same input -> same hash (deterministic)."""

    def test_api_key_hash_is_consistent(self):
        from kbase_mcp.auth import hash_api_key

        key = "my_secret_api_key_value_12345"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 hex digest length


class TestMcpKeyRevokedCannotBeUsed:
    """Revoked key fails validation even if not expired."""

    @pytest.mark.asyncio
    async def test_mcp_key_revoked_cannot_be_used(self, plain_key, revoked_mcp_api_key):
        from kbase_mcp.auth import validate_api_key

        # Key is not expired (expires_at is None) but is revoked
        assert revoked_mcp_api_key.revoked is True
        assert revoked_mcp_api_key.expires_at is None

        with patch("kbase_mcp.auth.repo_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = [revoked_mcp_api_key.model_dump()]

            with pytest.raises(ValueError, match="revoked"):
                await validate_api_key(plain_key)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
