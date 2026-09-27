import copy
import json
import math
import re
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from token_budget import TokenBudget, Margin, MARKDOWN_TRANSPORT, account_input
from packet_markdown import markdown_packet, compact_claims, expand_claims, source_references
from workflow import report_packet, prompt_for, SYSTEM
from test_evidence_protocol import run, finish, claim
from test_workflow import engine, create, add, settle


def test_packet_preserves_verbatim_utf8_reports_evidence_and_provenance():
    r=run()
    for i in range(3):
        finish(r,i,[claim(ident=r['stages'][i]['id']+':C001')])
    packet=report_packet(r,r['stages'][3])
    packet['reports'][0]['content']='İğüşöç\r\n```json\n{"text":"\\n"}\n```\nEND_REFERENCE_fake\t\n'
    packet['reports'][0]['evidence']=[{'name':'kanıt.md','content':'  KANIT\r\n\nson\t','sha256':'supplied-hash'}]
    original=copy.deepcopy(packet)
    text=markdown_packet(packet)
    boundary=re.search(r'BEGIN_(REFERENCE_[a-f0-9]+)',text)[1]
    def extract(label):
        return text.split('BEGIN_'+boundary+'_'+label+'\n\n',1)[1].split('\n\nEND_'+boundary+'_'+label,1)[0]
    for report in packet['reports']:
        assert extract(report['stage']+'_content').encode()==report['content'].encode()
        for i,e in enumerate(report['evidence']):
            assert extract(report['stage']+'_evidence_'+str(i)).encode()==e['content'].encode()
            assert e['name'] in text and e['sha256'] in text
        for key in ('provenance','researched_at','origin_url','recorded_at','sha256'):
            assert json.dumps(report[key],ensure_ascii=False) in text
        for url in report['citations']:assert url in text
    assert packet==original
    assert text.count('Cited by:')==len({u for s in packet['reports'] for u in s['citations']})


def test_claim_index_roundtrip_keeps_invalid_rejections_history_and_source_unions():
    r=run()
    finish(r,0,[claim()]);finish(r,1,[claim(ident='research_chatgpt:C001')]);finish(r,2,[claim(ident='research_claude:C001')])
    finish(r,3,[claim(status='rejected',sources=[],counter_sources=['https://example.org/erratum'],counter_evidence='Exact opposing evidence')])
    finish(r,4,[claim(status='rejected',sources=[],counter_sources=[],counter_evidence='')])
    p=report_packet(r,r['stages'][5]);original=p['evidence_register']['claims']
    compact=compact_claims(original,p['reports'])
    urls=[s['url'] for s in p['evidence_register']['sources']]
    restored=source_references(source_references(compact,urls),urls,expand=True)
    assert expand_claims(restored,p['reports'])==original
    assert p['evidence_register']['upstream_warnings']
    text=markdown_packet(p)
    assert r['stages'][4]['report']['content'] in text  # invalid rejection is still in the original report
    assert all(w in text for w in p['evidence_register']['upstream_warnings'][0]['warnings'])


def test_unfinished_round_and_corrupted_reports_still_fail_closed():
    r=run()
    with pytest.raises(ValueError):prompt_for(r,r['stages'][3],packet_format='markdown-v1')
    for i in range(3):finish(r,i,[claim(ident=r['stages'][i]['id']+':C001')])
    r['stages'][0]['report']['content']+='corrupted'
    with pytest.raises(ValueError,match='bütünlüğü'):prompt_for(r,r['stages'][3],packet_format='markdown-v1')


@pytest.mark.parametrize('multiplier',[0.9,float('nan'),float('inf')])
def test_invalid_margin_rejected(multiplier):
    with pytest.raises(ValueError):Margin(multiplier=multiplier)


def test_budget_counts_transport_and_has_exact_boundary():
    b=TokenBudget(len,{'ChatGPT':{'multiplier':1.15,'overhead_tokens':9}})
    raw=account_input('system','İ\n"packet"',MARKDOWN_TRANSPORT)
    limit=math.ceil(len(raw)*1.15)+9
    result=b.measure('İ\n"packet"','ChatGPT',limit,'system',MARKDOWN_TRANSPORT)
    assert result['raw_tokens']==len('İ\n"packet"')
    assert result['transport_raw_tokens']==len(raw)
    assert result['fits'] and result['remaining_input_tokens']==0
    assert not b.measure('İ\n"packet"','ChatGPT',limit-1,'system',MARKDOWN_TRANSPORT)['fits']
    assert b.measure('same','Claude',1000,'system',MARKDOWN_TRANSPORT)['token_margin']['multiplier']==1.25


