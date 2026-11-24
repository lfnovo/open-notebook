"""fn::text_search must read the full-text indexes, never scan the tables (#1636).

Migration 24 added notebook scope to every branch as
`AND (!$scoped OR source IN $scoped_sources)`. SurrealDB's planner gives up on
the whole WHERE clause as soon as it meets a unary operator (and would also do
so for the OR), so each branch fetched every row of its table, embeddings and
full texts included, even when nothing matched.

The plan is asserted instead of the duration: EXPLAIN is deterministic, and it
runs on the definition stored in the database, not on the migration's text.

As in test_text_search_limit.py, both directions are asserted: the rolled-back
definition must reproduce the table scans, and migration 29 must remove them.
"""

import re
from pathlib import Path
from typing import Any

import pytest
from surrealdb import AsyncSurreal, RecordID

from open_notebook.database.async_migrate import AsyncMigrationManager

MIGRATIONS = Path("open_notebook/database/migrations")

#: (table, searched field) -> the full-text index that must serve it.
FULL_TEXT_INDEXES = {
    ("source", "title"): "idx_source_title",
    ("source", "full_text"): "idx_source_full_text",
    ("source_embedding", "content"): "idx_source_embed_chunk",
    ("source_insight", "content"): "idx_source_insight",
    ("note", "title"): "idx_note_title",
    ("note", "content"): "idx_note",
}

#: One full-text SELECT of the stored function. `(?!SELECT)` keeps a match from
#: starting in one SELECT and ending in the next.
LEG = re.compile(
    r"SELECT\b(?:(?!\bSELECT\b).)*?\bFROM (?P<table>\w+)\b"
    r"(?:(?!\bSELECT\b).)*?\bWHERE (?P<field>\w+) @1@"
    r"(?:(?!\bSELECT\b).)*?\bGROUP BY id",
    re.IGNORECASE | re.DOTALL,
)

SCOPES: dict[str, list[RecordID] | None] = {
    "unscoped": None,
    "empty": [],
    "chosen": [RecordID("notebook", "chosen")],
    "chosen+other": [RecordID("notebook", "chosen"), RecordID("notebook", "other")],
    "unlinked": [RecordID("notebook", "unlinked")],
}


async def _schema(db: Any) -> None:
    await db.query((MIGRATIONS / "1.surrealql").read_text())
    for migration in AsyncMigrationManager().up_migrations[1:]:
        await db.query(migration.sql)


async def _fixture(db: Any) -> None:
    await _schema(db)
    await db.query(
        """
        CREATE notebook:chosen SET name = 'Chosen';
        CREATE notebook:other SET name = 'Other';
        CREATE notebook:unlinked SET name = 'Unlinked';
        CREATE source:a SET title = 'quasar survey', full_text = 'a quasar, then another quasar';
        CREATE source:b SET title = 'pulsar survey', full_text = 'mentions a quasar once';
        CREATE source:c SET title = 'nothing here', full_text = 'plain text';
        CREATE source_embedding:a0 SET source = source:a, order = 0, content = 'quasar chunk', embedding = [1.0, 0.0];
        CREATE source_embedding:a1 SET source = source:a, order = 1, content = 'second quasar quasar chunk', embedding = [1.0, 0.0];
        CREATE source_embedding:c0 SET source = source:c, order = 0, content = 'a lone quasar chunk', embedding = [1.0, 0.0];
        CREATE source_insight:b0 SET source = source:b, insight_type = 'summary', content = 'quasar evidence', embedding = [1.0, 0.0];
        CREATE note:n0 SET title = 'quasar note', content = 'body', embedding = [1.0, 0.0];
        CREATE note:n1 SET title = 'plain note', content = 'quasar in the body', embedding = [1.0, 0.0];
        RELATE source:a->reference->notebook:chosen;
        RELATE source:a->reference->notebook:other;
        RELATE source:b->reference->notebook:other;
        RELATE note:n0->artifact->notebook:chosen;
        RELATE note:n1->artifact->notebook:other;
        """
    )


