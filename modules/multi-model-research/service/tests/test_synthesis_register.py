import copy
import json
import re
from types import SimpleNamespace

import pytest

from context_preparation import PreparationError, digest, envelope, plan_segments
import synthesis_register as registry


def register(count=8):
    return {'claims': [{'id': f'C{i}', 'statement': f'Not safe in condition {i}.',
            'original_stage': 'review', 'sources': ['https://example.org/paper'],
            'assessments': [{'stage': 'review', 'status': 'unverified',
                'conditions': 'Only for adults; never children. ' * 80,
                'value': 2.5, 'unit': 'percent', 'counter_evidence': ['Unresolved.']}]}
            for i in range(count)], 'sources': [], 'limits': 'Not verified.'}


def batches(value):
    return registry.plan_batches(value, {'question': 'Test'},
                                 lambda b: len(registry.render_batch(b)) < 11000)


def test_complete_records_reconstruct_in_order_with_all_qualifications():
    original = register(); before = copy.deepcopy(original); parts = batches(original)
    assert len(parts) > 1 and original == before
    assert [c for b in parts for c in b['records']] == original['claims']
    assert all(len(registry.render_batch(b)) < 11000 for b in parts)
    registry.validate_batches(original, {'question': 'Test'}, parts)
    parent = registry.catalog(original)
    assert parent['full_register_sha256'] == digest(registry.encoded(original))
    assert all(c['input_statuses'][0]['status'] == 'unverified' for c in parent['claims'])
    assert [c['statement'] for c in parent['claims']] == [c['statement'] for c in original['claims']]
    assert [[parent['source_urls'][s] for s in c['source_ids']] for c in parent['claims']] == [c['sources'] for c in original['claims']]


@pytest.mark.parametrize('mutation', ['omit', 'repeat', 'reorder', 'condition', 'id', 'brief', 'hash'])
def test_mutated_batches_fail_closed(mutation):
    original = register(); parts = batches(original)
    if mutation == 'omit': parts.pop()
    elif mutation == 'repeat': parts.append(copy.deepcopy(parts[0]))
    elif mutation == 'reorder': parts.reverse()
    elif mutation == 'condition': parts[0]['records'][0]['assessments'][0]['conditions'] = 'Safe.'
    elif mutation == 'id': parts[0]['claim_ids'][0] = 'Invented'
    elif mutation == 'brief': parts[0]['payload']['brief']['question'] = 'Changed'
    else: parts[0]['payload']['full_register_sha256'] = '0' * 64
    with pytest.raises(PreparationError): registry.validate_batches(original, {'question': 'Test'}, parts)


@pytest.mark.parametrize('found', [[], ['C1', 'C1'], ['C1', 'Other'], 'C1'])
def test_claim_response_cannot_omit_repeat_or_invent_ids(found):
    with pytest.raises(PreparationError): registry.validate_response(json.dumps({'reviewed_claim_ids': found}), ['C1','C2'])


def test_indivisible_record_and_batch_limit_still_block():
    with pytest.raises(PreparationError, match='indivisible'):
        registry.plan_batches(register(), {}, lambda b: False)
    with pytest.raises(PreparationError, match='batch count'):
        registry.plan_batches(register(), {}, lambda b: len(b['records']) == 1, max_batches=2)


def test_lineage_catalog_is_explicit_and_keeps_all_records_bound():
    value=register(); parent=registry.catalog(value,include_statements=False)
    assert parent['scope']=='claim-lineage-only'
    assert 'not present in this parent catalog' in parent['notice']
    assert all('statement' not in c for c in parent['claims'])
    assert parent['full_register_sha256']==digest(registry.encoded(value))
    plan={'protected_register':value,'register_mode':registry.VERSION,'register_catalog_mode':'lineage-only',
          'register_catalog':parent,'register_brief':{'question':'Test'},'register_parts':batches(value)}
    registry.validate_plan(plan)
    assert [c['statement'] for b in plan['register_parts'] for c in b['records']]==[c['statement'] for c in value['claims']]
    plan['register_catalog']['claims'][0]['input_statuses'][0]['status']='supported'
    with pytest.raises(PreparationError,match='catalog changed'):registry.validate_plan(plan)


def test_peer_plans_share_the_strictest_budget_and_keep_full_statements_in_batches(monkeypatch):
    import segmented_execution as segment
    import workflow
    value=register(12)
    for c in value['claims']:c['statement']+=' Long but meaningful statement.'*65
    peers=[{'id':'a','round':3,'mode':'account'},{'id':'b','round':3,'mode':'account'}]
    run={'stages':peers,'question':'Shared question','scope':'All evidence','language':'tr','as_of':'2026-09-26'}
    prompt='Task\n'+envelope('Evidence')
    monkeypatch.setattr(workflow,'prompt_for',lambda *a:prompt)
    monkeypatch.setattr(workflow,'report_packet',lambda *a:{'evidence_register':value,'reports':[]})
    def measure(text,peer):
        limit=30000 if peer['id']=='a' else 15000
        return {'fits':len(text)<=limit,'utilization':len(text)/limit}
    e=SimpleNamespace(measure_input=measure)
    plans=[segment.plan_for(e,run,peer,prompt) for peer in peers]
    assert plans[0]==plans[1] and plans[0]['register_catalog_mode']=='lineage-only'
    assert [c for b in plans[0]['register_parts'] for c in b['records']]==value['claims']


