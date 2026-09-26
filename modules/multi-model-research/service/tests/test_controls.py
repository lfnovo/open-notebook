import asyncio
import uuid
import pytest
from engine import ServiceError
from test_workflow import engine, settle, create, add
from workflow import STAGES


@pytest.mark.asyncio
async def test_maintenance_resume_preserves_attention_then_retries_only_selected_stage(engine, monkeypatch):
    import httpx, server
    run = await create(engine, False); rid = run['id']
    for sid, _, rnd, _ in STAGES:
        if rnd <= 2: await add(engine, rid, sid)
    await settle(engine)
    run = await engine.get(rid)
    run['paused'] = True
    engine.stage(run, 'synthesis_chatgpt').update(status='integrity_error', error='Unprovided URL')
    engine.stage(run, 'synthesis_claude').update(status='research_unavailable', error='Provider refusal', attempts=4)
    from workflow import refresh_status
    refresh_status(run); await engine.store.save(run)
    run = await engine.get(rid)
    monkeypatch.setattr(server, 'ENGINE', engine)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='http://test',
                                headers={'Authorization': 'Bearer ' + server.KEY}) as client:
        result = await client.post(f'/runs/{rid}/resume', json={
            'expected_state': engine.control_snapshot(run), 'retry_attention': False})
        assert result.status_code == 200
    await settle(engine)
    run = await engine.get(rid)
    assert not run['paused'] and not engine.provider.calls
    claude = dict(engine.stage(run, 'synthesis_claude'))
    assert claude['status'] == 'research_unavailable' and claude['error'] == 'Provider refusal'
    await engine.retry_stage(rid, 'synthesis_chatgpt', engine.stage_snapshot(run, engine.stage(run, 'synthesis_chatgpt')))
    await settle(engine)
    run = await engine.get(rid)
    assert engine.stage(run, 'synthesis_claude') == claude
    assert [c[0] for c in engine.provider.calls] == ['synthesis_chatgpt']

async def active(engine):
    engine.provider.gates['synthesis_claude']=asyncio.Event()
    run=await create(engine)
    for sid,_,rnd,_ in STAGES:
        if rnd<=2:await add(engine,run['id'],sid)
    for _ in range(100):
        run=await engine.get(run['id'])
        if sum(s['status']=='completed' for s in run['stages'])==6 and any(s.get('request_dispatched') and s['provider']=='Claude' for s in run['stages']):return run
        await asyncio.sleep(.01)
    raise AssertionError('fixture not running')

async def stopped(engine,rid,action='stop'):
    result=await engine.action(rid,action)
    assert result['status']=='stopping'
    await asyncio.gather(*engine.control_tasks.values())
    return await engine.get(rid)

@pytest.mark.asyncio
async def test_stop_cancels_exact_request_then_resume_preserves_reports(engine):
    cancelled=[]
    async def cancel(stage):cancelled.append(stage['request_id'])
    engine.provider.cancel=cancel
    run=await active(engine);before={s['id']:s['report']['sha256'] for s in run['stages'] if s['report']}
    result=await stopped(engine,run['id'])
    assert result['status']=='stopped' and result['paused'] and len(cancelled)==1
    assert not engine.tasks and not await engine.sweep_retries()
    with pytest.raises(ServiceError):await engine.retry_stage(run['id'],'synthesis_claude')
    engine.provider.gates.clear()
    await engine.action(run['id'],'resume');await settle(engine)
    after=await engine.get(run['id']);assert after['status']=='completed'
    for s in after['stages']:
        if s['id'] in before:assert s['report']['sha256']==before[s['id']]
    assert [c[0] for c in engine.provider.calls].count('synthesis_chatgpt')==1
    assert next(s for s in after['stages'] if s['id']=='synthesis_claude')['request_id']!=cancelled[0]

@pytest.mark.asyncio
async def test_cancel_requires_explicit_restore_and_survives_recovery(engine):
    async def cancel(stage):pass
    engine.provider.cancel=cancel
    run=await active(engine);result=await stopped(engine,run['id'],'cancel')
    assert result['status']=='cancelled'
    await engine.recover();assert (await engine.get(run['id']))['status']=='cancelled'
    for action in ('resume','pause','automate'):
        with pytest.raises(ServiceError):await engine.action(run['id'],action)
    engine.provider.gates.clear()
    await engine.action(run['id'],'restore');await settle(engine)
    assert (await engine.get(run['id']))['status']=='completed'

