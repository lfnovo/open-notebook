import json
import pytest
from context_preparation import plan_segments, validate_plan, render_segment, parse_result, PreparationError


def test_plan_covers_every_byte_in_order_including_unicode_and_crlf():
    text = ('Koşul: yalnız yetişkinler; çocuklarda yasak.\r\n' * 200)
    plan = plan_segments(text, lambda s: len(s) <= 1800)
    assert len(plan['parts']) > 1
    assert ''.join(p['text'] for p in plan['parts']) == text
    assert validate_plan(plan, text)
    assert all(len(render_segment(p, plan)) <= 1800 for p in plan['parts'])


def test_omitted_duplicate_reordered_or_changed_part_fails_closed():
    import copy
    text = 'Evidence unique context.\n' * 800
    original = plan_segments(text, lambda s: len(s) <= 1800)
    for mutate in (lambda p:p['parts'].pop(), lambda p:p['parts'].reverse(),
                   lambda p:p['parts'].append(p['parts'][0]),
                   lambda p:p['parts'][0].update(text='Wrong')):
        plan = copy.deepcopy(original); mutate(plan)
        with pytest.raises(PreparationError): validate_plan(plan,text)


def test_an_unreachable_budget_makes_no_partial_plan():
    with pytest.raises(PreparationError):plan_segments('x',lambda s:False)


def test_result_must_account_for_exact_expected_parts_and_have_a_report():
    assert parse_result(json.dumps({'coverage':['P1'],'report':'A finding.'}),['P1']) == 'A finding.'
    for coverage,report in [([], 'x'),(['P1','P2'],'x'),(['P1','P1'],'x'),(['P1'],'')]:
        with pytest.raises(PreparationError):parse_result(json.dumps({'coverage':coverage,'report':report}),['P1'])

@pytest.mark.asyncio
@pytest.mark.parametrize('answer',['Preserved findings and limitations.','See https://invented.invalid/source','connection_lost','recover_receipt'])
async def test_execution_records_all_parts_and_reuses_completed_calls(tmp_path,answer):
    import asyncio
    import re
    from types import SimpleNamespace
    import segmented_execution
    from context_preparation import digest, envelope
    body=envelope('Condition and counter-evidence.\n'*300)
    prompt='Task\n'+body
    plan=plan_segments(body,lambda s:len(s)<=1800)
    plan['protected_register']={'claims':[{'id':'C1','status':'disputed','value':2.5,'unit':'percent','exception':'only when dry'}]}
    plan['source_inventory']=['https://example.org/evidence']
    run={'id':'r','paused':False,'stages':[{'id':'s','round':4,'provider':'ChatGPT'}]}
    stage=run['stages'][0]
    class Provider:
        calls=0
        requests=[]
        async def synthesize(self,stage,text):
            self.calls+=1
            self.requests.append(text)
            if answer in ('connection_lost','recover_receipt') and (answer=='connection_lost' or self.calls==1):raise OSError('Connection closed before receipt')
            ids=json.loads(re.search(r'exactly once: (\[.*?\])\.',text)[1])
            return json.dumps({'coverage':ids,'report':'Recovered findings.' if answer=='recover_receipt' else answer}),{'prompt_tokens':100}
    class Store:
        async def save(self,value):pass
    provider=Provider()
    class Engine:
        lock=asyncio.Lock();store=Store()
        async def get(self,rid):return run
        def stage(self,r,sid):return stage
        def input_path(self,r,s):return tmp_path/'input-packet.md'
        def measure_input(self,text,s):return {'fits':len(text)<=10000,'utilization':len(text)/10000}
    engine=Engine();engine.provider=provider
    journal=tmp_path/'segmented-journal.json'
    journal.write_text(json.dumps({'version':'segmented-evidence-v1','input_sha256':digest(prompt),'plan':plan,'jobs':{}}))
    if answer=='recover_receipt':
        from engine import ServiceError
        with pytest.raises(ServiceError):await segmented_execution.execute(engine,run,stage,prompt)
        async def recover(child,text):
            saved=json.loads(journal.read_text())['jobs']['map-P1']
            assert child['request_id']==saved['request_id']
            assert digest(text)==saved['input_sha256']
            return json.dumps({'coverage':['P1'],'report':'Recovered findings.'}),{'prompt_tokens':100}
        provider.recover=recover
        result,_=await segmented_execution.execute(engine,run,stage,prompt)
        assert result=='Recovered findings.'
        assert provider.calls==len(plan['parts'])+1  # One interrupted call, recovered without resubmission.
        assert json.loads(journal.read_text())['jobs']['map-P1']['status']=='completed'
        return
    if answer=='connection_lost':
        from engine import ServiceError
        with pytest.raises(ServiceError) as error:await segmented_execution.execute(engine,run,stage,prompt)
        assert error.value.kind=='submission_uncertain'
        with pytest.raises(ServiceError) as error:await segmented_execution.execute(engine,run,stage,prompt)
        assert error.value.kind=='submission_uncertain'
        assert provider.calls==1
        return
    if 'invented.invalid' in answer:
        from engine import ServiceError
        with pytest.raises(ServiceError) as error:await segmented_execution.execute(engine,run,stage,prompt)
        assert error.value.kind=='integrity_error'
        assert provider.calls==1
        return
    report,usage=await segmented_execution.execute(engine,run,stage,prompt)
    assert report=='Preserved findings and limitations.'
    assert usage['coverage']==[p['id'] for p in plan['parts']]
    assert provider.calls==len(plan['parts'])+1
    assert json.dumps(plan['protected_register'],separators=(',',':')) in provider.requests[-1]
    assert plan['source_inventory'][0] in provider.requests[-1]
    await segmented_execution.execute(engine,run,stage,prompt)
    assert provider.calls==len(plan['parts'])+1
    saved=json.loads(journal.read_text())
    key=next(iter(saved['jobs']));saved['jobs'][key]['status']='in_flight'
    journal.write_text(json.dumps(saved))
    from engine import ServiceError
    with pytest.raises(ServiceError) as error:await segmented_execution.execute(engine,run,stage,prompt)
    assert error.value.kind=='submission_uncertain'
    assert provider.calls==len(plan['parts'])+1
    # Only an explicitly confirmed stop clears uncertainty; other calls stay cached.
    stage['request_id']=saved['jobs'][key]['request_id']
    await segmented_execution.confirm_cancel(engine,run,stage)
    await segmented_execution.execute(engine,run,stage,prompt)
    assert provider.calls==len(plan['parts'])+2
    stage['preparation']=segmented_execution.summary(plan)
    saved=json.loads(journal.read_text())
    saved['plan']['protected_register']['claims'][0]['status']='accepted'
    journal.write_text(json.dumps(saved))
    with pytest.raises(ServiceError) as error:await segmented_execution.execute(engine,run,stage,prompt)
    assert error.value.kind=='integrity_error'
    assert provider.calls==len(plan['parts'])+2


def test_planner_reserves_a_final_call_before_dispatch(monkeypatch):
    import segmented_execution
    import workflow
    from types import SimpleNamespace
    from context_preparation import envelope
    stage={'round':3,'mode':'account'}
    run={'stages':[stage]}
    prompt='Task\n'+envelope('Evidence')
    monkeypatch.setattr(workflow,'prompt_for',lambda *a:prompt)
    monkeypatch.setattr(segmented_execution,'plan_segments',lambda *a,**kw:{'parts':[{}]*64})
    engine=SimpleNamespace(measure_input=lambda *a:{'fits':True,'utilization':.1})
    with pytest.raises(PreparationError,match='call limit'):
        segmented_execution.plan_for(engine,run,stage,prompt)