async def _plans(db: Any) -> list[tuple[str, str, list[str]]]:
    """(table, field, [index or 'TABLE SCAN', ...]) for each leg of the stored function."""
    info = await db.query("INFO FOR DB;")
    definition = info["functions"]["text_search"]
    plans = []
    for leg in LEG.finditer(definition):
        for scoped, scope in ((False, []), (True, [RecordID("source", "a")])):
            rows = await db.query(
                f"{leg.group(0)} EXPLAIN;",
                {
                    "query_text": "quasar",
                    "scoped": scoped,
                    "scoped_sources": scope,
                    "scoped_notes": [],
                },
            )
            assert isinstance(rows, list), rows
            iterations = [
                row["detail"]["plan"]["index"]
                if row["operation"] == "Iterate Index"
                else "TABLE SCAN"
                for row in rows
                if row["operation"].startswith("Iterate")
            ]
            assert iterations, rows
            plans.append((leg.group("table"), leg.group("field"), iterations))
    # A leg the regex stops recognizing must fail here, not go unchecked.
    assert {(table, field) for table, field, _ in plans} == set(FULL_TEXT_INDEXES), (
        definition
    )
    return plans


async def _search(
    db: Any, query: str, limit: int, sources: bool, notes: bool, scope: Any
) -> list[dict[str, Any]]:
    rows = await db.query(
        "RETURN fn::text_search($query, $limit, $sources, $notes, $scope);",
        {
            "query": query,
            "limit": limit,
            "sources": sources,
            "notes": notes,
            "scope": scope,
        },
    )
    assert isinstance(rows, list), rows
    return rows


@pytest.mark.asyncio
async def test_every_branch_reads_its_full_text_index() -> None:
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "text_index")
        await _schema(db)

        for table, field, iterations in await _plans(db):
            assert iterations == [FULL_TEXT_INDEXES[(table, field)]], (table, field)


@pytest.mark.asyncio
async def test_the_rolled_back_text_search_REPRODUCES_the_table_scans() -> None:
    manager = AsyncMigrationManager()
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "text_index_cycle")
        await _schema(db)

        # Migration 29 is index 28. Rolling it back restores 26's definition.
        await db.query(manager.down_migrations[28].sql)
        for table, field, iterations in await _plans(db):
            assert iterations == ["TABLE SCAN"], (table, field)

        await db.query(manager.up_migrations[28].sql)
        for table, field, iterations in await _plans(db):
            assert iterations == [FULL_TEXT_INDEXES[(table, field)]], (table, field)


@pytest.mark.asyncio
async def test_results_are_the_same_as_before_migration_29() -> None:
    """Same rows, same relevance, same order: only the plan changes."""
    manager = AsyncMigrationManager()
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "text_index_results")
        await _fixture(db)

        cases = [
            (query, limit, sources, notes, scope)
            for query in ("quasar", "quasar survey", "survey", "absent")
            for limit in (1, 3, 50)
            for sources, notes in ((True, False), (False, True), (True, True))
            for scope in SCOPES
        ]

        async def run_all() -> list[list[dict[str, Any]]]:
            return [
                await _search(db, query, limit, sources, notes, SCOPES[scope])
                for query, limit, sources, notes, scope in cases
            ]

        after = await run_all()
        await db.query(manager.down_migrations[28].sql)
        before = await run_all()

        assert any(before), "the fixture matches nothing, so nothing was compared"
        for case, old, new in zip(cases, before, after):
            assert new == old, case


@pytest.mark.asyncio
async def test_scope_still_excludes_other_notebooks() -> None:
    """An index hit outside the notebook must not leak into a scoped search."""
    db: Any
    async with AsyncSurreal("mem://") as db:
        await db.use("search_regression", "text_index_scope")
        await _fixture(db)

        async def parents(scope: str) -> set[str]:
            rows = await _search(db, "quasar", 50, True, True, SCOPES[scope])
            return {str(row["parent_id"]) for row in rows}

        everything = {"source:a", "source:b", "source:c", "note:n0", "note:n1"}
        assert await parents("unscoped") == everything
        assert await parents("empty") == everything
        assert await parents("chosen") == {"source:a", "note:n0"}
        assert await parents("chosen+other") == everything - {"source:c"}
        assert await parents("unlinked") == set()
