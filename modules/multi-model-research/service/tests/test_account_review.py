import copy
import json

import pytest

from context_preparation import PreparationError, validate_plan


def test_new_review_transport_is_explicit_and_old_stages_keep_their_transport():
    from workflow import initial_stages
    old = initial_stages('browser', True)
    new = initial_stages('browser', True, account_review=True)
    assert [s['mode'] for s in old if s['round'] == 2] == ['browser', 'browser']
    assert [s['account_profile'] for s in new if s['round'] == 2] == ['research_review'] * 2
    assert all(s['mode'] == 'account' for s in new if s['round'] == 2)
    assert [s for s in old if s['round'] != 2] == [s for s in new if s['round'] != 2]


def test_parts_preserve_utf8_paragraphs_tables_and_mermaid_fences():
    from review_contract import partition
    text = ('# Koşullar\n\n' + 'Yalnız kuru ortamda geçerlidir; ıslakken geçersizdir.\n\n' * 10
            + '```mermaid\ngraph TD\nA --> B\n```\n\n'
            + '| Value | Unit |\n| --- | --- |\n| 3 | kg |\n\n' + 'Sonuç.\n\n' * 10)
    plan = partition(text, lambda value: len(value) < 650)
    assert validate_plan(plan, text)
    assert len(plan['parts']) > 1
    assert any('```mermaid\ngraph TD\nA --> B\n```' in p['text'] for p in plan['parts'])
    assert any('| Value | Unit |\n| --- | --- |\n| 3 | kg |' in p['text'] for p in plan['parts'])
    damaged = copy.deepcopy(plan)
    damaged['parts'][0]['text'] += '.'
    with pytest.raises(PreparationError): validate_plan(damaged, text)
    with pytest.raises(PreparationError, match='indivisible'):
        partition('```text\n' + 'x' * 1000 + '\n```', lambda s: len(s) < 600)


def framed_evidence(contents):
    from packet_markdown import markdown_packet
    return markdown_packet({'question': 'Araştırma?', 'scope': '', 'reports': [
        {'stage': 'research_' + str(i), 'content': content, 'evidence': [], 'citations': []}
        for i, content in enumerate(contents)
    ]})


@pytest.mark.parametrize('broken', [
    '```evidence-ledger\nevidence-ledger\n\n```evidence-ledger\n{"claims":[]}\n```\n```',
    '~~~text\nAn unfinished fence.\n',
    '````text\nA shorter fence does not close this.\n```',
])
def test_unclosed_report_fence_cannot_swallow_later_reports(broken):
    from review_contract import partition
    from context_preparation import render_segment
    intact = ('Yalnız kuru ortamda geçerlidir; ıslakken geçersizdir.\n\n' * 55
              + '```mermaid\ngraph TD\nA --> B\n```\n\n')
    text = framed_evidence([broken, intact])
    plan = partition(text, lambda value: len(value) < 1800)
    assert validate_plan(plan, text)
    assert ''.join(p['text'] for p in plan['parts']).encode() == text.encode()
    assert len(plan['parts']) > 1
    assert all(len(render_segment(p, plan)) < 1800 for p in plan['parts'])
    assert any(broken in p['text'] for p in plan['parts'])
    assert any('```mermaid\ngraph TD\nA --> B\n```' in p['text'] for p in plan['parts'])
    assert partition(text, lambda value: len(value) < 1800) == plan


def test_report_boundaries_are_byte_checked_not_guessed_from_fence_text():
    from review_contract import blocks
    broken = '```text\nKoşul: yağmurda değil.\n'
    text = framed_evidence([broken, 'Independent report.\n\n'])
    for damaged in (
        text.replace('UTF-8 bytes: ' + str(len(broken.encode())), 'UTF-8 bytes: 1', 1),
        text.replace('_research_0_content\n\n## Report:', '_wrong_content\n\n## Report:', 1),
    ):
        with pytest.raises(PreparationError, match='boundary'):
            blocks(damaged)
    # A marker inside ordinary source code is never an authorized packet boundary.
    code = '```text\nEND_REFERENCE_' + 'a' * 64 + '_research_0_content\n\nTail.\n```\n'
    assert blocks(code) == [code]


def test_oversized_real_code_block_is_still_rejected_without_truncation():
    from review_contract import partition
    text = framed_evidence(['```text\n' + 'x' * 3000 + '\n```', 'Next report.'])
    with pytest.raises(PreparationError, match='indivisible'):
        partition(text, lambda value: len(value) < 1800)


