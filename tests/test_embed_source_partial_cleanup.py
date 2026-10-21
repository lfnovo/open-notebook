"""embed_source must not leave a partial set of embeddings behind when a
batched insert fails part-way (#1390).

repo_insert writes in batches of 50 (#1293), so it is no longer atomic. The
database is faked in memory here: DELETE clears the source's rows and the
insert stores its first batch before failing on the second.
"""

from unittest.mock import AsyncMock, patch

import pytest

from commands.embedding_commands import EmbedSourceInput, embed_source_command

SOURCE_ID = "source:abc"
OTHER_SOURCE_ID = "source:other"


class _FakeSource:
    full_text = "some text " * 200
    asset = None


class _FakeEmbeddingTable:
    def __init__(self, fail_on_batch: int):
        self.rows: list = [
            {"source": SOURCE_ID, "order": 0, "stale": True},
            {"source": OTHER_SOURCE_ID, "order": 0},
        ]
        self.fail_on_batch = fail_on_batch

    async def repo_query(self, query, params=None):
        # Only honour the scoped form; an unscoped DELETE would fail here.
        assert query == "DELETE source_embedding WHERE source = $source_id"
        target = str(params["source_id"])
        self.rows = [r for r in self.rows if str(r["source"]) != target]
        return []

    def rows_for(self, source_id):
        return [r for r in self.rows if r["source"] == source_id]

    async def repo_insert(self, table, records):
        assert table == "source_embedding"
        for batch_no, start in enumerate(range(0, len(records), 50)):
            if batch_no == self.fail_on_batch:
                raise ConnectionError("websocket closed")
            self.rows.extend(
                {**r, "source": str(r["source"])} for r in records[start : start + 50]
            )


def _patches(table: _FakeEmbeddingTable, n_chunks: int):
    return (
        patch(
            "commands.embedding_commands.Source.get",
            new=AsyncMock(return_value=_FakeSource()),
        ),
        patch(
            "commands.embedding_commands.chunk_text",
            return_value=[f"chunk {i}" for i in range(n_chunks)],
        ),
        patch(
            "commands.embedding_commands.generate_embeddings",
            new=AsyncMock(return_value=[[0.1, 0.2]] * n_chunks),
        ),
        patch("commands.embedding_commands.repo_query", new=table.repo_query),
        patch("commands.embedding_commands.repo_insert", new=table.repo_insert),
    )


@pytest.mark.asyncio
async def test_failure_on_later_batch_leaves_no_embeddings():
    table = _FakeEmbeddingTable(fail_on_batch=1)
    p1, p2, p3, p4, p5 = _patches(table, n_chunks=120)

    with p1, p2, p3, p4, p5:
        with pytest.raises(ConnectionError, match="websocket closed"):
            await embed_source_command(EmbedSourceInput(source_id=SOURCE_ID))

    assert table.rows_for(SOURCE_ID) == []
    assert len(table.rows_for(OTHER_SOURCE_ID)) == 1


@pytest.mark.asyncio
async def test_original_error_is_reraised_when_cleanup_also_fails():
    table = _FakeEmbeddingTable(fail_on_batch=1)
    calls = {"n": 0}
    original_query = table.repo_query

    async def flaky_query(query, params=None):
        calls["n"] += 1
        if calls["n"] == 2:  # the cleanup DELETE
            raise RuntimeError("cleanup failed")
        return await original_query(query, params)

    p1, p2, p3, _p4, p5 = _patches(table, n_chunks=120)
    with (
        p1,
        p2,
        p3,
        p5,
        patch("commands.embedding_commands.repo_query", new=flaky_query),
    ):
        with pytest.raises(ConnectionError, match="websocket closed"):
            await embed_source_command(EmbedSourceInput(source_id=SOURCE_ID))


@pytest.mark.asyncio
async def test_successful_insert_keeps_all_embeddings():
    table = _FakeEmbeddingTable(fail_on_batch=-1)
    p1, p2, p3, p4, p5 = _patches(table, n_chunks=120)

    with p1, p2, p3, p4, p5:
        result = await embed_source_command(EmbedSourceInput(source_id=SOURCE_ID))

    assert result.success is True
    assert result.chunks_created == 120
    rows = table.rows_for(SOURCE_ID)
    assert len(rows) == 120
    assert not any(r.get("stale") for r in rows)
    assert len(table.rows_for(OTHER_SOURCE_ID)) == 1
