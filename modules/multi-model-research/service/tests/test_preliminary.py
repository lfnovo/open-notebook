import asyncio
import pytest
from test_workflow import engine,settle,add
from workflow import ancestors

@pytest.mark.asyncio
async def test_preliminary_three_to_one_then_legacy_workflow(engine):
    gate=asyncio.Event();engine.provider.gates['pre_research_claude']=gate
    data={'question':'Original research question','scope':'Primary evidence','language':'Türkçe','preliminary':True,'auto_synthesize':False,'execution_mode':'imports'}
    run=await engine.create(data,'preliminary-test-1');rid=run['id'];assert len(run['stages'])==12
    await asyncio.sleep(.06);run=await engine.get(rid)
    assert {sid for sid,_ in engine.provider.calls}=={'pre_research_chatgpt','pre_research_claude','pre_research_gemini'}
    assert all(s['status']=='pending' for s in run['stages'][4:])
    for sid,prompt in engine.provider.calls:assert 'Synthesis pre_research_' not in prompt
    gate.set();await settle(engine);run=await engine.get(rid)
    assert [sid for sid,_ in engine.provider.calls][-1]=='pre_brief_chatgpt'
    assert run['question']==data['question']
    assert all(s['status']=='completed' for s in run['stages'][:4])
    packet=await engine.packet(rid,'research_gemini')
    for s in run['stages'][:4]:assert s['report']['content'] in packet['prompt']
    assert packet['report_count']==4
    for sid in ('research_gemini','research_chatgpt','research_claude','review_chatgpt','review_claude'):await add(engine,rid,sid)
    await engine.action(rid,'resume');await settle(engine)
    assert (await engine.get(rid))['question']==data['question']

@pytest.mark.asyncio
async def test_failed_preliminary_blocks_merge_and_preserves_siblings(engine):
    engine.provider.fail.add('pre_research_claude')
    run=await engine.create({'question':'Source based research','preliminary':True,'auto_synthesize':True,'execution_mode':'imports','language':'Türkçe','scope':''},'preliminary-test-2')
    await settle(engine);assert len(engine.provider.calls)==3
    engine.provider.fail.clear();await engine.action(run['id'],'resume');await settle(engine)
    names=[sid for sid,_ in engine.provider.calls]
    assert names.count('pre_research_chatgpt')==1 and names.count('pre_research_gemini')==1 and names.count('pre_research_claude')==2 and names.count('pre_brief_chatgpt')==1
