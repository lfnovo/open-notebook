"""View stamps must not move notebook or source updated (#1398)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from surrealdb import AsyncSurreal, RecordID

MIGRATIONS = Path("open_notebook/database/migrations")
PINNED = datetime(2020, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_view_stamp_does_not_bump_updated() -> None:
    """UPDATE last_viewed_at leaves a pinned updated instant in place."""
    async with AsyncSurreal("mem://") as db:
        await db.use("view_regression", "updated")
        await db.query((MIGRATIONS / "1.surrealql").read_text())
        await db.query((MIGRATIONS / "18.surrealql").read_text())
        await db.query("CREATE notebook:n SET name = 'Notebook';")
        await db.query("CREATE source:s SET title = 'Source';")
        await db.query((MIGRATIONS / "26.surrealql").read_text())

        for table, key in (("notebook", "n"), ("source", "s")):
            await db.query(
                f'UPDATE {table}:{key} SET updated = d"2020-01-01T00:00:00Z";'
            )
            row = await db.query(
                f"UPDATE ${table}_id SET last_viewed_at = time::now();",
                {f"{table}_id": RecordID(table, key)},
            )
            assert row[0]["updated"] == PINNED
            assert row[0]["last_viewed_at"] is not None