def test_no_catalog_mode_or_unknown_mode_can_silently_change_records():
    plan={'register_mode':'invented'}
    with pytest.raises(PreparationError,match='Unknown'):registry.validate_plan(plan)


def test_planner_selects_bounded_records_only_when_full_register_does_not_fit(monkeypatch):
    import segmented_execution as segment
    import workflow
    value = register(20); stage = {'id':'s','round':3,'mode':'account'}
    run = {'stages':[stage], 'question':'Test','scope':'','language':'tr','as_of':'2026-09-26'}
    prompt = 'Task\n' + envelope('Evidence')
    monkeypatch.setattr(workflow, 'prompt_for', lambda *a: prompt)
    monkeypatch.setattr(workflow, 'report_packet', lambda *a: {'evidence_register':value,'reports':[]})
    engine = SimpleNamespace(measure_input=lambda text, peer: {'fits':len(text)<=16000,'utilization':len(text)/16000})
    plan = segment.plan_for(engine, run, stage, prompt)
    assert plan['register_mode'] == registry.VERSION
    assert plan['protected_register'] == value
    registry.validate_plan(plan)
    assert segment.summary(plan)['minimum_calls'] == len(plan['parts']) + len(plan['register_parts']) + 1
    monkeypatch.setattr(workflow, 'report_packet', lambda *a: {'evidence_register':register(1),'reports':[]})
    small = segment.plan_for(engine, run, stage, prompt)
    assert 'register_mode' not in small


@pytest.mark.asyncio
async def test_execution_includes_all_register_batches_and_reuses_receipts(tmp_path):
    import asyncio
    import segmented_execution as segment
    prompt = 'Task\n' + envelope('Original evidence')
    from packet_markdown import evidence_body
    body, _ = evidence_body(prompt)
    plan = plan_segments(body, lambda s: len(s)<3000)
    plan.update(protected_register=register(), source_inventory=['https://example.org/paper'],
                register_mode=registry.VERSION, register_brief={'question':'Test'})
    plan['register_catalog'] = registry.catalog(plan['protected_register'])
    plan['register_parts'] = batches(plan['protected_register'])
    stage = {'id':'s','round':4,'provider':'ChatGPT'}; run = {'id':'r','stages':[stage]}
    path = tmp_path/'segmented-journal.json'
    path.write_text(json.dumps({'input_sha256':digest(prompt),'plan':plan,'jobs':{}}))
    requests = []
    class Provider:
        async def synthesize(self, child, text):
            requests.append(text)
            parts = json.loads(re.search(r'part IDs exactly once: (\[.*?\])\.', text)[1])
            claim_match = re.search(r'claim IDs exactly once: (\[.*?\])\.', text)
            claim_ids = json.loads(claim_match[1]) if claim_match else []
            return json.dumps({'coverage':parts,'reviewed_claim_ids':claim_ids,'report':'All qualifications remain unresolved.'}), {}
    class Store:
        async def save(self, value): pass
    class Engine:
        lock=asyncio.Lock(); store=Store(); provider=Provider()
        async def get(self, rid): return run
        def stage(self, run, sid): return stage
        def input_path(self, run, stage): return tmp_path/'input-packet.md'
        def measure_input(self, text, stage): return {'fits':len(text)<30000,'utilization':len(text)/30000}
    e=Engine()
    report, usage = await segment.execute(e, run, stage, prompt)
    assert len(requests) == len(plan['parts']) + len(plan['register_parts']) + 1
    assert 'separate recorded batches' in report
    assert 'scope' in requests[-1] and registry.VERSION in requests[-1]
    assert usage['register_claim_ids'] == [c['id'] for c in plan['protected_register']['claims']]
    previous = len(requests)
    assert (await segment.execute(e, run, stage, prompt))[0] == report
    assert len(requests) == previous
    # A completed, hash-correct provider response with missing claim coverage still fails on replay.
    saved = json.loads(path.read_text()); job = saved['jobs']['register-R1']
    response = json.loads(job['response']); response['reviewed_claim_ids'] = []
    job['response'] = json.dumps(response); job['response_sha256'] = digest(job['response'])
    path.write_text(json.dumps(saved))
    from engine import ServiceError
    with pytest.raises(ServiceError, match='claim identity'):
        await segment.execute(e, run, stage, prompt)
    assert len(requests) == previous
