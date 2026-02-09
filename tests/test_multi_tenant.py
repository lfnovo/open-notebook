"""
Unit tests for the multi-tenant feature.

Tests cover:
1. user_context ContextVar isolation
2. _get_database_name() dynamic routing
3. ProxyAuthMiddleware header parsing and auth
4. ensure_user_migrated() caching
5. Integration: FastAPI TestClient with X-Forwarded-User header
6. Data isolation between users via separate databases
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.user_context import current_user


# ============================================================================
# TEST SUITE 1: ContextVar Behavior
# ============================================================================


class TestUserContext:
    """Test suite for current_user ContextVar."""

    def test_default_is_empty_string(self):
        """Default value should be empty string (single-user mode)."""
        assert current_user.get("") == ""

    def test_set_and_get(self):
        """Setting and getting the contextvar works."""
        token = current_user.set("alice")
        try:
            assert current_user.get() == "alice"
        finally:
            current_user.reset(token)

    def test_reset_restores_default(self):
        """Resetting the token restores the previous value."""
        assert current_user.get("") == ""
        token = current_user.set("bob")
        assert current_user.get() == "bob"
        current_user.reset(token)
        assert current_user.get("") == ""

    def test_nested_set_and_reset(self):
        """Nested set/reset works correctly (simulates nested middleware)."""
        token1 = current_user.set("alice")
        assert current_user.get() == "alice"

        token2 = current_user.set("bob")
        assert current_user.get() == "bob"

        current_user.reset(token2)
        assert current_user.get() == "alice"

        current_user.reset(token1)
        assert current_user.get("") == ""


# ============================================================================
# TEST SUITE 2: Database Name Routing
# ============================================================================


class TestGetDatabaseName:
    """Test suite for _get_database_name() dynamic routing."""

    def test_returns_env_var_when_no_user(self):
        """Without a user set, falls back to SURREAL_DATABASE env var."""
        from open_notebook.database.repository import _get_database_name

        # Ensure contextvar is empty
        assert current_user.get("") == ""
        with patch.dict(os.environ, {"SURREAL_DATABASE": "my_default_db"}):
            assert _get_database_name() == "my_default_db"

    def test_returns_default_when_no_user_no_env(self):
        """Without user or env var, falls back to 'open_notebook'."""
        from open_notebook.database.repository import _get_database_name

        assert current_user.get("") == ""
        with patch.dict(os.environ, {}, clear=False):
            # Remove SURREAL_DATABASE if set
            env = os.environ.copy()
            env.pop("SURREAL_DATABASE", None)
            with patch.dict(os.environ, env, clear=True):
                result = _get_database_name()
                assert result == "open_notebook"

    def test_returns_user_prefixed_name(self):
        """With user set, returns 'user_<sanitized_name>_<hash>'."""
        from open_notebook.database.repository import _get_database_name

        token = current_user.set("alice")
        try:
            assert _get_database_name() == "user_alice_2bd806c97f0e"
        finally:
            current_user.reset(token)

    def test_sanitizes_email_user(self):
        """Email addresses are sanitized (@ and . become _) with hash suffix."""
        from open_notebook.database.repository import _get_database_name

        token = current_user.set("alice@company.com")
        try:
            assert _get_database_name() == "user_alice_company_com_22c9943ba6fd"
        finally:
            current_user.reset(token)

    def test_sanitizes_special_characters(self):
        """Special characters are sanitized to underscores with hash suffix."""
        from open_notebook.database.repository import _get_database_name

        token = current_user.set("user-name/with spaces!")
        try:
            result = _get_database_name()
            assert result == "user_user_name_with_spaces__fc4997ad11fa"
            # Should only contain alphanumeric and underscore
            assert all(c.isalnum() or c == "_" for c in result)
        finally:
            current_user.reset(token)

    def test_no_collision_between_similar_names(self):
        """Users with same sanitized form but different original get different DBs."""
        from open_notebook.database.repository import _get_database_name

        token1 = current_user.set("alice.bob@co.com")
        try:
            db1 = _get_database_name()
        finally:
            current_user.reset(token1)

        token2 = current_user.set("alice_bob@co_com")
        try:
            db2 = _get_database_name()
        finally:
            current_user.reset(token2)

        assert db1 != db2, f"Collision: {db1} == {db2}"

    def test_ignores_env_var_when_user_set(self):
        """When a user is set, env var SURREAL_DATABASE is ignored."""
        from open_notebook.database.repository import _get_database_name

        token = current_user.set("bob")
        try:
            with patch.dict(os.environ, {"SURREAL_DATABASE": "should_not_use"}):
                assert _get_database_name() == "user_bob_81b637d8fcd2"
        finally:
            current_user.reset(token)


# ============================================================================
# TEST SUITE 3: ProxyAuthMiddleware
# ============================================================================


class TestProxyAuthMiddleware:
    """Test suite for ProxyAuthMiddleware header parsing and auth enforcement."""

    @pytest.fixture
    def multi_tenant_client(self):
        """Create a test client with MULTI_TENANT_MODE enabled."""
        # Set env var BEFORE importing the app
        with patch.dict(os.environ, {"MULTI_TENANT_MODE": "true"}):
            # Force re-import to pick up the new env var
            import importlib
            import api.main

            importlib.reload(api.main)
            yield TestClient(api.main.app)

        # Reload again to restore original state
        with patch.dict(os.environ, {"MULTI_TENANT_MODE": ""}):
            importlib.reload(api.main)

    def test_missing_header_returns_401(self, multi_tenant_client):
        """Request without X-Forwarded-User header should get 401."""
        response = multi_tenant_client.get("/api/notebooks")
        assert response.status_code == 401
        assert "X-Forwarded-User" in response.json()["detail"]

    def test_empty_header_returns_401(self, multi_tenant_client):
        """Request with empty X-Forwarded-User header should get 401."""
        response = multi_tenant_client.get(
            "/api/notebooks",
            headers={"X-Forwarded-User": ""},
        )
        assert response.status_code == 401

    def test_whitespace_header_returns_401(self, multi_tenant_client):
        """Request with whitespace-only header should get 401."""
        response = multi_tenant_client.get(
            "/api/notebooks",
            headers={"X-Forwarded-User": "   "},
        )
        assert response.status_code == 401

    def test_health_excluded_no_header_needed(self, multi_tenant_client):
        """Health endpoint is excluded — no header needed."""
        response = multi_tenant_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_excluded_no_header_needed(self, multi_tenant_client):
        """Root endpoint is excluded — no header needed."""
        response = multi_tenant_client.get("/")
        assert response.status_code == 200

    def test_auth_status_excluded(self, multi_tenant_client):
        """Auth status endpoint is excluded — no header needed."""
        response = multi_tenant_client.get("/api/auth/status")
        assert response.status_code == 200

    @patch("api.auth.ensure_user_migrated", new_callable=AsyncMock)
    @patch("open_notebook.database.repository.repo_query", new_callable=AsyncMock)
    def test_valid_header_passes_through(
        self, mock_repo_query, mock_migrate, multi_tenant_client
    ):
        """Request with valid X-Forwarded-User header should pass through."""
        mock_repo_query.return_value = []
        mock_migrate.return_value = None

        response = multi_tenant_client.get(
            "/api/notebooks",
            headers={"X-Forwarded-User": "alice"},
        )
        # Should not be 401 (may be 200 or 500 depending on DB, but NOT 401)
        assert response.status_code != 401

    def test_options_preflight_passes_without_header(self, multi_tenant_client):
        """CORS preflight (OPTIONS) should pass without user header."""
        response = multi_tenant_client.options("/api/notebooks")
        assert response.status_code != 401


# ============================================================================
# TEST SUITE 4: Migration Caching
# ============================================================================


class TestEnsureUserMigrated:
    """Test suite for ensure_user_migrated() caching logic."""

    @pytest.mark.asyncio
    @patch("api.auth.AsyncMigrationManager")
    async def test_first_call_runs_migration(self, MockManager):
        """First call for a user should check and run migrations."""
        from api.auth import _migrated_users, ensure_user_migrated

        # Clear cache
        _migrated_users.discard("test_user_migration_1")

        manager_instance = MockManager.return_value
        manager_instance.needs_migration = AsyncMock(return_value=True)
        manager_instance.run_migration_up = AsyncMock()

        # Set contextvar so db_connection points to this user's DB
        token = current_user.set("test_user_migration_1")
        try:
            await ensure_user_migrated("test_user_migration_1")
            manager_instance.needs_migration.assert_called_once()
            manager_instance.run_migration_up.assert_called_once()
        finally:
            current_user.reset(token)
            _migrated_users.discard("test_user_migration_1")

    @pytest.mark.asyncio
    @patch("api.auth.AsyncMigrationManager")
    async def test_second_call_skips_migration(self, MockManager):
        """Second call for same user should skip migration (cached)."""
        from api.auth import _migrated_users, ensure_user_migrated

        # Clear and pre-populate cache
        _migrated_users.discard("test_user_migration_2")

        manager_instance = MockManager.return_value
        manager_instance.needs_migration = AsyncMock(return_value=True)
        manager_instance.run_migration_up = AsyncMock()

        token = current_user.set("test_user_migration_2")
        try:
            # First call — runs migration
            await ensure_user_migrated("test_user_migration_2")
            assert manager_instance.needs_migration.call_count == 1

            # Second call — should skip
            await ensure_user_migrated("test_user_migration_2")
            assert manager_instance.needs_migration.call_count == 1  # still 1
        finally:
            current_user.reset(token)
            _migrated_users.discard("test_user_migration_2")

    @pytest.mark.asyncio
    @patch("api.auth.AsyncMigrationManager")
    async def test_different_users_both_migrate(self, MockManager):
        """Different users each get their own migration check."""
        from api.auth import _migrated_users, ensure_user_migrated

        _migrated_users.discard("user_a_test")
        _migrated_users.discard("user_b_test")

        manager_instance = MockManager.return_value
        manager_instance.needs_migration = AsyncMock(return_value=False)
        manager_instance.run_migration_up = AsyncMock()

        token = current_user.set("user_a_test")
        try:
            await ensure_user_migrated("user_a_test")
        finally:
            current_user.reset(token)

        token = current_user.set("user_b_test")
        try:
            await ensure_user_migrated("user_b_test")
        finally:
            current_user.reset(token)

        # needs_migration called twice — once per user
        assert manager_instance.needs_migration.call_count == 2
        _migrated_users.discard("user_a_test")
        _migrated_users.discard("user_b_test")

    @pytest.mark.asyncio
    @patch("api.auth.AsyncMigrationManager")
    async def test_no_migration_needed_still_cached(self, MockManager):
        """Even if no migration needed, user is cached to avoid re-checking."""
        from api.auth import _migrated_users, ensure_user_migrated

        _migrated_users.discard("test_user_no_mig")

        manager_instance = MockManager.return_value
        manager_instance.needs_migration = AsyncMock(return_value=False)

        token = current_user.set("test_user_no_mig")
        try:
            await ensure_user_migrated("test_user_no_mig")
            assert "test_user_no_mig" in _migrated_users
            manager_instance.run_migration_up.assert_not_called()
        finally:
            current_user.reset(token)
            _migrated_users.discard("test_user_no_mig")


# ============================================================================
# TEST SUITE 5: db_connection() Uses Correct Database
# ============================================================================


class TestDbConnectionRouting:
    """Test that db_connection() connects to the right database per user."""

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.AsyncSurreal")
    async def test_single_user_mode_uses_env(self, MockSurreal):
        """Without user contextvar, db.use() gets env var database."""
        from open_notebook.database.repository import db_connection

        mock_db = AsyncMock()
        MockSurreal.return_value = mock_db

        assert current_user.get("") == ""

        with patch.dict(
            os.environ,
            {
                "SURREAL_NAMESPACE": "test_ns",
                "SURREAL_DATABASE": "test_db",
                "SURREAL_USER": "root",
                "SURREAL_PASSWORD": "root",
            },
        ):
            async with db_connection() as conn:
                pass

        mock_db.use.assert_called_once_with("test_ns", "test_db")

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.AsyncSurreal")
    async def test_multi_tenant_uses_user_database(self, MockSurreal):
        """With user contextvar set, db.use() gets per-user database name."""
        from open_notebook.database.repository import db_connection

        mock_db = AsyncMock()
        MockSurreal.return_value = mock_db

        token = current_user.set("alice")
        try:
            with patch.dict(
                os.environ,
                {
                    "SURREAL_NAMESPACE": "test_ns",
                    "SURREAL_DATABASE": "should_not_use",
                    "SURREAL_USER": "root",
                    "SURREAL_PASSWORD": "root",
                },
            ):
                async with db_connection() as conn:
                    pass

            mock_db.use.assert_called_once_with("test_ns", "user_alice_2bd806c97f0e")
        finally:
            current_user.reset(token)

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.AsyncSurreal")
    async def test_different_users_get_different_databases(self, MockSurreal):
        """Two requests with different users connect to different databases."""
        from open_notebook.database.repository import db_connection

        mock_db = AsyncMock()
        MockSurreal.return_value = mock_db

        env_vars = {
            "SURREAL_NAMESPACE": "test_ns",
            "SURREAL_DATABASE": "default",
            "SURREAL_USER": "root",
            "SURREAL_PASSWORD": "root",
        }

        # Alice's request
        token1 = current_user.set("alice")
        try:
            with patch.dict(os.environ, env_vars):
                async with db_connection() as conn:
                    pass
            alice_call = mock_db.use.call_args_list[-1]
            assert alice_call[0] == ("test_ns", "user_alice_2bd806c97f0e")
        finally:
            current_user.reset(token1)

        # Bob's request
        token2 = current_user.set("bob")
        try:
            with patch.dict(os.environ, env_vars):
                async with db_connection() as conn:
                    pass
            bob_call = mock_db.use.call_args_list[-1]
            assert bob_call[0] == ("test_ns", "user_bob_81b637d8fcd2")
        finally:
            current_user.reset(token2)


# ============================================================================
# TEST SUITE 6: Backward Compatibility (Single-User Mode)
# ============================================================================


class TestBackwardCompatibility:
    """Test that single-user mode (MULTI_TENANT_MODE not set) still works."""

    @pytest.fixture
    def single_user_client(self):
        """Create a test client in single-user mode (default)."""
        with patch.dict(os.environ, {"MULTI_TENANT_MODE": ""}):
            import importlib
            import api.main

            importlib.reload(api.main)
            yield TestClient(api.main.app)

        # Restore
        importlib.reload(api.main)

    def test_no_header_needed_when_no_password(self, single_user_client):
        """In single-user mode without password, requests pass through."""
        response = single_user_client.get("/health")
        assert response.status_code == 200

    def test_root_works(self, single_user_client):
        """Root endpoint works in single-user mode."""
        response = single_user_client.get("/")
        assert response.status_code == 200
        assert "running" in response.json()["message"]
