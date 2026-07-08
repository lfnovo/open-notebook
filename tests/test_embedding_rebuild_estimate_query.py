"""
Regression test for the malformed "existing sources" count query in
api/routers/embedding_rebuild.py's start_rebuild() (mode="existing" branch).

The query used to end in `FROM {}` - a stray, unfilled-looking placeholder
(not an f-string, so not injectable, but SurrealQL requires SELECT to have
a FROM target, and `{}` isn't a real table). It happened to still produce
a correct result in this repo's embedded SurrealDB engine, but that's an
accident of how the parser tolerates an empty-object FROM target, not
documented/guaranteed SurrealQL behavior - and it read as broken.

This is specifically a "is the query text itself valid, well-defined
SurrealQL that returns the right answer" bug, which a mocked repo_query
can't catch (mocking would just assume the query is fine and test the
Python branching around it, which was never the problem). So this test
runs the actual query from the source file against a real embedded
SurrealDB instance instead of mocking - matching how this specific fix was
verified during development.
"""

import re

import pytest
import pytest_asyncio
from surrealdb import AsyncSurreal

from open_notebook.database.repository import repo_query


def _extract_existing_sources_query() -> str:
    """Pull the exact query text out of the source file, so this test
    can't silently drift from what's actually shipped."""
    with open("api/routers/embedding_rebuild.py") as f:
        content = f.read()
    match = re.search(
        r'result = await repo_query\(\s*"""(.*?)"""', content, re.DOTALL
    )
    assert match, "could not locate the existing-sources count query in embedding_rebuild.py"
    return match.group(1)


@pytest_asyncio.fixture
async def embedded_db(tmp_path, monkeypatch):
    """Point repo_query at a scratch file-backed embedded SurrealDB instance
    for the duration of this test, then restore the real config."""
    db_path = tmp_path / "embedding_rebuild_test_db"
    monkeypatch.setenv("SURREAL_URL", f"file://{db_path}")
    monkeypatch.setenv("SURREAL_NAMESPACE", "test_ns")
    monkeypatch.setenv("SURREAL_DATABASE", "test_db")
    monkeypatch.setenv("SURREAL_USER", "root")
    monkeypatch.setenv("SURREAL_PASSWORD", "root")

    bootstrap = AsyncSurreal(f"file://{db_path}")
    await bootstrap.use("test_ns", "test_db")
    await bootstrap.query("DEFINE USER root ON ROOT PASSWORD 'root' ROLES OWNER")
    await bootstrap.close()

    yield


class TestExistingSourcesCountQuery:
    def test_query_no_longer_contains_the_stray_placeholder(self):
        query = _extract_existing_sources_query()
        assert "FROM {}" not in query
        assert "RETURN" in query

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_source_embeddings(self, embedded_db):
        query = _extract_existing_sources_query()
        result = await repo_query(query)
        assert result == [0]

    @pytest.mark.asyncio
    async def test_counts_distinct_sources_with_a_nonempty_embedding(self, embedded_db):
        query = _extract_existing_sources_query()

        for i in range(3):
            await repo_query(f"CREATE source:s{i} SET title = 'Source {i}';")
        await repo_query(
            "CREATE source_embedding SET source = source:s0, content = 'x', embedding = [0.1, 0.2];"
        )
        await repo_query(
            "CREATE source_embedding SET source = source:s1, content = 'x', embedding = [0.3, 0.4];"
        )
        # s2 has no source_embedding at all - must not be counted

        result = await repo_query(query)
        assert result == [2]

    @pytest.mark.asyncio
    async def test_duplicate_embedding_rows_for_one_source_count_once(self, embedded_db):
        query = _extract_existing_sources_query()

        await repo_query("CREATE source:s0 SET title = 'S0';")
        await repo_query(
            "CREATE source_embedding SET source = source:s0, content = 'a', embedding = [0.1];"
        )
        await repo_query(
            "CREATE source_embedding SET source = source:s0, content = 'b', embedding = [0.2];"
        )

        result = await repo_query(query)
        assert result == [1]

    @pytest.mark.asyncio
    async def test_empty_embedding_array_is_excluded(self, embedded_db):
        query = _extract_existing_sources_query()

        await repo_query("CREATE source:s0 SET title = 'S0';")
        await repo_query(
            "CREATE source_embedding SET source = source:s0, content = 'a', embedding = [];"
        )

        result = await repo_query(query)
        assert result == [0]

    @pytest.mark.asyncio
    async def test_result_shape_matches_what_start_rebuild_expects(self, embedded_db):
        """Locks in the exact contract api/routers/embedding_rebuild.py's
        start_rebuild() relies on (result[0] is a bare int), so a future
        query rewrite can't silently change the shape without this failing."""
        query = _extract_existing_sources_query()
        await repo_query("CREATE source:s0 SET title = 'S0';")
        await repo_query(
            "CREATE source_embedding SET source = source:s0, content = 'a', embedding = [0.1];"
        )

        result = await repo_query(query)
        assert isinstance(result, list)
        assert isinstance(result[0], int)
