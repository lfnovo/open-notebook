import asyncio
import pytest
from engine import ServiceError
from test_workflow import engine, create, add, settle
from workflow import STAGES

async def parallel(engine):
    for sid in ('synthesis_chatgpt','synthesis_claude'):engine.provider.gates[sid]=asyncio.Event()
    run=await create(engine)
    for sid,_,rnd,_ in STAGES:
        if rnd<=2:await add(engine,run['id'],sid)
    for _ in range(100):
        run=await engine.get(run['id'])
        if sum(bool(s.get('request_dispatched')) for s in run['stages'])==2:return run
        await asyncio.sleep(.01)
    assert False

async def control(engine,run,sid,action):
    await engine.stage_action(run['id'],sid,action,engine.stage_snapshot(run,engine.stage(run,sid)))
    await asyncio.gather(*engine.control_tasks.values())
    return await engine.get(run['id'])

@pytest.mark.asyncio
async def test_stage_stop_cancels_only_target_and_preserves_sibling(engine):
    cancelled=[]
    async def cancel(s):cancelled.append(s['id'])
    engine.provider.cancel=cancel
    run=await parallel(engine);rid=run['id'];saved=[s['report'] for s in run['stages'][:5]]
    run=await control(engine,run,'synthesis_chatgpt','stop')
    assert cancelled==['synthesis_chatgpt'] and not run['paused']
    assert engine.stage(run,'synthesis_claude')['status']=='running'
    assert engine.stage(run,'synthesis_chatgpt')['control_state']=='stopped'
    assert not await engine.sweep_retries()
    await engine.kick(rid)
    assert len(engine.provider.calls)==2
    engine.provider.gates['synthesis_claude'].set();await settle(engine)
    assert engine.stage(await engine.get(rid),'final_chatgpt')['status']=='pending'
    engine.provider.gates['synthesis_chatgpt'].set()
    run=await engine.get(rid);await control(engine,run,'synthesis_chatgpt','resume');await settle(engine)
    run=await engine.get(rid);assert run['status']=='completed'
    assert [s['report'] for s in run['stages'][:5]]==saved
    assert [c[0] for c in engine.provider.calls].count('synthesis_claude')==1

@pytest.mark.asyncio
async def test_retry_while_sibling_running_and_snapshot_ignores_sibling_progress(engine):
    run=await parallel(engine);rid=run['id']
    engine.provider.fail.add('synthesis_chatgpt');engine.provider.gates['synthesis_chatgpt'].set()
    await asyncio.sleep(.06);run=await engine.get(rid)
    assert engine.stage(run,'synthesis_chatgpt')['status']=='failed'
    snapshot=engine.stage_snapshot(run,engine.stage(run,'synthesis_chatgpt'))
    engine.provider.fail.clear()
    await engine.stage_action(rid,'synthesis_chatgpt','retry',snapshot)
    await asyncio.sleep(.04)
    run=await engine.get(rid)
    assert engine.stage(run,'synthesis_chatgpt')['status']=='completed'
    assert engine.stage(run,'synthesis_claude')['status']=='running'
    assert [c[0] for c in engine.provider.calls].count('synthesis_claude')==1
    with pytest.raises(ServiceError):await engine.stage_action(rid,'synthesis_chatgpt','retry',snapshot)

@pytest.mark.asyncio
async def test_hold_survives_restart_and_whole_resume_does_not_clear_it(engine):
    run=await create(engine);rid=run['id']
    run=await control(engine,run,'research_chatgpt','cancel')
    await engine.recover();run=await engine.get(rid)
    assert engine.stage(run,'research_chatgpt')['control_state']=='cancelled'
    await engine.action(rid,'pause');await engine.action(rid,'resume')
    run=await engine.get(rid);assert engine.stage(run,'research_chatgpt')['control_state']=='cancelled'
    with pytest.raises(ServiceError):await engine.stage_action(rid,'research_chatgpt','resume')
    run=await control(engine,run,'research_chatgpt','restore')
    assert engine.stage(run,'research_chatgpt')['status']=='waiting_input'

@pytest.mark.asyncio
async def test_stage_route_requires_fresh_confirmation(engine,monkeypatch):
    import httpx,server
    monkeypatch.setattr(server,'ENGINE',engine)
    run=await create(engine);sid='research_chatgpt'
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as c:
        url=f"/runs/{run['id']}/stages/{sid}/actions/pause"
        assert (await c.post(url,json={})).status_code==401
        c.headers['Authorization']='Bearer '+server.KEY
        assert (await c.post(url,json={})).status_code==409
        snap=engine.stage_snapshot(run,engine.stage(run,sid))
        assert (await c.post(url,json={'expected_state':snap})).status_code==200
        await asyncio.gather(*engine.control_tasks.values())
        assert (await c.post(url,json={'expected_state':snap})).status_code==409

