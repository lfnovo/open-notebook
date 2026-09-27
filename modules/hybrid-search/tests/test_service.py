"""Failure-path contracts; ranking quality is measured by integration.py."""
from unittest.mock import AsyncMock, patch
import pytest
from open_notebook.modules.hybrid_search import service
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError

# Both retrieval channels always select doc_hash; the row shape must include it.
ROW={'id':'hs:1','doc_id':'note:a','parent_id':'note:a','title':'Example','kind':'note','doc_hash':'hash','content':'AB-123 answer','start':0,'end':13,'sha256':'body','rrf_score':.1,'channels':['vector']}

@pytest.fixture
def engine(monkeypatch):
 monkeypatch.setattr(service,'settings',lambda:service.DEFAULTS.copy())
 e=service.HybridSearch(query=AsyncMock(return_value=[{'doc_id':'note:a','doc_hash':'hash'}]))
 e.active=AsyncMock(return_value={'table':'hs_p_a','signature':'same','model':'example'})
 e.metadata=AsyncMock(return_value=[{'id':'note:a','parent_id':'note:a','kind':'note','doc_hash':'hash'}])
 e.model=AsyncMock(return_value=('same',None))
 e.lexical=AsyncMock(return_value={'bm25_tr':[ROW]})
 e.vector=AsyncMock(return_value=[ROW]);e.rerank=AsyncMock(return_value=[ROW]);e.start=AsyncMock()
 return e

@pytest.mark.asyncio
async def test_vector_failure_is_explicit_but_text_survives(engine):
 engine.vector.side_effect=TimeoutError()
 rows,meta=await engine.search('AB-123',rerank=False)
 assert rows and meta['warnings']==['vector_unavailable']

@pytest.mark.asyncio
async def test_lexical_failure_is_explicit_but_vector_survives(engine):
 engine.lexical.side_effect=RuntimeError()
 rows,meta=await engine.search('AB-123',rerank=False)
 assert rows and meta['warnings']==['lexical_unavailable']

@pytest.mark.asyncio
async def test_total_failure_never_masquerades_as_no_matches(engine):
 engine.lexical.side_effect=RuntimeError();engine.vector.side_effect=TimeoutError()
 with pytest.raises(DatabaseOperationError):await engine.search('AB-123')

@pytest.mark.asyncio
async def test_reranker_failure_retains_fused_order(engine):
 engine.rerank.side_effect=TimeoutError()
 rows,meta=await engine.search('AB-123')
 assert rows and meta['warnings']==['reranker_unavailable'] and not meta['reranked']

@pytest.mark.asyncio
async def test_embedding_change_never_searches_old_vector_space(engine):
 engine.model.return_value=('changed',None)
 rows,meta=await engine.search('AB-123',rerank=False)
 engine.vector.assert_not_called();engine.start.assert_awaited_once()
 assert rows and 'embedding_changed' in meta['warnings']

@pytest.mark.asyncio
async def test_same_text_in_other_doc_does_not_cross_scope(engine):
 engine.lexical.return_value={'bm25_tr':[{**ROW,'doc_id':'note:secret'}]}
 engine.vector.return_value=[]
 rows,_=await engine.search('AB-123',rerank=False)
 assert not rows

@pytest.mark.asyncio
async def test_source_type_filter_and_no_locations(engine):
 rows,_=await engine.search('AB-123',source=False,note=False,rerank=False)
 assert not rows

@pytest.mark.asyncio
async def test_pending_doc_excluded_and_background_refresh_started(engine):
 engine.metadata.return_value[0]['doc_hash']='changed'
 rows,meta=await engine.search('AB-123',rerank=False)
 assert not rows and meta['pending_documents']==1
 engine.start.assert_awaited_once()

@pytest.mark.asyncio
@pytest.mark.parametrize('text',[' ','x'*4001])
async def test_query_limits(engine,text):
 with pytest.raises(InvalidInputError):await engine.search(text)

@pytest.mark.asyncio
async def test_checks_later_statement_failures():
 connection=AsyncMock();connection.query_raw.return_value={'result':[{'status':'OK','result':None},{'status':'ERR','result':'fixture failure'}]}
 from contextlib import asynccontextmanager
 @asynccontextmanager
 async def mock_connection():yield connection
 with patch.object(service,'db_connection',mock_connection):
  with pytest.raises(DatabaseOperationError):await service.checked_query('DDL; DDL;')

@pytest.mark.asyncio
async def test_neural_weak_match_abstains_without_discarding_evidence(engine):
 engine.rerank.return_value=[{**ROW,'rerank_score':.00001}]
 rows,meta=await engine.search('AB-123')
 assert rows and 'weak_relevance' in meta['warnings'] and not meta['reranked']

@pytest.mark.asyncio
async def test_ask_uses_hybrid_scoped_evidence_and_returns_diagnostics(monkeypatch):
 from open_notebook.graphs import ask
 from unittest.mock import MagicMock
 monkeypatch.setattr(ask.SearchAdapter,'enabled',lambda:True)
 fake=MagicMock();fake.search=AsyncMock(return_value=([{'id':'note:a','matches':['evidence']}],{'warnings':[]}))
 monkeypatch.setattr(ask.SearchAdapter,'engine',lambda:fake)
 monkeypatch.setattr(service,'settings',lambda:service.DEFAULTS.copy())
 model=MagicMock();model.ainvoke=AsyncMock(return_value=MagicMock(content='Supported [note:a]'))
 monkeypatch.setattr(ask,'provision_langchain_model',AsyncMock(return_value=model))
 value=await ask.provide_answer({'question':'question','term':'query','instructions':'extract','notebook_ids':['notebook:a']},{'configurable':{}})
 assert fake.search.call_args.args[-1]==['notebook:a']
 assert value['retrieval']==[{'warnings':[]}]
 assert value['answers']==['Supported [note:a]']

@pytest.mark.parametrize('text,allowed',[('Fake [source:nope]',['source:yes']),('Fake [note:secret]',[])])
def test_unknown_citation_rejected(text,allowed):
 from open_notebook.graphs.ask import validate_citations
 from open_notebook.exceptions import ExternalServiceError
 with pytest.raises(ExternalServiceError):validate_citations(text,allowed)

@pytest.mark.asyncio
async def test_unpublished_partial_document_never_reaches_search(engine):
 engine.query.return_value=[]
 rows,meta=await engine.search('AB-123',rerank=False)
 assert rows==[] and 'index_updating' in meta['warnings']
 engine.start.assert_awaited()

@pytest.mark.asyncio
async def test_publication_lookup_failure_never_returns_unverified_parts(engine):
 engine.query.side_effect=DatabaseOperationError('unavailable')
 with pytest.raises(DatabaseOperationError):await engine.search('AB-123',rerank=False)
