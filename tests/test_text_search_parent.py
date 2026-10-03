from pathlib import Path

import pytest
from surrealdb import AsyncSurreal, RecordID

MIGRATIONS = Path("open_notebook/database/migrations")


def records(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    assert all(isinstance(row, dict) for row in value)
    return value


def functions(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    result = value["functions"]
    assert isinstance(result, dict)
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", [None, [], [RecordID("notebook", "chosen")]])
async def test_text_insights_keep_their_id_and_resolve_the_parent_source(
    scope: list[RecordID] | None,
) -> None:
    """Text and vector insight hits must share the same source identity (#1312)."""
    from open_notebook.database.async_migrate import AsyncMigrationManager

    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "insight_parent")
        # Only the search schema/functions are needed. Unrelated podcast
        # migrations depend on tables owned by podcast-creator.
        await db.query((MIGRATIONS / "1.surrealql").read_text())
        for migration in AsyncMigrationManager().up_migrations[23:]:
            await db.query(migration.sql)
        await db.query(
            """
            CREATE notebook:chosen SET name = 'Chosen';
            CREATE notebook:other SET name = 'Other';
            CREATE source:parent SET title = 'quasar source', full_text = 'quasar text';
            CREATE source_insight:insight SET source = source:parent,
                insight_type = 'summary', content = 'quasar evidence', embedding = [1.0, 0.0];
            CREATE note:control SET title = 'quasar note', content = 'quasar note', embedding = [1.0, 0.0];
            RELATE source:parent->reference->notebook:chosen;
            RELATE note:control->artifact->notebook:chosen;
            """
        )
        rows = records(
            await db.query(
                "RETURN fn::text_search('quasar', 10, true, true, $scope);",
                {"scope": None if scope is None else [item for item in scope]},
            )
        )
        by_id = {str(row["id"]): row for row in rows}
        assert str(by_id["source_insight:insight"]["parent_id"]) == "source:parent"
        assert str(by_id["source:parent"]["parent_id"]) == "source:parent"
        assert str(by_id["note:control"]["parent_id"]) == "note:control"
        vector = records(
            await db.query(
                "RETURN fn::vector_search([1.0, 0.0], 10, true, false, 0.5, $scope);",
                {"scope": None if scope is None else [item for item in scope]},
            )
        )
        assert str(vector[0]["parent_id"]) == "source:parent"
        assert str(vector[0]["id"]) == "source_insight:insight"
        assert (
            await db.query(
                "RETURN fn::text_search('quasar', 10, true, true, [notebook:other]);"
            )
            == []
        )
        notes = records(
            await db.query(
                "RETURN fn::text_search('quasar', 10, false, true, $scope);",
                {"scope": None if scope is None else [item for item in scope]},
            )
        )
        assert [str(row["id"]) for row in notes] == ["note:control"]
        sources = records(
            await db.query(
                "RETURN fn::text_search('quasar', 10, true, false, $scope);",
                {"scope": None if scope is None else [item for item in scope]},
            )
        )
        assert {str(row["id"]) for row in sources} == {
            "source:parent",
            "source_insight:insight",
        }


@pytest.mark.asyncio
async def test_migration_25_up_down_up_preserves_vector_search() -> None:
    from open_notebook.database.async_migrate import AsyncMigrationManager

    manager = AsyncMigrationManager()
    assert len(manager.up_migrations) == len(manager.down_migrations)
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "migration_cycle")
        await db.query((MIGRATIONS / "1.surrealql").read_text())
        await db.query(manager.up_migrations[23].sql)
        await db.query(
            "CREATE source:parent SET title = 'Article';"
            "CREATE source_insight:insight SET source = source:parent,"
            "insight_type = 'summary', content = 'quasar', embedding = [1.0, 0.0];"
        )
        before = functions(await db.query("INFO FOR DB;"))
        for migration, expected in [
            (manager.up_migrations[24], "source:parent"),
            (manager.down_migrations[24], "source_insight:insight"),
            (manager.up_migrations[24], "source:parent"),
        ]:
            await db.query(migration.sql)
            rows = records(
                await db.query(
                    "RETURN fn::text_search('quasar', 1, true, false, NONE);"
                )
            )
            assert len(rows) == 1
            assert str(rows[0]["parent_id"]) == expected
            assert str(rows[0]["id"]) == "source_insight:insight"
            after = functions(await db.query("INFO FOR DB;"))
            assert after["vector_search"] == before["vector_search"]
        assert (
            await db.query("RETURN fn::text_search('absent', 10, true, true, NONE);")
            == []
        )