@pytest.mark.asyncio
async def test_import_into_paused_stage_clears_hold_without_losing_report(engine):
    run=await create(engine);rid=run['id'];sid='research_chatgpt'
    run=await control(engine,run,sid,'pause')
    await add(engine,rid,sid)
    stage=engine.stage(await engine.get(rid),sid)
    assert stage['status']=='completed' and not stage['control_state'] and stage['report']

@pytest.mark.asyncio
async def test_cancelled_stage_cannot_be_bypassed_by_import(engine):
    run=await create(engine);rid=run['id'];sid='research_chatgpt'
    await control(engine,run,sid,'cancel')
    with pytest.raises(ServiceError):await add(engine,rid,sid)

@pytest.mark.asyncio
async def test_explicit_skip_preserves_reports_and_unblocks_preliminary_merge(engine):
    import copy
    from workflow import report_packet
    engine.provider.fail.add('pre_research_gemini')
    run=await engine.create({'question':'Research this subject','scope':'','language':'English',
        'preliminary':True,'auto_synthesize':False,'execution_mode':'imports'},'skip-preliminary')
    await settle(engine);run=await engine.get(run['id'])
    saved=copy.deepcopy([s['report'] for s in run['stages'][1:3]])
    run=await control(engine,run,'pre_research_gemini','skip');await settle(engine)
    run=await engine.get(run['id']);skipped=engine.stage(run,'pre_research_gemini')
    assert skipped['status']=='skipped' and skipped['report'] is None
    assert skipped['skip']['previous_status']=='failed'
    assert skipped['next_retry_at'] is None and skipped['control_state'] is None
    assert [s['report'] for s in run['stages'][1:3]]==saved
    assert engine.stage(run,'pre_brief_chatgpt')['status']=='completed'
    prompt=next(p for sid,p in engine.provider.calls if sid=='pre_brief_chatgpt')
    packet=report_packet(run,engine.stage(run,'pre_brief_chatgpt'))
    assert len(packet['reports'])==2
    assert (await engine.packet(run['id'],'pre_brief_chatgpt'))['report_count']==2
    assert packet['skipped_stages'][0]['stage']=='pre_research_gemini'
    from token_budget import TokenBudget
    engine.budget=TokenBudget(len)
    plan=await engine.context_plan(run['id'])
    assert 'pre_research_gemini' not in [row['stage_id'] for row in plan['stages']]
    assert 'skipped_stages' in prompt and 'Gemini' in prompt
    assert 'Üç bağımsız ön araştırma' not in prompt
    assert not await engine.sweep_retries()
    await engine.recover()
    for action in ('retry','resume','restore','skip'):
        with pytest.raises(ServiceError):await control(engine,await engine.get(run['id']),'pre_research_gemini',action)
    with pytest.raises(ServiceError):await add(engine,run['id'],'pre_research_gemini')

@pytest.mark.asyncio
async def test_skip_requires_completed_peer_and_never_changes_frozen_downstream_input(engine):
    run=await create(engine)
    with pytest.raises(ServiceError):await control(engine,run,'research_gemini','skip')
    await add(engine,run['id'],'research_chatgpt')
    await settle(engine)
    run=await engine.get(run['id'])
    engine.stage(run,'review_chatgpt')['attempts']=1
    await engine.store.save(run)
    with pytest.raises(ServiceError):await control(engine,run,'research_gemini','skip')
    engine.stage(run,'review_chatgpt')['attempts']=0
    await engine.store.save(run)
    run=await control(engine,run,'research_gemini','skip')
    with pytest.raises(ServiceError):await control(engine,run,'final_chatgpt','skip')

@pytest.mark.asyncio
async def test_running_stage_must_be_stopped_before_skip(engine):
    run=await parallel(engine)
    with pytest.raises(ServiceError):await control(engine,run,'synthesis_chatgpt','skip')


@pytest.mark.asyncio
async def test_resuming_multipart_stage_keeps_live_cancellation_target(engine,monkeypatch):
    from unittest.mock import AsyncMock
    run=await engine.create({'question':'Research this subject','scope':'','language':'English',
        'auto_synthesize':False,'execution_mode':'imports'},'retain-request-target')
    for sid,_,rnd,_ in STAGES:
        if rnd<=2:await add(engine,run['id'],sid)
    await settle(engine)
    run=await engine.get(run['id']);stage=engine.stage(run,'synthesis_chatgpt')
    stage.update(status='ready',request_id='a'*32,request_dispatched=True,attempts=1)
    run['auto_synthesize']=True
    await engine.store.save(run)
    monkeypatch.setattr(engine,'preparation_plan',lambda *a:{'version':'test-plan'})
    monkeypatch.setattr(engine,'execute',AsyncMock())
    await engine.kick(run['id'])
    current=engine.stage(await engine.get(run['id']),'synthesis_chatgpt')
    assert current['request_id']=='a'*32 and current['request_dispatched'] is True
