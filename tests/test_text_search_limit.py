"""fn::text_search must order by relevance and not lose the best match (#1505).

Same defect as #1431 in the sibling function: the final statement grouped,
ordered and limited in one SELECT, so SurrealDB returned the grouped rows in
group-key order and the LIMIT truncated an id-ordered list. Unlike vector
search, nothing re-sorts text search results in Python, so the wrong order also
reached callers whenever nothing was cut.

As in test_vector_search_limit.py, both directions are asserted: the rolled-back
definition must reproduce the defect, and migration 26 must remove it.
"""

from pathlib import Path
from typing import Any

import pytest
from surrealdb import AsyncSurreal

MIGRATIONS = Path("open_notebook/database/migrations")

#: Fewer than the notes created below, so the LIMIT has to discard something.
MATCH_COUNT = 3
NOTE_COUNT = 5
QUERY = "RETURN fn::text_search('quasar', $limit, true, true, NONE);"


def records(value: object) -> list[dict[str, Any]]:
    assert isinstance(value, list), value
    assert all(isinstance(row, dict) for row in value)
    return value


def kinds(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["id"]).split(":")[0] for row in rows]


async def _fixture(db: Any) -> None:
    """One source that matches on title AND full text (the best match), crowded
    by more notes than the limit allows. `note` sorts before `source`, which is
    why id-ordered truncation drops the source."""
    await db.query((MIGRATIONS / "1.surrealql").read_text())
    from open_notebook.database.async_migrate import AsyncMigrationManager

    for migration in AsyncMigrationManager().up_migrations[1:]:
        await db.query(migration.sql)

    await db.query(
        "CREATE source:best SET title = 'quasar', full_text = 'quasar quasar';"
    )
    for index in range(NOTE_COUNT):
        await db.query(
            f"CREATE note:n{index} SET title = 'note {index}', "
            f"content = 'a long note that mentions quasar once among many "
            f"other words number {index}';"
        )

    # The fixture must actually make the source the best match, or the tests
    # below pass or fail for reasons unrelated to the ordering.
    rows = records(await db.query(QUERY, {"limit": 50}))
    best = max(rows, key=lambda row: float(row["relevance"]))
    assert str(best["id"]) == "source:best", rows
    assert kinds(rows).count("note") == NOTE_COUNT, rows


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [MATCH_COUNT, NOTE_COUNT + 1, 50])
async def test_text_search_returns_best_match_first(limit: int) -> None:
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", f"text_limit_{limit}")
        await _fixture(db)

        rows = records(await db.query(QUERY, {"limit": limit}))

        assert len(rows) == min(limit, NOTE_COUNT + 1)
        assert str(rows[0]["id"]) == "source:best", kinds(rows)
        relevances = [row["relevance"] for row in rows]
        assert relevances == sorted(relevances, reverse=True), relevances


@pytest.mark.asyncio
async def test_the_rolled_back_text_search_REPRODUCES_the_defect() -> None:
    from open_notebook.database.async_migrate import AsyncMigrationManager

    manager = AsyncMigrationManager()

    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "text_limit_cycle")
        await _fixture(db)
        args: dict[str, Any] = {"limit": MATCH_COUNT}

        # Migration 26 is index 25. Rolling it back restores 25's
        # single-statement fn::text_search, which is the broken one.
        await db.query(manager.down_migrations[25].sql)
        broken = records(await db.query(QUERY, args))
        assert "source" not in kinds(broken), (
            "the rolled-back definition returned the source, so this test is "
            "not reproducing #1505: %s" % kinds(broken)
        )

        await db.query(manager.up_migrations[25].sql)
        fixed = records(await db.query(QUERY, args))
        assert str(fixed[0]["id"]) == "source:best", kinds(fixed)
