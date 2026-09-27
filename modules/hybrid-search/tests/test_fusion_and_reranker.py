"""Fusion weighting, reranker key handling and the abstain threshold."""
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock
import pytest

spec = importlib.util.spec_from_file_location(
    'ranking', Path(__file__).parents[1] / 'overlay/open_notebook/modules/hybrid_search/ranking.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
from open_notebook.modules.hybrid_search import service

K = 60


def row(name):
    return {'id': name, 'doc_id': name, 'parent_id': name, 'title': name, 'content': name}


# --------------------------------------------------------------------------
# Fusion: the two lexical indexes hold the same text, so they are one family.
# --------------------------------------------------------------------------
def test_one_lexical_analyzer_still_casts_a_full_vote():
    only_turkish = r.fuse({'bm25_tr': [row('a')]})[0]['rrf_score']
    only_vector = r.fuse({'vector': [row('a')]})[0]['rrf_score']
    assert only_turkish == pytest.approx(only_vector), (
        'an exact keyword match that only the Turkish analyzer can find must not '
        'be worth half of a semantic match')
    assert only_turkish == pytest.approx(1 / (K + 1))


def test_both_analyzers_finding_it_is_still_one_vote():
    both = r.fuse({'bm25_tr': [row('a')], 'bm25_en': [row('a')]})[0]['rrf_score']
    assert both == pytest.approx(1 / (K + 1)), 'the same text found twice is not two pieces of evidence'


def test_a_family_scores_at_its_best_rank():
    ranked = r.fuse({'bm25_tr': [row('x'), row('a')], 'bm25_en': [row('a')]})
    hit = next(h for h in ranked if h['id'] == 'a')
    assert hit['rrf_score'] == pytest.approx(1 / (K + 1)), 'rank 1 in either analyzer is rank 1'


def test_distinct_families_do_add_up():
    lexical_and_vector = r.fuse({'bm25_tr': [row('a')], 'vector': [row('a')]})[0]['rrf_score']
    assert lexical_and_vector == pytest.approx(2 / (K + 1))


def test_agreement_across_families_outranks_one_strong_channel():
    ranked = r.fuse({'bm25_tr': [row('b'), row('a')], 'vector': [row('b'), row('a')]})
    assert ranked[0]['id'] == 'b'
    both = next(h for h in ranked if h['id'] == 'a')
    assert both['channels'] == ['bm25_tr', 'vector'] and both['ranks'] == {'bm25_tr': 2, 'vector': 2}


# --------------------------------------------------------------------------
# The reranker key must not be read from disk inside the event loop per search.
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_key_is_read_once_and_reread_only_when_rejected(tmp_path, monkeypatch):
    key = tmp_path / 'reranker.key'
    key.write_text('first\n')
    monkeypatch.setenv('LOCAL_RERANKER_KEY_FILE', str(key))
    engine = service.HybridSearch(query=AsyncMock(return_value=[]))

    assert await engine.reranker_key() == 'first'
    key.write_text('rotated\n')
    assert await engine.reranker_key() == 'first', 'the cached key is reused'
    assert await engine.reranker_key(reload=True) == 'rotated', 'rejection re-reads it'


# --------------------------------------------------------------------------
# The abstain threshold is a setting, not a constant buried in the code.
# --------------------------------------------------------------------------
def test_threshold_is_exposed_with_its_current_value():
    assert service.DEFAULTS['weak_relevance_permille'] == 1, 'default behaviour is unchanged'


@pytest.mark.asyncio
@pytest.mark.parametrize('permille,score,expect_warning', [(1, .002, False), (1, .0005, True),
                                                           (500, .4, True), (500, .6, False)])
async def test_threshold_decides_when_neural_order_is_set_aside(monkeypatch, permille, score, expect_warning):
    hit = {**row('a'), 'kind': 'note', 'doc_hash': 'h', 'start': 0, 'end': 1, 'sha256': 's',
           'rrf_score': .1, 'channels': ['vector']}
    monkeypatch.setattr(service, 'settings',
                        lambda: {**service.DEFAULTS, 'weak_relevance_permille': permille})
    engine = service.HybridSearch(query=AsyncMock(return_value=[{'doc_id': 'a', 'doc_hash': 'h'}]))
    engine.active = AsyncMock(return_value={'table': 'hs_p_a', 'signature': 's', 'model': 'm'})
    engine.metadata = AsyncMock(return_value=[{'id': 'a', 'parent_id': 'a', 'kind': 'note', 'doc_hash': 'h'}])
    engine.model = AsyncMock(return_value=('s', None))
    engine.lexical = AsyncMock(return_value={'bm25_tr': [hit]})
    engine.vector = AsyncMock(return_value=[hit])
    engine.rerank = AsyncMock(return_value=[{**hit, 'rerank_score': score}])
    engine.start = AsyncMock()

    _, meta = await engine.search('query', rerank=True)
    assert ('weak_relevance' in meta['warnings']) is expect_warning
    assert meta['reranked'] is not expect_warning
