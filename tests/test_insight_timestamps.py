"""Tests for #1045 - source_insight timestamps.

Two layers:
1. New source_insight records get created/updated stamped at creation time
   (migration 19 defines the fields with time::now() defaults, mirroring the
   source/note/notebook tables - insight creation happens via a raw CREATE in
   commands/embedding_commands.py, not ObjectModel.save()).
2. The API serializes missing timestamps as null (never the string "None")
   and present timestamps as ISO strings.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Source, SourceInsight

MIGRATIONS_DIR = (
    Path(__file__).parent.parent / "open_notebook" / "database" / "migrations"
)


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


# ============================================================================
# Layer 1: new insights get created/updated stamped at creation time
# ============================================================================


class TestInsightTimestampStamping:
    """source_insight rows must be stamped with created/updated on creation.

    Insights are created by a raw `CREATE source_insight CONTENT {...}` query
    (create_insight command), and source_insight is SCHEMAFULL - so the stamp
    has to come from the schema (DEFINE FIELD ... DEFAULT time::now()), exactly
    like the source, note and notebook tables. These tests guard the two
    failure modes: the migration losing its field definitions, and the
    migration file not being registered in the hard-coded manager list.
    """

    def test_migration_defines_timestamp_fields(self):
        sql = (MIGRATIONS_DIR / "19.surrealql").read_text()
        assert (
            "DEFINE FIELD IF NOT EXISTS created ON source_insight "
            "DEFAULT time::now() VALUE $before OR time::now()" in sql
        )
        assert (
            "DEFINE FIELD IF NOT EXISTS updated ON source_insight "
            "DEFAULT time::now() VALUE time::now()" in sql
        )

    def test_migration_down_removes_timestamp_fields(self):
        sql = (MIGRATIONS_DIR / "19_down.surrealql").read_text()
        assert "REMOVE FIELD IF EXISTS created ON TABLE source_insight" in sql
        assert "REMOVE FIELD IF EXISTS updated ON TABLE source_insight" in sql

    def test_migration_is_registered_in_manager(self):
        """Migrations are hard-coded in AsyncMigrationManager, not discovered."""
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        # up and down lists must stay in sync and include migration 19
        assert len(manager.up_migrations) >= 19
        assert len(manager.up_migrations) == len(manager.down_migrations)
        assert "created ON source_insight" in manager.up_migrations[18].sql
        assert "updated ON source_insight" in manager.up_migrations[18].sql


# ============================================================================
# Layer 2: API serialization - null when absent, ISO string when present
# ============================================================================


def _insight(created=None, updated=None) -> SourceInsight:
    return SourceInsight(
        id="source_insight:abc",
        insight_type="summary",
        content="Some insight",
        created=created,
        updated=updated,
    )


def _source() -> Source:
    return Source(id="source:xyz", title="A source")


class TestInsightTimestampSerialization:
    """API must emit null for missing timestamps and ISO strings otherwise."""

    @patch("api.routers.insights.SourceInsight.get", new_callable=AsyncMock)
    def test_get_insight_absent_timestamps_are_null(self, mock_get, client):
        insight = _insight()
        mock_get.return_value = insight

        with patch.object(
            SourceInsight, "get_source", new_callable=AsyncMock
        ) as mock_source:
            mock_source.return_value = _source()
            response = client.get("/api/insights/source_insight:abc")

        assert response.status_code == 200
        body = response.json()
        assert body["created"] is None
        assert body["updated"] is None

    @patch("api.routers.insights.SourceInsight.get", new_callable=AsyncMock)
    def test_get_insight_present_timestamps_are_iso(self, mock_get, client):
        ts = datetime(2026, 7, 11, 12, 30, 45, tzinfo=timezone.utc)
        mock_get.return_value = _insight(created=ts, updated=ts)

        with patch.object(
            SourceInsight, "get_source", new_callable=AsyncMock
        ) as mock_source:
            mock_source.return_value = _source()
            response = client.get("/api/insights/source_insight:abc")

        assert response.status_code == 200
        body = response.json()
        assert body["created"] == "2026-07-11T12:30:45+00:00"
        assert body["updated"] == "2026-07-11T12:30:45+00:00"

    @patch("api.routers.sources.Source.get", new_callable=AsyncMock)
    def test_list_source_insights_never_serializes_the_string_none(
        self, mock_get, client
    ):
        ts = datetime(2026, 7, 11, 12, 30, 45, tzinfo=timezone.utc)
        source = _source()
        mock_get.return_value = source

        with patch.object(
            Source, "get_insights", new_callable=AsyncMock
        ) as mock_insights:
            mock_insights.return_value = [
                _insight(),  # legacy row without timestamps
                _insight(created=ts, updated=ts),  # stamped row
            ]
            response = client.get("/api/sources/source:xyz/insights")

        assert response.status_code == 200
        body = response.json()
        assert body[0]["created"] is None
        assert body[0]["updated"] is None
        assert body[1]["created"] == "2026-07-11T12:30:45+00:00"
        assert body[1]["updated"] == "2026-07-11T12:30:45+00:00"
        for row in body:
            assert row["created"] != "None"
            assert row["updated"] != "None"