def sample():
    return {'coverage': ['P1'], 'findings': [{'statement': 'Conditional finding.',
        'status': 'supported', 'prior_claim_ids': ['C1'],
        'prior_assessments': [{'id':'C1','status':'supported','reason':'The quotation agrees with the original conditional claim.'}],
        'original_quote': 'Only when dry.', 'conditions': 'Dry conditions only.',
        'counter_evidence': 'Wet conditions invalidate it.', 'limits': 'Not universal.',
        'sources': [{'url': 'https://example.org/a', 'quote': 'Only when dry.'}]}],
        'blind_spots': ['No wet-weather trial.'], 'dependencies': []}


@pytest.mark.parametrize('damage', ['coverage', 'prior_id', 'quote', 'status', 'source', 'condition', 'shared_status'])
def test_map_rejects_fabricated_or_incomplete_records(damage):
    from review_contract import parse_map
    value = sample()
    assert parse_map(json.dumps(value), 'P1', 'Only when dry.', {'C1'})
    if damage == 'coverage': value['coverage'] = ['P1', 'P1']
    if damage == 'prior_id': value['findings'][0]['prior_claim_ids'] = ['invented']
    if damage == 'quote': value['findings'][0]['original_quote'] = 'Always works.'
    if damage == 'status': value['findings'][0]['status'] = 'certain'
    if damage == 'source': value['findings'][0]['sources'] = []
    if damage == 'condition': del value['findings'][0]['conditions']
    if damage == 'shared_status': value['findings'][0]['prior_assessments']=[]
    with pytest.raises(PreparationError): parse_map(json.dumps(value), 'P1', 'Only when dry.', {'C1'})


def test_final_requires_every_finding_and_disagreement():
    from review_contract import parse_merge
    value = {'coverage': ['P1', 'P2'], 'reviewed_findings': ['P1:F1', 'P2:F1'],
             'report': 'The evidence conflicts; conditions differ.'}
    assert parse_merge(json.dumps(value), ['P1', 'P2'], ['P1:F1', 'P2:F1'])
    value['reviewed_findings'].pop()
    with pytest.raises(PreparationError): parse_merge(json.dumps(value), ['P1', 'P2'], ['P1:F1', 'P2:F1'])


@pytest.mark.parametrize('url', ['http://127.0.0.1/x', 'http://[::1]/', 'http://169.254.169.254/',
    'http://10.0.0.1/', 'https://user:pass@example.org/', 'file:///etc/passwd', 'https://example.org:8317/'])
def test_source_reader_blocks_private_targets_and_credentials(url):
    from review_sources import validate_target
    with pytest.raises(PreparationError): validate_target(url)


