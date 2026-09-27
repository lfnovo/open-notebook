"""Disposable SurrealDB 2.6 test. No models, original records, or live database."""
import asyncio, json, os, time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from open_notebook.database.repository import ensure_record_id
from open_notebook.modules.hybrid_search import service
from open_notebook.modules.hybrid_search.storage import PassageWriter

assert os.environ.get('SURREAL_DATABASE') == 'hybrid_validation_bounded'
assert os.environ.get('SURREAL_URL') == 'ws://hybrid-index-validation-db:8000/rpc'

async def main():
    service.settings=lambda:service.DEFAULTS.copy()
    q=service.checked_query;table='hs_p_bounded';engine=service.HybridSearch(query=q)
    await engine.prepare(table,768)
    def rows(version,n):
        return [{'id':ensure_record_id(f'{table}:{version}{i}'),'doc_id':'note:a','parent_id':'note:a',
                 'kind':'note','title':'Fixture','doc_hash':version,'part':i,
                 'content':('Safe complete evidence token%04d. '%i)*40,'start':i,'end':i+1,'sha256':str(i),
                 'search_tr':('Safe complete evidence token%04d. '%i)*40,'search_en':('Safe complete evidence token%04d. '%i)*40,
                 'embedding':[.01 + (i%31)/1000]*768} for i in range(n)]
    events=[];failure={'insert':None,'calls':0}
    async def audited(sql,v=None):
        if sql.startswith('INSERT'):
            failure['calls']+=1
            assert len(v['rows'])<=16
            if failure['calls']==failure['insert']:raise RuntimeError('injected interruption')
            events.append(len(v['rows']))
        if sql.startswith('DELETE $ids'):assert len(v['ids'])<=16
        return await q(sql,v)
    w=PassageWriter(audited,ensure_record_id)
    await w.replace(table,'note:a','old',rows('old',35))
    failure.update(insert=failure['calls']+2)
    try:await w.replace(table,'note:a','new',rows('new',3386))
    except RuntimeError:pass
    else:raise AssertionError('Failure was not injected')
    marker=(await q('SELECT * FROM $id',{'id':w.metadata_id(table,'note:a')}))[0]
    assert marker['doc_hash']=='old'
    candidate=rows('new',1)[0];candidate['id']=str(candidate['id'])
    engine.active=AsyncMock(return_value={'table':table,'signature':'test','model':'fixture'})
    engine.metadata=AsyncMock(return_value=[{'id':'note:a','parent_id':'note:a','kind':'note','doc_hash':'new'}])
    engine.model=AsyncMock(return_value=('test',SimpleNamespace(name='fixture')))
    engine.lexical=AsyncMock(return_value={'bm25_en':[candidate]});engine.vector=AsyncMock(return_value=[]);engine.start=AsyncMock()
    found,meta=await engine.search('evidence',rerank=False)
    assert found==[] and 'index_updating' in meta['warnings']
    failure['insert']=None;started=time.monotonic()
    await w.replace(table,'note:a','new',rows('new',3386))
    print('Complete document published; checking and pruning',flush=True)
    marker=(await q('SELECT * FROM $id',{'id':w.metadata_id(table,'note:a')}))[0]
    assert marker['doc_hash']=='new' and marker['parts']==3386 and not marker['cleanup_pending']
    found,meta=await engine.search('evidence',rerank=False);assert len(found)==1
    stored=await q(f'SELECT count() AS n FROM {table} GROUP ALL');assert stored[0]['n']==3386
    # Cleanup uses the same bounded path when an original document is deleted.
    await w.prune(table,'doc_id=$doc',{'doc':'note:a'})
    assert not await q(f'SELECT id FROM {table} LIMIT 1')
    print(json.dumps({'status':'passed','passages':3386,'max_insert_rows':max(events),
        'insert_requests':len(events),'interruption_hidden':True,'resume_complete':True,
        'bounded_delete':True,'seconds':round(time.monotonic()-started,2)}),flush=True)

asyncio.run(main())
