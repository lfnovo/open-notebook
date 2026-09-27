import copy
import json

import pytest

from context_preparation import PreparationError, digest
from test_review_reconciliation import payload, Runner


def response():
    return {'coverage': ['P1', 'P2'], 'reviewed_findings': [
        {'id': 'P1:F1', 'status': 'unverified', 'justification': 'Only when dry; wet trials missing.',
         'receipt_checks': {'passage_not_matched': ['R0']}},
        {'id': 'P2:F1', 'status': 'unverified', 'justification': 'Conflicting conditions remain unresolved.',
         'receipt_checks': {'passage_not_matched': ['R1']}}],
        'report': 'Unverified findings cannot justify a universal conclusion.'}


def test_rich_review_records_preserve_all_annotations_and_check_identity_exactly():
    from review_reconciliation import parse_reconciliation
    data = payload(2); value = response(); original = copy.deepcopy(value)
    raw = json.dumps(value)
    report = parse_reconciliation(raw, data['coverage'], ['P1:F1', 'P2:F1'], data)
    assert value == original
    assert value['report'] in report and 'Only when dry; wet trials missing.' in report
    block = json.loads(report.split('```json\n', 1)[1].rsplit('\n```', 1)[0])
    assert block['records'] == value['reviewed_findings']
    assert block['response_sha256'] == digest(raw)
    assert block['accepted_as_source_verification'] is False
    assert block['unresolved_receipt_references'] == []


@pytest.mark.parametrize('fault', ['missing', 'extra', 'duplicate', 'mixed', 'id_type', 'empty_report', 'part'])
def test_rich_record_support_never_invents_missing_coverage(fault):
    from review_reconciliation import parse_reconciliation
    value = response()
    if fault == 'missing': value['reviewed_findings'].pop()
    if fault == 'extra': value['reviewed_findings'].append({'id':'P3:F1'})
    if fault == 'duplicate': value['reviewed_findings'].append(copy.deepcopy(value['reviewed_findings'][0]))
    if fault == 'mixed': value['reviewed_findings'][0] = 'P1:F1'
    if fault == 'id_type': value['reviewed_findings'][0]['id'] = 1
    if fault == 'empty_report': value['report'] = ''
    if fault == 'part': value['coverage'] = ['P1']
    with pytest.raises(PreparationError):
        parse_reconciliation(json.dumps(value), ['P1','P2'], ['P1:F1','P2:F1'], payload(2))


@pytest.mark.parametrize('receipt', ['made-up-receipt', 'R1'])
def test_wrong_receipt_annotations_are_retained_but_never_accepted_as_verification(receipt):
    from review_reconciliation import parse_reconciliation
    value = response(); value['reviewed_findings'][0]['receipt_checks'] = {'passage_matched_not_fact_checked':[receipt]}
    data = payload(2); original = copy.deepcopy(data)
    report = parse_reconciliation(json.dumps(value), ['P1','P2'], ['P1:F1','P2:F1'], data)
    assert data == original
    block = json.loads(report.split('```json\n',1)[1].rsplit('\n```',1)[0])
    assert block['records'] == value['reviewed_findings']
    assert block['unresolved_receipt_references'][0]['receipt_id'] == receipt
    assert 'not accepted source receipts' in report


def test_annotations_cannot_promote_the_input_verification_status():
    from review_reconciliation import parse_reconciliation
    value = response(); value['reviewed_findings'][0]['status'] = 'supported'
    data = payload(2)
    report = parse_reconciliation(json.dumps(value), ['P1','P2'], ['P1:F1','P2:F1'], data)
    block = json.loads(report.split('```json\n',1)[1].rsplit('\n```',1)[0])
    assert block['input_statuses'] == {'P1:F1':'unverified','P2:F1':'unverified'}
    assert block['records'][0]['status'] == 'supported'
    assert 'cannot promote an unverified finding' in report
    assert data['working_findings'][0]['findings'][0]['status'] == 'unverified'


