"""Query cost must follow the candidate count, not the size of the archive."""
from unittest.mock import AsyncMock
import pytest
from open_notebook.modules.hybrid_search import service

ROW = {'id': 'hs:1', 'doc_id': 'note:a', 'parent_id': 'note:a', 'title': 'T', 'kind': 'note',
       'doc_hash': 'hash', 'content': 'body', 'start': 0, 'end': 4, 'sha256': 's',
       'rrf_score': .1, 'channels': ['vector']}


def engine_with(monkeypatch, docs, seen):
    monkeypatch.setattr(service, 'settings', lambda: service.DEFAULTS.copy())

    async def query(sql, variables=None):
        seen.append((sql, variables or {}))
        if sql.startswith('SELECT doc_id,doc_hash FROM $records'):
            requested = {str(r) for r in variables['records']}
            return [{'doc_id': d['id'], 'doc_hash': d['doc_hash']} for d in docs
                    if str(engine.writer.metadata_id('hs_p_a', d['id'])) in requested]
        return []

    engine = service.HybridSearch(query=query)
    engine.active = AsyncMock(return_value={'table': 'hs_p_a', 'signature': 's', 'model': 'm'})
    engine.metadata = AsyncMock(return_value=docs)
    engine.model = AsyncMock(return_value=('s', None))
    engine.start = AsyncMock()
    engine.rerank = AsyncMock(side_effect=lambda q, rows, n: rows)
    return engine


def archive(n):
    return [{'id': f'note:{i}', 'parent_id': f'note:{i}', 'kind': 'note', 'doc_hash': 'hash'}
            for i in range(n)]


@pytest.mark.asyncio
async def test_an_unscoped_search_never_sends_one_identifier_per_document(monkeypatch):
    seen = []
    engine = engine_with(monkeypatch, archive(5000), seen)
    engine.vector = AsyncMock(return_value=[])
    await engine.search('strateji', rerank=False)
    sent = [v for _, v in seen if 'valid' in v]
    assert not sent, 'the archive must not be materialised into a query parameter'
    assert any('kind IN $kinds' in sql for sql, _ in seen), 'scope is still applied inside the query'


@pytest.mark.asyncio
async def test_a_notebook_search_still_restricts_by_identifier(monkeypatch):
    seen = []
    engine = engine_with(monkeypatch, archive(3), seen)
    engine.scope = AsyncMock(return_value=archive(3))
    engine.vector = AsyncMock(return_value=[])
    await engine.search('strateji', notebook_ids=['notebook:a'], rerank=False)
    sent = [v['valid'] for _, v in seen if 'valid' in v]
    assert sent and sent[0] == ['note:0', 'note:1', 'note:2'], 'a notebook is bounded, so ids are fine'


@pytest.mark.asyncio
async def test_a_changed_document_is_dropped_from_results_and_reported(monkeypatch):
    seen = []
    engine = engine_with(monkeypatch, [{'id': 'note:a', 'parent_id': 'note:a', 'kind': 'note',
                                        'doc_hash': 'new'}], seen)
    engine.lexical = AsyncMock(return_value={'bm25_tr': [ROW]})   # row still carries the old hash
    engine.vector = AsyncMock(return_value=[])
    rows, meta = await engine.search('strateji', rerank=False)
    assert rows == [] and meta['pending_documents'] == 1
    assert 'index_updating' in meta['warnings']
    engine.start.assert_awaited()


@pytest.mark.asyncio
async def test_a_document_outside_the_scope_cannot_reach_the_results(monkeypatch):
    seen = []
    engine = engine_with(monkeypatch, [{'id': 'note:other', 'parent_id': 'note:other',
                                        'kind': 'note', 'doc_hash': 'hash'}], seen)
    engine.lexical = AsyncMock(return_value={'bm25_tr': [ROW]})   # note:a is not in scope
    engine.vector = AsyncMock(return_value=[])
    rows, _ = await engine.search('strateji', rerank=False)
    assert rows == [], 'identical content elsewhere must not cross scope'


@pytest.mark.asyncio
async def test_a_fresh_in_scope_document_survives_both_checks(monkeypatch):
    seen = []
    engine = engine_with(monkeypatch, [{'id': 'note:a', 'parent_id': 'note:a', 'kind': 'note',
                                        'doc_hash': 'hash'}], seen)
    engine.lexical = AsyncMock(return_value={'bm25_tr': [ROW]})
    engine.vector = AsyncMock(return_value=[])
    rows, meta = await engine.search('strateji', rerank=False)
    assert [r['id'] for r in rows] == ['note:a'] and meta['pending_documents'] == 0


@pytest.mark.asyncio
async def test_unscoped_vector_widens_instead_of_scanning_every_vector(monkeypatch):
    seen = []
    engine = engine_with(monkeypatch, archive(2), seen)
    engine.cache[('s', 'q')] = [0.0] * 8
    await engine.vector('hs_p_a', 'q', 's', type('S', (), {'name': 'x'})(), None, 10, False)
    assert not any('vector::similarity::cosine' in sql for sql, _ in seen), (
        'an exact cosine over an unbounded archive reads every stored vector')
    widths = [sql.split('<|')[1].split('|>')[0] for sql, _ in seen if '<|' in sql]
    assert widths == ['10,200', '40,400'], 'the approximate search widens instead'
