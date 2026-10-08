"""generate_embeddings(use_cache=True) resumes a failed run from the hash cache."""

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.utils.embedding import _cache_evict, generate_embeddings


class _FakeCacheTable:
    def __init__(self):
        self.rows: list = []

    async def repo_query(self, query, params=None):
        if "WHERE hash IN" in query:
            wanted = set(params["hashes"])
            return [r for r in self.rows if r["hash"] in wanted]
        if "count()" in query:
            return [{"n": len(self.rows)}]
        raise AssertionError(f"unexpected query: {query}")

    async def repo_insert(self, table, records, ignore_duplicates=False):
        assert table == "embedding_cache"
        self.rows.extend(records)
        return records


def _fake_model(fail_on_call=None):
    model = MagicMock()
    model.model_name = "fake-model"
    model.calls = []

    async def aembed(batch):
        model.calls.append(list(batch))
        if fail_on_call == len(model.calls):
            raise ConnectionError("quota exceeded")
        return [[float(t[1:])] for t in batch]

    model.aembed = aembed
    return model


def _patches(table, model):
    return (
        patch(
            "open_notebook.ai.models.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=model,
        ),
        patch("open_notebook.database.repository.repo_query", new=table.repo_query),
        patch("open_notebook.database.repository.repo_insert", new=table.repo_insert),
        patch("open_notebook.utils.embedding.EMBEDDING_BATCH_SIZE", 2),
        patch("open_notebook.utils.embedding.EMBEDDING_MAX_RETRIES", 1),
        patch("open_notebook.utils.embedding.EMBEDDING_RETRY_DELAY", 0),
    )


@pytest.mark.asyncio
async def test_failed_run_resumes_from_cache():
    table = _FakeCacheTable()
    texts = [f"t{i}" for i in range(6)]

    failing = _fake_model(fail_on_call=3)
    with ExitStack() as stack:
        for p in _patches(table, failing):
            stack.enter_context(p)
        with pytest.raises(RuntimeError):
            await generate_embeddings(texts, use_cache=True)
    assert len(table.rows) == 4

    working = _fake_model()
    with ExitStack() as stack:
        for p in _patches(table, working):
            stack.enter_context(p)
        result = await generate_embeddings(texts, use_cache=True)
    assert working.calls == [["t4", "t5"]]
    assert result == [[float(i)] for i in range(6)]


@pytest.mark.asyncio
async def test_use_cache_false_never_touches_cache():
    table = _FakeCacheTable()
    table.repo_query = AsyncMock(return_value=[])
    table.repo_insert = AsyncMock(return_value=[])
    texts = [f"t{i}" for i in range(6)]

    model = _fake_model()
    with ExitStack() as stack:
        for p in _patches(table, model):
            stack.enter_context(p)
        result = await generate_embeddings(texts)

    assert table.repo_query.await_count == 0
    assert table.repo_insert.await_count == 0
    assert model.calls == [["t0", "t1"], ["t2", "t3"], ["t4", "t5"]]
    assert result == [[float(i)] for i in range(6)]


@pytest.mark.asyncio
async def test_broken_cache_falls_through_to_provider():
    table = _FakeCacheTable()
    table.repo_query = AsyncMock(side_effect=ConnectionError("db down"))
    table.repo_insert = AsyncMock(side_effect=ConnectionError("db down"))
    texts = [f"t{i}" for i in range(6)]

    model = _fake_model()
    with ExitStack() as stack:
        for p in _patches(table, model):
            stack.enter_context(p)
        result = await generate_embeddings(texts, use_cache=True)

    assert table.repo_query.await_count > 0
    assert model.calls == [["t0", "t1"], ["t2", "t3"], ["t4", "t5"]]
    assert result == [[float(i)] for i in range(6)]


@pytest.mark.asyncio
async def test_eviction_removes_oldest_rows_over_the_cap():
    rows = [
        {"id": "embedding_cache:d", "created": 4},
        {"id": "embedding_cache:a", "created": 1},
        {"id": "embedding_cache:c", "created": 3},
        {"id": "embedding_cache:b", "created": 2},
    ]

    async def repo_query(query, params=None):
        if "count()" in query:
            return [{"n": len(rows)}]
        if "ORDER BY created ASC" in query:
            return sorted(rows, key=lambda r: r["created"])[: params["n"]]
        if query.startswith("DELETE embedding_cache"):
            rows[:] = [r for r in rows if r["id"] not in params["ids"]]
            return []
        raise AssertionError(f"unexpected query: {query}")

    with (
        patch("open_notebook.database.repository.repo_query", new=repo_query),
        patch("open_notebook.database.repository.ensure_record_id", new=lambda v: v),
    ):
        await _cache_evict(2)
        assert sorted(r["id"] for r in rows) == [
            "embedding_cache:c",
            "embedding_cache:d",
        ]
        await _cache_evict(2)
        assert len(rows) == 2


@pytest.mark.asyncio
async def test_max_rows_zero_disables_cache():
    table = _FakeCacheTable()
    table.repo_query = AsyncMock(return_value=[])
    table.repo_insert = AsyncMock(return_value=[])
    texts = [f"t{i}" for i in range(6)]

    model = _fake_model()
    with ExitStack() as stack:
        for p in _patches(table, model):
            stack.enter_context(p)
        stack.enter_context(
            patch("open_notebook.utils.embedding.EMBEDDING_CACHE_MAX_ROWS", 0)
        )
        result = await generate_embeddings(texts, use_cache=True)

    assert table.repo_query.await_count == 0
    assert table.repo_insert.await_count == 0
    assert model.calls == [["t0", "t1"], ["t2", "t3"], ["t4", "t5"]]
    assert result == [[float(i)] for i in range(6)]
