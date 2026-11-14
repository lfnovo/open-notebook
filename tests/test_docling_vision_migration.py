"""Migration 28 adds the Docling vision endpoint fields to Settings (#1561).

Applied to an embedded SurrealDB, as in test_text_search_limit.py. On an
existing settings record, 28 backfills the three fields as NULL, which the
SurrealDB client reads back as None, without touching the other settings or
overwriting saved values; 28_down removes them again.
"""

from typing import Any

import pytest
from surrealdb import AsyncSurreal

from open_notebook.database.async_migrate import AsyncMigration, AsyncMigrationManager

FIELDS = ("docling_vision_url", "docling_vision_model", "docling_vision_prompt")
RECORD = "open_notebook:content_settings"

#: A content_settings record as a version-27 install saved it.
PRE_28_SETTINGS = (
    f"UPSERT {RECORD} CONTENT {{"
    " default_content_processing_engine_doc: 'docling',"
    " default_content_processing_engine_url: 'auto',"
    " default_embedding_option: 'ask', auto_delete_files: 'yes',"
    " docling_ocr: true, docling_formulas: false, docling_vision: true,"
    " youtube_preferred_languages: ['en'] };"
)


def migration_28() -> tuple[AsyncMigration, AsyncMigration]:
    manager = AsyncMigrationManager()
    # Migration 28 is index 27.
    up, down = manager.up_migrations[27], manager.down_migrations[27]
    assert "docling_vision_url" in up.sql and "UNSET" in down.sql
    return up, down


async def settings_row(db: Any) -> dict[str, Any]:
    row = await db.query(f"SELECT * FROM ONLY {RECORD};")
    assert isinstance(row, dict), row
    return row


def assert_other_settings_kept(row: dict[str, Any]) -> None:
    assert row["docling_vision"] is True
    assert row["default_content_processing_engine_doc"] == "docling"
    assert row["youtube_preferred_languages"] == ["en"]


@pytest.mark.asyncio
async def test_migration_28_backfills_null_on_existing_settings() -> None:
    up, _ = migration_28()
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("migration_28", "backfill")
        await db.query(PRE_28_SETTINGS)

        await db.query(up.sql)

        row = await settings_row(db)
        for field in FIELDS:
            # Present as NULL (not missing), which the client returns as None.
            assert field in row, row
            assert row[field] is None, row
        assert_other_settings_kept(row)


@pytest.mark.asyncio
async def test_migration_28_keeps_saved_values_when_run_again() -> None:
    up, _ = migration_28()
    saved = {
        "docling_vision_url": "http://192.168.1.20:1234/v1/chat/completions",
        "docling_vision_model": "qwen2.5-vl-7b",
        "docling_vision_prompt": "Describe the chart.",
    }
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("migration_28", "rerun")
        await db.query(PRE_28_SETTINGS)
        await db.query(up.sql)
        await db.query(f"UPDATE {RECORD} MERGE $saved;", {"saved": saved})

        await db.query(up.sql)

        row = await settings_row(db)
        assert {field: row[field] for field in FIELDS} == saved


@pytest.mark.asyncio
async def test_migration_28_down_removes_the_fields() -> None:
    up, down = migration_28()
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("migration_28", "rollback")
        await db.query(PRE_28_SETTINGS)
        await db.query(up.sql)
        await db.query(
            f"UPDATE {RECORD} SET docling_vision_url = $url;",
            {"url": "http://192.168.1.20:1234/v1/chat/completions"},
        )

        await db.query(down.sql)

        row = await settings_row(db)
        for field in FIELDS:
            assert field not in row, row
        assert_other_settings_kept(row)

        # Upgrading again after a rollback backfills NULL again.
        await db.query(up.sql)
        row = await settings_row(db)
        assert all(field in row and row[field] is None for field in FIELDS), row


@pytest.mark.asyncio
async def test_migration_28_creates_no_record_on_a_fresh_database() -> None:
    up, _ = migration_28()
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("migration_28", "fresh")

        await db.query(up.sql)

        # No settings record yet: the ContentSettings defaults (None) apply.
        assert not await db.query(f"SELECT * FROM {RECORD};")
