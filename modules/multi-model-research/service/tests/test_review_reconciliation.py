import copy
import json
from types import SimpleNamespace

import pytest

from context_preparation import PreparationError, digest


def payload(count=8):
    nodes = []
    receipts = {}
    for index in range(count):
        rid = 'R' + str(index)
        receipts[rid] = {'verification': 'passage_not_matched', 'passage_context': 'Not safe when wet. ' * 40}
        nodes.append({'coverage': ['P' + str(index + 1)], 'blind_spots': ['Wet-weather trials missing.'],
            'dependencies': ['Compare dry and wet conditions.'], 'findings': [{
                'id': 'P' + str(index + 1) + ':F1', 'statement': 'Only safe when dry.',
                'status': 'unverified', 'model_status': 'supported', 'conditions': 'Dry only.',
                'counter_evidence': 'Wet weather is unsafe.', 'limits': 'One trial.',
                'original_quote': 'Only safe when dry.', 'prior_claim_ids': ['C1'],
                'prior_assessments': [{'id': 'C1', 'status': 'unverified', 'reason': 'Unmatched quotation.'}],
                'sources': [{'url': 'https://example.org/' + rid, 'quote': 'Only safe when dry.', 'receipt_id': rid}],
                'verification': {'unverified_sources': 1, 'unverified_receipts': [rid]}}]})
    return {'brief': {'question': 'Is it safe?', 'language': 'English'},
        'coverage': [p['coverage'][0] for p in nodes], 'source_sha256': digest('original'),
        'prior_claim_register': {'claims': [{'id': 'C1', 'statement': 'Safe only when dry.'}]},
        'working_findings': nodes, 'source_receipts': receipts}


def test_partition_keeps_every_field_source_condition_and_original_payload():
    from review_reconciliation import partition_payload, validate_batches
    data = payload(); original = copy.deepcopy(data)
    groups = partition_payload(data, lambda d: len(json.dumps(d)) < 4800)
    assert 1 < len(groups) < 8
    assert validate_batches(data, groups)
    assert data == original
    assert [f for g in groups for n in g['working_findings'] for f in n['findings']] == [
        f for n in data['working_findings'] for f in n['findings']]
    for g in groups:
        assert g['prior_claim_register'] == data['prior_claim_register']
        assert all(n['dependencies'] for n in g['working_findings'])


@pytest.mark.parametrize('damage', ['omit', 'duplicate', 'status', 'quote', 'receipt', 'register', 'condition', 'dependency'])
def test_partition_rejects_dropped_changed_or_duplicated_evidence(damage):
    from review_reconciliation import partition_payload, validate_batches
    data = payload(); groups = partition_payload(data, lambda d: len(json.dumps(d)) < 4800)
    f = groups[0]['working_findings'][0]['findings'][0]
    if damage == 'omit': groups.pop()
    if damage == 'duplicate': groups.append(copy.deepcopy(groups[0]))
    if damage == 'status': f['status'] = 'supported'
    if damage == 'quote': f['original_quote'] = 'Always safe.'
    if damage == 'receipt': next(iter(groups[0]['source_receipts'].values()))['verification'] = 'passage_matched_not_fact_checked'
    if damage == 'register': groups[0]['prior_claim_register']['claims'].clear()
    if damage == 'condition': f['conditions'] = 'Any weather.'
    if damage == 'dependency': groups[0]['working_findings'][0]['dependencies'] = []
    with pytest.raises(PreparationError): validate_batches(data, groups)


def test_indivisible_finding_is_never_clipped_and_batch_count_is_bounded():
    from review_reconciliation import partition_payload
    with pytest.raises(PreparationError, match='indivisible'):
        partition_payload(payload(), lambda d: False)
    with pytest.raises(PreparationError, match='batch limit'):
        partition_payload(payload(), lambda d: len(d['working_findings']) <= 1, max_batches=2)


def test_multiple_findings_in_one_part_keep_its_notes_and_receipts():
    from review_reconciliation import partition_payload, validate_batches
    data = payload(3)
    node = data['working_findings'][0]
    for index, other in enumerate(data['working_findings'][1:], 2):
        finding = other['findings'][0]; finding['id'] = 'P1:F' + str(index)
        node['findings'].append(finding)
    data['working_findings'] = [node]; data['coverage'] = ['P1']
    groups = partition_payload(data, lambda d: len(d['working_findings'][0]['findings']) <= 1)
    assert len(groups) == 3 and validate_batches(data, groups)
    assert all(g['working_findings'][0]['dependencies'] == node['dependencies'] for g in groups)