def test_budget_representation_matches_actual_account_bridge(tmp_path,monkeypatch):
    import importlib.util
    (tmp_path/'config.json').write_text(json.dumps({'models':{'chatgpt-account':{'provider':'codex'}}}))
    (tmp_path/'.bridge-key').write_text('isolated-test-key')
    monkeypatch.setenv('ACCOUNT_BRIDGE_ROOT',str(tmp_path))
    path=Path(__file__).resolve().parents[3]/'account-models/service/server.py'
    spec=importlib.util.spec_from_file_location('budget_contract_bridge',path)
    monkeypatch.syspath_prepend(str(path.parent))
    bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    prompt='İğüş\r\n```json\n{"exact":"\\n"}\n```'
    for fmt in ('json-v1',MARKDOWN_TRANSPORT):
        body={'model':'chatgpt-account','local_profile':'research_synthesis','local_prompt_format':fmt,
              'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}]}
        actual,_,_=bridge.prepare_prompt(body)
        assert actual.encode()==account_input(SYSTEM,prompt,fmt).encode()


@pytest.mark.asyncio
async def test_old_bridge_cannot_silently_reescape_the_counted_packet(tmp_path,monkeypatch):
    import httpx
    from engine import AccountProvider, ServiceError
    requests=[]
    def handler(request):
        requests.append(request.method)
        return httpx.Response(200,json={'status':'healthy'})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr('engine.httpx.AsyncClient',lambda **kwargs:client)
    key=tmp_path/'key';key.write_text('isolated-test-key')
    with pytest.raises(ServiceError,match='model isteği gönderilmedi'):
        await AccountProvider(key).synthesize({'provider':'ChatGPT','account_input_format':MARKDOWN_TRANSPORT},'Full packet')
    assert requests==['GET']


@pytest.mark.asyncio
async def test_early_forecast_is_not_a_submission_and_pending_packet_remains_blocked(engine):
    engine.budget=TokenBudget(lambda t:len(t)//4,{'ChatGPT':{'multiplier':1,'overhead_tokens':10}})
    engine.token_limit=10000
    r=await create(engine,False)
    for s in r['stages'][:4]:await add(engine,r['id'],s['id'])
    assert all(row['projection'] for row in (await engine.context_plan(r['id']))['stages'])
    await add(engine,r['id'],'review_claude')
    plan=await engine.context_plan(r['id'])
    assert len(plan['stages'])==3
    final=plan['stages'][-1]
    assert final['projection'] and final['missing_reports']==2 and final['reserved_report_tokens']==64000
    assert final['warning'] and not engine.provider.calls
    from engine import ServiceError
    with pytest.raises(ServiceError):await engine.packet(r['id'],'final_chatgpt')
    await settle(engine)
    assert not (await engine.get(r['id']))['paused']


@pytest.mark.asyncio
async def test_budget_guard_prevents_request_and_auto_retry_without_changing_evidence(engine):
    engine.budget=TokenBudget(len);engine.token_limit=20
    r=await create(engine)
    for s in r['stages'][:5]:await add(engine,r['id'],s['id'])
    await settle(engine)
    updated=await engine.get(r['id'])
    assert not engine.provider.calls
    for s in updated['stages'][5:7]:
        assert s['status']=='context_limit' and s['attempts']==0 and s['next_retry_at'] is None
        assert s['input_budget']['remaining_input_tokens']<0
        packet=await engine.packet(r['id'],s['id'])
        for previous in updated['stages'][:5]:assert previous['report']['content'] in packet['prompt']


@pytest.mark.asyncio
async def test_existing_completed_import_and_sent_input_keep_old_format(engine):
    r=await create(engine,False);r.pop('packet_format')
    for s in r['stages']:s.pop('account_input_format',None)
    for s in r['stages'][:5]:
        await engine.store.save(r)
        r=await add(engine,r['id'],s['id'])
    # Completed manual synthesis has no attempts or saved packet, but must retain its old export.
    r=await add(engine,r['id'],'synthesis_chatgpt')
    old=await engine.packet(r['id'],'synthesis_chatgpt')
    await engine.recover()
    assert (await engine.packet(r['id'],'synthesis_chatgpt'))['sha256']==old['sha256']
    pending=await engine.packet(r['id'],'synthesis_claude')
    assert 'BEGIN_REFERENCE_' in pending['prompt']


@pytest.mark.asyncio
async def test_saved_packet_does_not_normalize_crlf_before_verifying_hash(engine):
    from workflow import digest
    r=await create(engine,False);stage=r['stages'][5]
    text='Exact evidence\r\nSecond line\r\n'
    p=engine.input_path(r,stage);p.parent.mkdir(parents=True);p.write_bytes(text.encode())
    stage.update(attempts=1,input_sha256=digest(text))
    assert engine.input_prompt(r,stage).encode()==text.encode()
