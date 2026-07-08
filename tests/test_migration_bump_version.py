"""
Tests for the migration version-bump idempotency fix
(open_notebook/database/async_migrate.py: bump_version()).

bump_version() used to CREATE a new _sbl_migrations record for the computed
next version. Two replicas racing to bump to the same version (e.g. both
starting up together) would have the second CREATE fail with "already
exists", crash-looping that replica. Switching to UPSERT makes a duplicate
bump to the same version a harmless no-op instead of an error - verified
directly against a live embedded SurrealDB instance (see session notes);
these are the corresponding fast unit-level regression tests.
"""

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.database.async_migrate import bump_version


class TestBumpVersionUsesUpsert:
    @pytest.mark.asyncio
    async def test_query_uses_upsert_not_create(self):
        with (
            patch(
                "open_notebook.database.async_migrate.get_latest_version",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "open_notebook.database.async_migrate.repo_query",
                new=AsyncMock(return_value=[]),
            ) as mock_query,
        ):
            await bump_version()

        query_str = mock_query.call_args.args[0]
        assert "UPSERT" in query_str
        assert "CREATE" not in query_str

    @pytest.mark.asyncio
    async def test_bumps_to_current_plus_one(self):
        with (
            patch(
                "open_notebook.database.async_migrate.get_latest_version",
                new=AsyncMock(return_value=4),
            ),
            patch(
                "open_notebook.database.async_migrate.repo_query",
                new=AsyncMock(return_value=[]),
            ) as mock_query,
        ):
            await bump_version()

        bound_vars = mock_query.call_args.args[1]
        assert bound_vars["version"] == 5

    @pytest.mark.asyncio
    async def test_duplicate_bump_does_not_raise(self):
        """Simulates a second replica bumping to a version that already has
        a row: UPSERT succeeds (unlike the old CREATE, which would raise)."""
        with (
            patch(
                "open_notebook.database.async_migrate.get_latest_version",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "open_notebook.database.async_migrate.repo_query",
                new=AsyncMock(return_value=[{"id": "_sbl_migrations:1", "version": 1}]),
            ),
        ):
            # Two callers both computing new_version=1 - neither should raise.
            await bump_version()
            await bump_version()
