"""View stamps must not move notebook or source updated (#1398)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from surrealdb import AsyncSurreal, RecordID

from open_notebook.database.async_migrate import AsyncMigrationManager

MIGRATIONS = Path("open_notebook/database/migrations")
PINNED = datetime(2020, 1, 1, tzinfo=timezone.utc)
TABLES = (("notebook", "n"), ("source", "s"))


def record(value: object) -> dict[str, object]:
    assert isinstance(value, list)
    assert len(value) == 1
    row = value[0]
    assert isinstance(row, dict)
    return row


def test_manager_registers_migration_26() -> None:
    """Migrations are hard-coded in AsyncMigrationManager, not discovered."""
    assert (MIGRATIONS / "26.surrealql").is_file()
    assert (MIGRATIONS / "26_down.surrealql").is_file()

    manager = AsyncMigrationManager()
    assert len(manager.up_migrations) >= 26
    assert len(manager.up_migrations) == len(manager.down_migrations)
    for table, _ in TABLES:
        assert (
            f"DEFINE FIELD OVERWRITE updated ON TABLE {table} DEFAULT time::now();"
            in manager.up_migrations[25].sql
        )
        assert (
            f"DEFINE FIELD OVERWRITE updated ON TABLE {table} "
            "DEFAULT time::now() VALUE time::now();" in manager.down_migrations[25].sql
        )


@pytest.mark.asyncio
async def test_view_stamp_does_not_bump_updated() -> None:
    """UPDATE last_viewed_at leaves a pinned updated instant in place, and
    rolling migration 26 back restores the bump on every write."""
    manager = AsyncMigrationManager()
    async with AsyncSurreal("mem://") as db:
        await db.use("view_regression", "updated")

        async def stamp_view(table: str, key: str) -> dict[str, object]:
            """Pin updated, then write only last_viewed_at, as a view does."""
            await db.query(
                f'UPDATE {table}:{key} SET updated = d"2020-01-01T00:00:00Z";'
            )
            return record(
                await db.query(
                    f"UPDATE ${table}_id SET last_viewed_at = time::now();",
                    {f"{table}_id": RecordID(table, key)},
                )
            )

        await db.query((MIGRATIONS / "1.surrealql").read_text())
        await db.query(manager.up_migrations[17].sql)
        await db.query("CREATE notebook:n SET name = 'Notebook';")
        await db.query("CREATE source:s SET title = 'Source';")

        await db.query(manager.up_migrations[25].sql)
        for table, key in TABLES:
            row = await stamp_view(table, key)
            assert row["updated"] == PINNED
            assert row["last_viewed_at"] is not None

        await db.query(manager.down_migrations[25].sql)
        for table, key in TABLES:
            row = await stamp_view(table, key)
            assert row["updated"] != PINNED