def test_ordinary_id_lists_keep_the_existing_exact_report():
    from review_reconciliation import parse_reconciliation
    value = response(); value['reviewed_findings'] = ['P1:F1','P2:F1']
    assert parse_reconciliation(json.dumps(value), ['P1','P2'], value['reviewed_findings'], payload(2)) == value['report']


@pytest.mark.asyncio
async def test_resumption_reuses_rich_response_without_new_provider_calls():
    from review_reconciliation import reconcile
    runner = Runner(); original_call = runner.call
    async def rich(key, request, profile):
        response, usage = await original_call(key, request, profile)
        value = json.loads(response)
        value['reviewed_findings'] = [{'id':fid, 'justification':'Conditions still apply.'} for fid in value['reviewed_findings']]
        return json.dumps(value), usage
    runner.call = rich
    report = await reconcile(runner, payload(4), 'Assess the evidence.\n')
    assert 'Conditions still apply.' in report
    calls = len(runner.requests)
    assert await reconcile(runner, payload(4), 'Assess the evidence.\n') == report
    assert len(runner.requests) == calls


def test_rich_annotations_do_not_weaken_the_default_merge_parser():
    from review_contract import parse_merge
    with pytest.raises(PreparationError): parse_merge(json.dumps(response()), ['P1','P2'], ['P1:F1','P2:F1'])


def test_explicit_finding_id_field_keeps_raw_records_and_exact_identity_gate():
    from review_reconciliation import parse_reconciliation
    value=response()
    for record in value['reviewed_findings']:
        record['finding_id']=record.pop('id')
        record['reviewed_by']='child report, not source verification'
    raw=json.dumps(value); original=copy.deepcopy(value)
    report=parse_reconciliation(raw,['P1','P2'],['P1:F1','P2:F1'],payload(2))
    block=json.loads(report.split('```json\n',1)[1].rsplit('\n```',1)[0])
    assert value==original and block['records']==original['reviewed_findings']
    assert block['identity_aliases']==[{'index':0,'field':'finding_id','id':'P1:F1'},
                                       {'index':1,'field':'finding_id','id':'P2:F1'}]
    assert block['response_sha256']==digest(raw)
    assert block['input_statuses']=={'P1:F1':'unverified','P2:F1':'unverified'}
    assert not block['accepted_as_source_verification']


@pytest.mark.parametrize('fault',['conflict','null_id','number','missing','duplicate','unknown','guessed_key'])
def test_finding_id_alias_does_not_guess_or_override_conflicting_identity(fault):
    from review_reconciliation import parse_reconciliation
    value=response()
    for record in value['reviewed_findings']:record['finding_id']=record.pop('id')
    first=value['reviewed_findings'][0]
    if fault=='conflict':first['id']='P2:F1'
    elif fault=='null_id':first['id']=None
    elif fault=='number':first['finding_id']=1
    elif fault=='missing':first.pop('finding_id')
    elif fault=='duplicate':first['finding_id']='P2:F1'
    elif fault=='unknown':first['finding_id']='P99:F1'
    else:first['identity']=first.pop('finding_id')
    with pytest.raises(PreparationError):
        parse_reconciliation(json.dumps(value),['P1','P2'],['P1:F1','P2:F1'],payload(2))


def test_finding_id_alias_never_turns_a_model_receipt_claim_into_verification():
    from review_reconciliation import parse_reconciliation
    value=response();record=value['reviewed_findings'][0]
    record['finding_id']=record.pop('id')
    record['receipt_checks']={'passage_matched_not_fact_checked':['made-up']}
    report=parse_reconciliation(json.dumps(value),['P1','P2'],['P1:F1','P2:F1'],payload(2))
    block=json.loads(report.split('```json\n',1)[1].rsplit('\n```',1)[0])
    assert block['unresolved_receipt_references'][0]['finding_id']=='P1:F1'
    assert block['unresolved_receipt_references'][0]['recorded'] is None