def test_source_reader_rejects_mixed_dns_and_checks_exact_passage(monkeypatch):
    import review_sources
    monkeypatch.setattr(review_sources.socket, 'getaddrinfo', lambda *a, **k: [
        (2, 1, 6, '', ('93.184.216.34', 443)), (2, 1, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(PreparationError): review_sources.validate_target('https://example.org')
    assert review_sources.passage_matches('Only\nwhen dry.', 'Only when dry.')
    assert not review_sources.passage_matches('Not safe when wet.', 'Safe when wet.')


def test_source_cache_checks_hashes_and_refuses_unsupported_content(tmp_path, monkeypatch):
    import review_sources
    from context_preparation import digest
    calls=[]
    def request(url, deadline):
        calls.append(url)
        return 200, {'content-type':'text/html'}, b'<p>Only when dry.</p><script>Bad text.</script>'
    monkeypatch.setattr(review_sources, '_request', request)
    reader=review_sources.SourceReader(tmp_path)
    receipt=reader.verify(sample()['findings'][0]['sources'][0])
    assert receipt['verification']=='passage_matched_not_fact_checked'
    assert reader.verify(sample()['findings'][0]['sources'][0])==receipt and len(calls)==1
    (tmp_path/(digest('https://example.org/a')+'.body')).write_bytes(b'changed')
    with pytest.raises(PreparationError):reader.snapshot('https://example.org/a')
    monkeypatch.setattr(review_sources,'_request',lambda *a:(200,{'content-type':'image/png'},b'PNG'))
    with pytest.raises(PreparationError):reader.snapshot('https://example.org/image')


def test_redirects_are_revalidated_and_limited(tmp_path, monkeypatch):
    import review_sources
    seen=[]
    def request(url, deadline):
        seen.append(url)
        if url.startswith('http://127.'):
            review_sources.validate_target(url)
        return 302, {'location':'http://127.0.0.1/private'}, b''
    monkeypatch.setattr(review_sources,'_request',request)
    with pytest.raises(PreparationError): review_sources.SourceReader(tmp_path).snapshot('https://example.org')
    assert len(seen)==2


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', [None, 'repair', 'wrapped', 'wrapped_repair', 'unmatched', 'unavailable', 'no_search', 'source_mismatch', 'lost_connection', 'missing_finding', 'oversized_merge', 'redirect', 'invented_url'])
async def test_durable_research_checks_sources_reconciles_and_does_not_repeat(tmp_path, monkeypatch, fault):
    import asyncio
    import review_execution
    from engine import ServiceError
    from context_preparation import digest, envelope
    from review_contract import partition
    from review_execution import summary, encoded
    from segmented_execution import confirm_cancel
    text='Only when dry.\n\n'*15
    body=envelope(text)
    plan=partition(body,lambda value:len(value)<600)
    plan.update(brief={'question':'Is this safe in wet conditions?', 'scope':'Compare exceptions', 'language':'English','as_of':'2026-09-22'},
        claim_catalog=[{'id':'C1','statement':'Only when dry.'}],
        protected_register={'claims':[{'id':'C1','statement':'Only when dry.'}]})
    assert len(plan['parts'])>1
    prompt='Task\n'+envelope(text)
    stage={'id':'review_chatgpt','provider':'ChatGPT','round':2,'account_profile':'research_review','preparation':summary(plan)}
    run={'id':'fixture','stages':[stage],'paused':False}
    state={'version':'account-review-v1','input_sha256':digest(prompt),'plan':plan,'jobs':{}}
    journal=tmp_path/'segmented-journal.json';journal.write_text(encoded(state))
    class Provider:
        calls=[]
        async def synthesize(self, child, request):
            self.calls.append((child,request))
            assert 'Is this safe in wet conditions?' in request
            if fault=='lost_connection':raise OSError('no receipt')
            data=json.loads(request.split('BEGIN_REFERENCE_',1)[1].split('\n',1)[1].split('\nEND_REFERENCE_',1)[0])
            if child['account_profile']=='research_review':
                result=sample();result['coverage']=[data['part_id']]
                part=next(p for p in plan['parts'] if p['id']==data['part_id'])
                result['findings'][0]['original_quote']=part['text'].strip().split('\n')[0]
                if fault in ('repair','wrapped_repair'):del result['findings'][0]['prior_assessments']
            elif 'recorded_response' in data:
                from review_contract import read_working_object
                result=read_working_object(data['recorded_response'])[0]
                result['findings'][0]['prior_assessments']=sample()['findings'][0]['prior_assessments']
            else:
                ids=[f['id'] for node in data['working_findings'] for f in node['findings']]
                if fault=='missing_finding':ids.pop()
                expected_verification = {'unmatched': 'passage_not_matched', 'unavailable': 'source_unavailable'}.get(fault, 'passage_matched_not_fact_checked')
                assert all(data['source_receipts'][source['receipt_id']]['verification']==expected_verification
                    for node in data['working_findings'] for f in node['findings'] for source in f['sources'])
                if fault in ('unmatched', 'unavailable'):
                    assert all(f['status'] == 'unverified' and f['model_status'] == 'supported'
                        for node in data['working_findings'] for f in node['findings'])
                    assert 'must remain unverified' in request
                result={'coverage':data['coverage'],'reviewed_findings':ids,'report':'Not safe when wet; the dry-condition result does not generalize.'}
                if fault == 'redirect':result['report'] += ' https://example.org/current\n- Source redirect.'
                if fault == 'invented_url':result['report'] += ' https://invented.example/claim\n- Unknown source.'
            response=json.dumps(result)
            if child['account_profile']=='research_review' and fault in ('wrapped','wrapped_repair'):
                response='Provider note: the wet-weather trial is missing.\n```json\n'+response+'\n```'
            return response,{'execution':{'searched':fault!='no_search','read_sources':True,'unexpected_tools':[]}}
    class Store:
        async def save(self,value):pass
    class Engine:
        lock=asyncio.Lock();store=Store();provider=Provider()
        async def get(self,rid):return run
        def stage(self,r,sid):return stage
        def input_path(self,r,s):return tmp_path/'input-packet.md'
        def measure_input(self,request,child):return {'fits':not(fault=='oversized_merge' and child.get('account_profile')=='review_merge')}
    import review_sources
    original_verify = review_sources.SourceReader.verify
    def request_source(*args):
        if fault == 'unavailable': raise review_sources.SourceUnavailable('Source returned HTTP 403.')
        if fault == 'redirect' and args[0] != 'https://example.org/current':
            return 302, {'location': 'https://example.org/current'}, b''
        return 200, {'content-type': 'text/plain'}, b'Not safe when wet.' if fault == 'unmatched' else b'Only when dry.'
    monkeypatch.setattr(review_sources, '_request', request_source)
    def verify(self,source):
        if fault=='source_mismatch':raise PreparationError('passage mismatch')
        return original_verify(self, source)
    monkeypatch.setattr(review_execution.SourceReader,'verify',verify)
    engine=Engine()
    if fault and fault not in ('repair', 'wrapped', 'wrapped_repair', 'unmatched', 'unavailable', 'redirect'):
        with pytest.raises(ServiceError) as error:await review_execution.execute(engine,run,stage,prompt)
        expected='submission_uncertain' if fault=='lost_connection' else 'context_limit' if fault=='oversized_merge' else 'integrity_error'
        assert error.value.kind==expected
        count=len(engine.provider.calls)
        with pytest.raises(ServiceError):await review_execution.execute(engine,run,stage,prompt)
        assert len(engine.provider.calls)==count
        if fault=='lost_connection':
            await confirm_cancel(engine,run,stage)
            assert json.loads(journal.read_text())['jobs']['review-P1']['status']=='cancelled'
        return
    report,usage=await review_execution.execute(engine,run,stage,prompt)
    assert 'Wet conditions invalidate it.' in report and 'Not universal.' in report
    assert '```evidence-ledger' in report and 'source-passage matching' in report
    assert usage['coverage']==[p['id'] for p in plan['parts']]
    expected_calls=len(plan['parts'])*(2 if fault in ('repair','wrapped_repair') else 1)+1
    assert len(engine.provider.calls)==expected_calls
    final_request=engine.provider.calls[-1][1]
    if fault in ('wrapped','wrapped_repair'):
        assert 'Provider note: the wet-weather trial is missing.' in final_request
        assert 'Provider note: the wet-weather trial is missing.' in report
        assert 'Preserved provider notes' in report
    assert final_request.count('"verification":"passage_matched_not_fact_checked"')==(0 if fault in ('unmatched', 'unavailable') else 1)
    if fault in ('unmatched', 'unavailable'):
        assert usage['source_passages_matched'] == 0 and usage['source_passages_unverified'] == 1
        assert 'Affected findings remain unverified' in report
    await review_execution.execute(engine,run,stage,prompt)
    assert len(engine.provider.calls)==expected_calls
    saved=json.loads(journal.read_text());saved['jobs']['review-P1']['response']+='corrupted'
    journal.write_text(encoded(saved))
    with pytest.raises(ServiceError):await review_execution.execute(engine,run,stage,prompt)
    assert len(engine.provider.calls)==expected_calls


@pytest.mark.asyncio
async def test_cancel_waits_for_snapshot_writer_before_releasing_stage(tmp_path):
    import asyncio
    import threading
    from types import SimpleNamespace
    from review_execution import ReviewRunner
    started=threading.Event();finish=threading.Event()
    def verify(source):started.set();finish.wait(timeout=2);return {}
    runner=ReviewRunner(SimpleNamespace(input_path=lambda *a:tmp_path/'input-packet.md'),{}, {},'')
    runner.reader=SimpleNamespace(assess=verify)
    task=asyncio.create_task(runner.verify_source({}))
    await asyncio.to_thread(started.wait,1)
    task.cancel();await asyncio.sleep(.01)
    assert not task.done()
    finish.set()
    with pytest.raises(asyncio.CancelledError):await task


def test_research_planning_cannot_clear_an_integrity_block():
    from engine import Engine
    policy={'blocked':True,'block_status':'integrity_error','findings':[{'id':'ECA-018'}]}
    assert Engine.preparation_plan(object(),{}, {'account_profile':'research_review'}, '', policy) is None
    assert policy['blocked'] and policy['block_status']=='integrity_error'


def test_repair_can_fill_assessments_but_cannot_change_or_remove_evidence():
    from review_contract import validate_repair
    before=sample();del before['findings'][0]['prior_assessments']
    after=sample()
    assert validate_repair(json.dumps(before),json.dumps(after))
    after['findings'][0]['conditions']='Always, including wet conditions.'
    with pytest.raises(PreparationError):validate_repair(json.dumps(before),json.dumps(after))
    after=sample();after['findings']=[]
    with pytest.raises(PreparationError):validate_repair(json.dumps(before),json.dumps(after))


def test_conflicting_prior_claims_keep_separate_statuses_and_new_sources_are_audited():
    from review_execution import ledger,encoded
    from evidence_protocol import audit_report
    from workflow import citations
    node=sample();finding=node['findings'][0];finding['id']='P1:F1'
    finding['prior_claim_ids'].append('C2')
    finding['prior_assessments'].append({'id':'C2','status':'rejected','reason':'The wet-condition claim is contradicted by the source.'})
    plan={'protected_register':{'claims':[{'id':'C1','statement':'Only when dry.'},{'id':'C2','statement':'Works when wet.'}]}}
    result=ledger(plan,[node],'review_chatgpt')
    assert [c['status'] for c in result['claims'][:2]]==['supported','rejected']
    content='```evidence-ledger\n'+encoded(result)+'\n```'
    previous={'id':'research_chatgpt','round':1,'evidence_audit':{'assessments':[
        {'id':c['id'],'statement':c['statement'],'sources':[],'status':'unverified'} for c in plan['protected_register']['claims']]}}
    stage={'id':'review_chatgpt','round':2,'mode':'account','account_profile':'research_review','report':{'content':content,'citations':citations(content)}}
    audited=audit_report({'stages':[previous,stage]},stage)
    assert len(audited['assessments'])==3 and not audited['missing_claim_ids']
    stage['account_profile']='review_merge'
    assert not audit_report({'stages':[previous,stage]},stage)['assessments']


@pytest.mark.asyncio
async def test_real_engine_round_barrier_dispatch_audit_and_report_preservation(tmp_path,monkeypatch):
    import asyncio
    from pathlib import Path
    from engine import Engine
    from store import Store
    from token_budget import TokenBudget
    from test_workflow import Sink,add
    from review_sources import SourceReader
    calls=[]
    class Provider:
        async def synthesize(self,stage,request):
            calls.append((stage['id'],stage['account_profile']))
            data=json.loads(request.split('BEGIN_REFERENCE_',1)[1].split('\n',1)[1].split('\nEND_REFERENCE_',1)[0])
            if stage['account_profile']=='research_review':
                result=sample();result['coverage']=[data['part_id']]
                finding=result['findings'][0];finding.update(prior_claim_ids=[],prior_assessments=[],
                    original_quote='Unique report research_gemini with full evidence https://example.org/research_gemini')
            else:result={'coverage':data['coverage'],'reviewed_findings':[f['id'] for n in data['working_findings'] for f in n['findings']],
                'report':'Conditional evidence only. The result does not generalize to wet conditions.'}
            return json.dumps(result),{'execution':{'searched':True,'read_sources':True,'unexpected_tools':[]}}
    monkeypatch.setattr(SourceReader,'verify',lambda self,source:{'url':source['url'],
        'final_url':source['url'],'verification':'passage_matched_not_fact_checked','body_sha256':'fixture'})
    store=Store(tmp_path);await store.open()
    counter=lambda s:len(s)//4
    engine=Engine(store,Provider(),Sink(),counter,120000,budget=TokenBudget(counter))
    try:
        run=await engine.create({'question':'Does this apply in wet conditions?', 'scope':'Preserve all exceptions', 'as_of':'2026-09-22',
            'language':'English','auto_synthesize':False,'account_review':True},'review-integration')
        for sid in ('research_gemini','research_chatgpt'):
            await add(engine,run['id'],sid)
        assert calls==[]
        await add(engine,run['id'],'research_claude')
        for _ in range(400):
            if not engine.tasks and not engine.background:break
            await asyncio.sleep(.01)
        result=await engine.get(run['id'])
        reviews=[s for s in result['stages'] if s['round']==2]
        assert len(calls)==4
        assert all(s['status']=='completed' and s['report']['provenance']=='account_research_review' for s in reviews)
        assert all(len(s['evidence_audit']['assessments'])==1 for s in reviews)
        assert reviews[0]['preparation']['plan_sha256']==reviews[1]['preparation']['plan_sha256']
        assert all(s['report']['content'].startswith('Unique report '+s['id']) for s in result['stages'] if s['round']==1)
        assert all(s['report'] is None for s in result['stages'] if s['round']>=3)
    finally:
        await engine.close();await store.close()


def test_quote_context_exposes_omitted_negation(tmp_path,monkeypatch):
    from review_sources import SourceReader
    from context_preparation import digest
    reader=SourceReader(tmp_path)
    text='Not safe when wet. The dry-weather result has strict limits.'
    monkeypatch.setattr(reader,'snapshot',lambda url:{'url':url,'text':text,'text_sha256':digest(text),'body_sha256':'hash'})
    receipt=reader.verify({'url':'https://example.org','quote':'safe when wet.'})
    assert receipt['passage_context'].startswith('Not safe')
    assert receipt['verification']=='passage_matched_not_fact_checked'
