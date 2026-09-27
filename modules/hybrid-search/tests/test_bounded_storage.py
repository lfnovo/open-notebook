"""A failed partial index must not publish or delete the last completed version."""
import copy
import pytest
from open_notebook.modules.hybrid_search.storage import PassageWriter, batches


def rows(n=39):
    return [{'id':f'hs_p_test:new{i}','doc_id':'note:a','doc_hash':'new','part':i,
             'content':'Preserved source text.','embedding':[.1,.2]} for i in range(n)]


class Database:
    def __init__(self):
        self.rows={f'hs_p_test:old{i}':dict(id=f'hs_p_test:old{i}',doc_id='note:a',doc_hash='old') for i in range(35)}
        self.meta={'doc_hash':'old'};self.calls=[];self.fail_at=None;self.insertions=0
    async def query(self,sql,v):
        self.calls.append((sql,copy.deepcopy(v)))
        if sql.startswith('INSERT IGNORE'):
            self.insertions+=1
            if self.insertions==self.fail_at:raise RuntimeError('connection lost')
            for r in v['rows']:self.rows.setdefault(str(r['id']),copy.deepcopy(r))
            return []
        if sql.startswith('SELECT id,doc_id,doc_hash,part'):
            return [self.rows[str(i)] for i in v['ids'] if str(i) in self.rows]
        if 'publish complete document' in sql:
            count=sum(r['doc_id']==v['doc'] and r['doc_hash']==v['hash'] for r in self.rows.values())
            if count!=v['expected']:raise RuntimeError('incomplete coverage')
            self.meta=copy.deepcopy(v['meta']);return []
        if sql.startswith('SELECT VALUE id'):
            return [r['id'] for r in self.rows.values() if r['doc_id']==v['doc'] and r['doc_hash']!=v['hash']][:16]
        if sql.startswith('DELETE $ids'):
            assert len(v['ids'])<=16
            for i in v['ids']:self.rows.pop(str(i),None)
            return []
        if sql.startswith('UPDATE $record'):
            self.meta['cleanup_pending']=False;return []
        raise AssertionError(sql)


@pytest.mark.asyncio
async def test_large_replacement_is_bounded_and_complete_before_publication():
    db=Database();w=PassageWriter(db.query,lambda x:x);payload=rows(3386)
    await w.replace('hs_p_test','note:a','new',payload)
    assert db.meta['parts']==3386 and db.meta['doc_hash']=='new'
    assert not db.meta['cleanup_pending'] and len(db.rows)==3386
    writes=[v['rows'] for s,v in db.calls if s.startswith('INSERT')]
    assert max(map(len,writes))<=16
    assert [r for batch in writes for r in batch]==payload
    published=next(i for i,(s,v) in enumerate(db.calls) if 'publish complete document' in s)
    assert all(not s.startswith('DELETE') for s,v in db.calls[:published])


@pytest.mark.asyncio
async def test_interruption_preserves_old_version_and_replay_is_idempotent():
    db=Database();db.fail_at=2;w=PassageWriter(db.query,lambda x:x)
    with pytest.raises(RuntimeError):await w.replace('hs_p_test','note:a','new',rows())
    assert db.meta=={'doc_hash':'old'} and sum(r['doc_hash']=='old' for r in db.rows.values())==35
    db.fail_at=None
    await w.replace('hs_p_test','note:a','new',rows())
    assert len(db.rows)==39 and db.meta['parts']==39
    await w.replace('hs_p_test','note:a','new',rows())
    assert len(db.rows)==39


@pytest.mark.asyncio
async def test_missing_persisted_row_never_publishes():
    db=Database();original=db.query
    async def drop(sql,v):
        result=await original(sql,v)
        if sql.startswith('SELECT id,doc_id,doc_hash,part'):return result[:-1]
        return result
    with pytest.raises(ValueError):await PassageWriter(drop,lambda x:x).replace('hs_p_test','note:a','new',rows())
    assert db.meta=={'doc_hash':'old'}


@pytest.mark.parametrize('bad', ['table','duplicate','hash','doc','oversized'])
@pytest.mark.asyncio
async def test_invalid_payload_fails_before_any_write(bad):
    db=Database();data=rows();table='hs_p_test'
    if bad=='table':table='note'
    elif bad=='duplicate':data[1]['id']=data[0]['id']
    elif bad=='hash':data[0]['doc_hash']='other'
    elif bad=='doc':data[0]['doc_id']='note:b'
    else:data[0]['content']='x'*(1024*1024)
    with pytest.raises(ValueError):await PassageWriter(db.query,lambda x:x).replace(table,'note:a','new',data)
    assert not db.calls


def test_byte_limit_never_splits_or_drops_a_record():
    data=[{'content':'ü'*20000} for _ in range(40)]
    groups=list(batches(data))
    assert [r for g in groups for r in g]==data and max(map(len,groups))<16


@pytest.mark.asyncio
async def test_cleanup_failure_leaves_complete_marker_and_can_resume():
    db=Database();original=db.query;fail=True
    async def interrupted(sql,v):
        if fail and sql.startswith('DELETE $ids'):
            raise RuntimeError('cleanup disconnected')
        return await original(sql,v)
    w=PassageWriter(interrupted,lambda x:x)
    with pytest.raises(RuntimeError):
        await w.replace('hs_p_test','note:a','new',rows())
    assert db.meta['doc_hash']=='new' and db.meta['parts']==39 and db.meta['cleanup_pending']
    assert len(db.rows)==74
    fail=False
    await w.cleanup('hs_p_test','note:a','new')
    assert len(db.rows)==39 and not db.meta['cleanup_pending']


@pytest.mark.asyncio
async def test_final_coverage_failure_preserves_last_completed_version():
    db=Database();original=db.query
    async def lose_row_before_publish(sql,v):
        if 'publish complete document' in sql:
            db.rows.pop('hs_p_test:new0')
        return await original(sql,v)
    with pytest.raises(RuntimeError):
        await PassageWriter(lose_row_before_publish,lambda x:x).replace('hs_p_test','note:a','new',rows())
    assert db.meta=={'doc_hash':'old'} and all(f'hs_p_test:old{i}' in db.rows for i in range(35))


@pytest.mark.parametrize('identifiers', [['note:a'], ['hs_p_test:x']*2, [f'hs_p_test:{i}' for i in range(17)]])
@pytest.mark.asyncio
async def test_cleanup_rejects_invalid_or_unbounded_result(identifiers):
    deleted=[]
    async def query(sql,v):
        if sql.startswith('SELECT'):return identifiers
        deleted.append(v)
    with pytest.raises(ValueError):
        await PassageWriter(query,lambda x:x).prune('hs_p_test','doc_id=$doc',{'doc':'note:a'})
    assert not deleted


@pytest.mark.asyncio
async def test_cleanup_stops_when_delete_makes_no_progress():
    deleted=[]
    async def query(sql,v):
        if sql.startswith('SELECT'):return ['hs_p_test:x']
        deleted.append(v)
    with pytest.raises(ValueError):
        await PassageWriter(query,lambda x:x).prune('hs_p_test','doc_id=$doc',{'doc':'note:a'})
    assert len(deleted)==1