@pytest.mark.asyncio
async def test_stop_failure_blocks_resume_and_can_be_retried(engine):
    async def fail(stage):raise ServiceError('Bridge unavailable',503)
    engine.provider.cancel=fail
    run=await active(engine);result=await stopped(engine,run['id'])
    assert result['status']=='stop_failed' and result['control_error']=='Bridge unavailable'
    with pytest.raises(ServiceError):await engine.action(run['id'],'resume')
    async def cancel(stage):pass
    engine.provider.cancel=cancel
    assert (await stopped(engine,run['id']))['status']=='stopped'

@pytest.mark.asyncio
async def test_pause_allows_current_report_to_finish_but_no_next_stage(engine):
    run=await active(engine)
    await engine.action(run['id'],'pause')
    with pytest.raises(ServiceError):await engine.action(run['id'],'resume')
    engine.provider.gates['synthesis_claude'].set();await settle(engine)
    run=await engine.get(run['id']);assert run['status']=='paused'
    assert sum(s['status']=='completed' for s in run['stages'])==7
    assert 'final_chatgpt' not in [c[0] for c in engine.provider.calls]

@pytest.mark.asyncio
async def test_finish_during_stop_keeps_report_and_cannot_launch_next(engine):
    run=await active(engine)
    async def cancel(stage):
        engine.provider.gates['synthesis_claude'].set()
        await asyncio.sleep(.05)
    engine.provider.cancel=cancel
    result=await stopped(engine,run['id'])
    assert sum(s['status']=='completed' for s in result['stages'])==7
    assert not engine.tasks
    assert 'final_chatgpt' not in [c[0] for c in engine.provider.calls]

@pytest.mark.asyncio
async def test_browser_stop_preserves_journal_and_resumes_same_job(engine):
    class Browser:
        def __init__(self):self.calls=[];self.gate=asyncio.Event()
        async def research(self,rid,stage,prompt,progress):
            self.calls.append((rid,stage['id'],prompt))
            await self.gate.wait()
            return {'content':'Research https://example.org','url':'https://example.org/chat'}
        def can_resume(self,*args):return True
        def artifacts(self,*args):return []
        async def close(self):pass
    engine.browser=Browser()
    run=await engine.create({'question':'Browser question','scope':'','language':'English','auto_synthesize':False,'execution_mode':'browser','notebook_id':None},uuid.uuid4().hex)
    await asyncio.sleep(.05)
    before=list(engine.browser.calls);assert len(before)==3
    await stopped(engine,run['id']);assert len(engine.browser.calls)==3
    await engine.action(run['id'],'resume');await asyncio.sleep(.05)
    assert engine.browser.calls[3:]==before

@pytest.mark.asyncio
async def test_control_endpoint_is_authenticated_and_returns_before_cancellation(engine,monkeypatch):
    import httpx,server
    monkeypatch.setattr(server,'ENGINE',engine)
    gate=asyncio.Event()
    async def cancel(stage):await gate.wait()
    engine.provider.cancel=cancel
    run=await active(engine);rid=run['id']
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as client:
        assert (await client.post(f'/runs/{rid}/stop')).status_code==401
        client.headers['Authorization']='Bearer '+server.KEY
        response=await asyncio.wait_for(client.post(f'/runs/{rid}/stop'),1)
        assert response.status_code==200 and response.json()['status']=='stopping'
        assert (await client.post(f'/runs/{rid}/resume')).status_code==409
        assert (await client.post(f'/runs/{rid}/stop')).json()['status']=='stopping'
        gate.set();await asyncio.gather(*engine.control_tasks.values())
        assert (await client.get(f'/runs/{rid}')).json()['status']=='stopped'

@pytest.mark.asyncio
async def test_stale_confirmation_is_rejected_before_any_side_effect(engine):
    run=await active(engine);snapshot=engine.control_snapshot(run)
    await engine.action(run['id'],'pause')
    with pytest.raises(ServiceError,match='durumu değişti'):
        await engine.action(run['id'],'stop',snapshot)
    after=await engine.get(run['id']);assert not after.get('control_state')
    assert after['paused'] and engine.tasks
