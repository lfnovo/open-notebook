"""metadata() hashes the whole corpus server side; searches must not pay that per query."""
from unittest.mock import AsyncMock
import pytest
from open_notebook.modules.hybrid_search import service


def build(monkeypatch, cache_seconds=10):
    monkeypatch.setattr(service, 'settings',
                        lambda: {**service.DEFAULTS, 'metadata_cache_seconds': cache_seconds})
    calls = {'n': 0}

    async def query(sql, variables=None):
        if 'crypto::sha256' in sql:
            calls['n'] += 1
            return [{'id': 'note:a', 'title': 'T', 'parent_id': 'note:a', 'kind': 'note',
                     'doc_hash': 'hash', 'chars': 10}]
        return []

    engine = service.HybridSearch(query=query)
    return engine, calls


@pytest.mark.asyncio
async def test_repeated_calls_hash_the_corpus_once(monkeypatch):
    engine, calls = build(monkeypatch)
    for _ in range(5):
        await engine.metadata()
    # Three tables are hashed on the cold call; the warm calls add nothing.
    assert calls['n'] == 3


@pytest.mark.asyncio
async def test_fresh_bypasses_the_cache(monkeypatch):
    engine, calls = build(monkeypatch)
    await engine.metadata()
    cold = calls['n']
    await engine.metadata(fresh=True)
    assert calls['n'] == cold * 2, 'indexing decisions must never read a cached hash'


@pytest.mark.asyncio
async def test_cache_expires(monkeypatch):
    engine, calls = build(monkeypatch, cache_seconds=0)
    await engine.metadata()
    cold = calls['n']
    await engine.metadata()
    assert calls['n'] > cold


@pytest.mark.asyncio
async def test_disabled_module_falls_back_to_the_default_window(monkeypatch):
    engine, calls = build(monkeypatch)

    def boom():
        raise RuntimeError('module disabled')

    monkeypatch.setattr(service, 'settings', boom)
    await engine.metadata()
    cold = calls['n']
    await engine.metadata()
    assert calls['n'] == cold, 'a settings failure must not reintroduce per-query hashing'
