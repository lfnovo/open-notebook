"""fn::vector_search must not lose sources to the LIMIT (#1431).

The defect: the final statement grouped, ordered and limited in one SELECT.
SurrealDB returns grouped rows in group-key order, so the ORDER BY was inert and
the LIMIT truncated a list ordered by record id. `note:` sorts before `source:`,
so any match_count below the number of embedded notes returned notes only --
discarding sources that scored higher than every note returned, with no error.

Both directions are asserted in one run: the rolled-back definition must
REPRODUCE the defect, and the migration must remove it. A regression test that
only demonstrates the fixed behaviour cannot distinguish a working fix from a
fixture that never had the problem.
"""

from pathlib import Path

import pytest
from surrealdb import AsyncSurreal, RecordID

MIGRATIONS = Path("open_notebook/database/migrations")

#: Fewer than the notes created below, so the LIMIT has to discard something.
MATCH_COUNT = 3
NOTE_COUNT = 5


def records(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    assert all(isinstance(row, dict) for row in value)
    return value


def kinds(rows: list[dict[str, object]]) -> list[str]:
    return [str(row["id"]).split(":")[0] for row in rows]


async def _fixture(db: AsyncSurreal) -> None:
    """One source chunk that is the BEST match, crowded by more notes than the
    limit allows.

    The source embedding is an exact match (cosine 1.0); every note is slightly
    off-axis and so scores lower. Record ids matter as much as the scores: `note`
    sorts before `source`, which is why id-ordered truncation drops the source.
    """
    await db.query((MIGRATIONS / "1.surrealql").read_text())
    from open_notebook.database.async_migrate import AsyncMigrationManager

    for migration in AsyncMigrationManager().up_migrations[23:]:
        await db.query(migration.sql)

    await db.query(
        """
        CREATE notebook:chosen SET name = 'Chosen';
        CREATE source:best SET title = 'best source', full_text = 'quasar';
        CREATE source_embedding:chunk SET source = source:best, order = 0,
            content = 'quasar evidence', embedding = [1.0, 0.0];
        RELATE source:best->reference->notebook:chosen;
        """
    )

    # ASSERT THE FIXTURE BUILT. `source_embedding` requires `order: int`, and
    # omitting it makes the CREATE fail by RETURNING an error string rather than
    # raising -- so the chunk silently did not exist and every assertion below
    # measured an empty source branch. A fixture that cannot reach the branch
    # under test passes or fails for reasons that have nothing to do with the
    # code.
    chunks = records(
        await db.query("SELECT id FROM source_embedding WHERE source = source:best;")
    )
    assert len(chunks) == 1, (
        "the source chunk was not created, so there is no source for the limit "
        "to drop: %r" % (chunks,)
    )
    for index in range(NOTE_COUNT):
        # 0.98, 0.96, ... -- all above min_similarity, none as close as the
        # source. Written as a loop so the count is a constant, not a literal
        # repeated five times.
        offset = 0.02 * (index + 1)
        await db.query(
            f"""
            CREATE note:n{index} SET title = 'note {index}',
                content = 'quasar note {index}',
                embedding = [{1.0 - offset}, {offset}];
            RELATE note:n{index}->artifact->notebook:chosen;
            """
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", [None, [], [RecordID("notebook", "chosen")]])
async def test_a_source_outscoring_every_note_survives_the_limit(
    scope: list[RecordID] | None,
) -> None:
    """The reported case: more embedded notes than match_count, best hit a source.

    Parametrised over the optional $notebook_ids added in migration 24, so the
    fix is asserted for global AND notebook-scoped search rather than only the
    path the reproduction happened to use.
    """
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "vector_limit")
        await _fixture(db)

        rows = records(
            await db.query(
                "RETURN fn::vector_search([1.0, 0.0], $limit, true, true, 0.5, $scope);",
                {"limit": MATCH_COUNT, "scope": scope},
            )
        )

        assert len(rows) == MATCH_COUNT
        assert "source" in kinds(rows), (
            "no source survived the limit: %s -- this is #1431" % kinds(rows)
        )
        assert str(rows[0]["id"]) == "source:best", (
            "the highest-scoring row is not first: %s"
            % [(str(r["id"]), r["similarity"]) for r in rows]
        )

        similarities = [row["similarity"] for row in rows]
        assert similarities == sorted(similarities, reverse=True), similarities


@pytest.mark.asyncio
async def test_the_rolled_back_definition_REPRODUCES_the_defect() -> None:
    """A known positive for the defect itself.

    Without this, the test above passes equally against a fixture that never had
    the problem, and a regression test that cannot fail is indistinguishable from
    one that is not looking.
    """
    from open_notebook.database.async_migrate import AsyncMigrationManager

    manager = AsyncMigrationManager()
    assert len(manager.up_migrations) == len(manager.down_migrations)

    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "vector_limit_cycle")
        await _fixture(db)

        query = "RETURN fn::vector_search([1.0, 0.0], $limit, true, true, 0.5, NONE);"
        args = {"limit": MATCH_COUNT}

        # Migration 26 is index 25. Roll it back to restore 24's single-statement
        # form, which is the broken one.
        await db.query(manager.down_migrations[25].sql)
        broken = records(await db.query(query, args))
        assert "source" not in kinds(broken), (
            "the rolled-back definition returned a source, so this test is not "
            "reproducing #1431 and proves nothing: %s" % kinds(broken)
        )

        # Forward again: the source comes back.
        await db.query(manager.up_migrations[25].sql)
        fixed = records(await db.query(query, args))
        assert "source" in kinds(fixed), kinds(fixed)
        assert str(fixed[0]["id"]) == "source:best"


@pytest.mark.asyncio
async def test_raising_the_limit_above_the_note_count_also_surfaced_the_source() -> (
    None
):
    """The falsifiable prediction from the report, kept as a test.

    It is the workaround, not the fix -- but if this ever stops holding, the
    mechanism in #1431 was not what we thought it was.
    """
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "vector_limit_high")
        await _fixture(db)
        rows = records(
            await db.query(
                "RETURN fn::vector_search([1.0, 0.0], 50, true, true, 0.5, NONE);"
            )
        )
        assert kinds(rows).count("source") == 1
        assert len(rows) == NOTE_COUNT + 1