def test_unlinked_prior_records_remain_in_parent_and_catalog_not_silently_discarded():
    from review_reconciliation import partition_payload, tree_payload, validate_batches
    data = payload(2)
    other = {'id': 'C2', 'statement': 'Wet conditions invalidate the result.',
             'assessments': [{'status': 'disputed', 'reason': 'A contrary trial exists.'}]}
    data['prior_claim_register']['claims'].append(other)
    groups = partition_payload(data, lambda d: True)
    assert groups[0]['prior_claim_register']['claims'] == data['prior_claim_register']['claims'][:1]
    assert groups[0]['claim_catalog'][-1] == {k: other[k] for k in ['id', 'statement']}
    assert groups[0]['register_scope']['full_register_sha256'] == digest(json.dumps(
        data['prior_claim_register'], ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    parent = tree_payload(data, [{'coverage': data['coverage'], 'finding_ids': ['P1:F1', 'P2:F1'], 'report': 'Unverified.'}])
    assert parent['prior_claim_register']['claims'][-1] == other
    assert validate_batches(data, groups)
    groups[0]['claim_catalog'].pop()
    with pytest.raises(PreparationError): validate_batches(data, groups)


class Runner:
    def __init__(self, limit=7500):
        self.state = {'jobs': {}}; self.stage = {}; self.requests = []
        self.engine = SimpleNamespace(measure_input=lambda request, child: {'fits': len(request) <= limit})

    async def persist(self): pass

    async def call(self, key, request, profile):
        assert self.engine.measure_input(request, {})['fits']
        if key in self.state['jobs']:
            old = self.state['jobs'][key]
            assert old['input'] == request
            return old['response'], {}
        self.requests.append((key, request))
        data = json.loads(request.split('BEGIN_REFERENCE_', 1)[1].split('\n', 1)[1].split('\nEND_REFERENCE_', 1)[0])
        ids = data['finding_ids'] if 'finding_ids' in data else [
            f['id'] for n in data['working_findings'] for f in n['findings']]
        response = json.dumps({'coverage': data['coverage'], 'reviewed_findings': ids,
            'report': 'Dry conditions only. Wet-weather trials missing. Unverified evidence cannot support a decision.'})
        self.state['jobs'][key] = {'input': request, 'response': response}
        return response, {}


@pytest.mark.asyncio
async def test_hierarchy_is_measured_resumable_and_preserves_all_intermediate_reports():
    from review_reconciliation import reconcile
    runner = Runner(); data = payload(12); original = copy.deepcopy(data)
    report = await reconcile(runner, data, 'Assess the evidence.\n')
    assert data == original and 'Hierarchical reconciliation' in report
    assert 'semantic completeness' in report
    assert all(fid in report for fid in [n['findings'][0]['id'] for n in data['working_findings']])
    count = len(runner.requests)
    assert count > 2
    assert await reconcile(runner, data, 'Assess the evidence.\n') == report
    assert len(runner.requests) == count
    assert all('Dry conditions only.' in j['response'] for j in runner.state['jobs'].values())
    data['working_findings'][0]['findings'][0]['status'] = 'supported'
    with pytest.raises(PreparationError, match='changed'):
        await reconcile(runner, data, 'Assess the evidence.\n')


@pytest.mark.asyncio
async def test_global_combination_cannot_claim_to_have_seen_every_raw_finding():
    from review_reconciliation import reconcile
    runner = Runner(); await reconcile(runner, payload(12), 'Assess the evidence.\n')
    key, request = runner.requests[-1]
    assert key.startswith('reconcile-tree-')
    assert 'not all original findings' in request
    assert 'unverified must remain unverified' in request
    assert 'relationship_index' in request


@pytest.mark.asyncio
async def test_interruption_reuses_completed_batches_and_pins_inputs():
    from review_reconciliation import reconcile
    runner = Runner(); original_call = runner.call
    async def interrupt(key, request, profile):
        if key == 'reconcile-batch-3': raise RuntimeError('Observer interrupted')
        return await original_call(key, request, profile)
    runner.call = interrupt
    with pytest.raises(RuntimeError, match='interrupted'):
        await reconcile(runner, payload(12), 'Assess the evidence.\n')
    saved = copy.deepcopy(runner.state['jobs'])
    assert set(saved) == {'reconcile-batch-1', 'reconcile-batch-2'}
    runner.call = original_call
    await reconcile(runner, payload(12), 'Assess the evidence.\n')
    assert all(runner.state['jobs'][k] == v for k, v in saved.items())
    assert len({k for k, _ in runner.requests}) == len(runner.requests)
    with pytest.raises(PreparationError, match='changed'):
        await reconcile(runner, payload(12), 'Changed protocol.\n')


@pytest.mark.asyncio
async def test_nonconverging_reports_stop_without_removing_originals():
    from review_reconciliation import reconcile
    runner = Runner(); original_call = runner.call
    async def huge(key, request, profile):
        response, usage = await original_call(key, request, profile)
        obj = json.loads(response); obj['report'] = 'Never remove this evidence. ' * 600
        return json.dumps(obj), usage
    runner.call = huge
    with pytest.raises(PreparationError, match='indivisible|converge'):
        await reconcile(runner, payload(12), 'Assess the evidence.\n')


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['missing', 'url'])
async def test_batch_reports_cannot_omit_ids_or_invent_sources(fault):
    from review_reconciliation import reconcile
    runner = Runner(); original_call = runner.call
    async def broken(key, request, profile):
        response, usage = await original_call(key, request, profile); obj = json.loads(response)
        if fault == 'missing': obj['reviewed_findings'].pop()
        else: obj['report'] += ' https://invented.example/claim'
        return json.dumps(obj), usage
    runner.call = broken
    with pytest.raises(PreparationError): await reconcile(runner, payload(12), 'Assess the evidence.\n')
