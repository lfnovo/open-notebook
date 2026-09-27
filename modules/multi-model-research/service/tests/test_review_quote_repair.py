import copy
import json
from unittest.mock import AsyncMock

import pytest

from context_preparation import PreparationError, digest
from review_contract import parse_map
from test_account_review import sample


def fixture():
    value = sample()
    row = copy.deepcopy(value['findings'][0])
    row['original_quote'] = 'The saved view and event logs require separate access checks before reuse.'
    value['findings'].append(row)
    source = 'Özgün: Only when dry.\n\nThe saved view policy and event logs require separate access checks before reuse.'
    response = json.dumps(value)
    proposal = {'response_sha256': digest(response), 'part_sha256': digest(source), 'anchors': [
        {'finding_index': 2, 'source_quote': source.split('\n\n')[1]}]}
    return value, source, response, proposal


def test_explicit_repair_preserves_all_findings_and_marks_omission_unverified():
    value, source, response, proposal = fixture()
    with pytest.raises(PreparationError): parse_map(response, 'P1', source, {'C1'})
    result = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))
    row = result['findings'][1]; original = value['findings'][1]
    for key in ('statement', 'original_quote', 'conditions', 'counter_evidence', 'limits', 'sources', 'prior_claim_ids'):
        assert row[key] == original[key]
    assert len(result['findings']) == len(value['findings'])
    assert row['status'] == row['prior_assessments'][0]['status'] == 'unverified'
    assert row['model_status'] == row['prior_assessments'][0]['model_status'] == 'supported'
    anchor = row['original_anchor']
    assert anchor['scope'] == 'repaired_part_quote' and not anchor['counted_as_part_evidence']
    assert source.encode()[anchor['start_byte']:anchor['end_byte']].decode() == anchor['text']
    assert anchor['inserted_tokens'] == ['policy']
    assert anchor['model_quote_sha256'] == digest(original['original_quote'])


@pytest.mark.parametrize('fault', ['response_hash', 'part_hash', 'missing', 'duplicate', 'other_finding',
    'invented_quote', 'substitution', 'ambiguous', 'added_url', 'unbounded', 'unknown_field'])
def test_repair_rejects_tampering_or_unbounded_reassociation(fault):
    value, source, response, proposal = fixture()
    if fault == 'response_hash': proposal['response_sha256'] = 'wrong'
    if fault == 'part_hash': proposal['part_sha256'] = 'wrong'
    if fault == 'missing': proposal['anchors'] = []
    if fault == 'duplicate': proposal['anchors'] *= 2
    if fault == 'other_finding': proposal['anchors'][0]['finding_index'] = 1
    if fault == 'invented_quote': proposal['anchors'][0]['source_quote'] += ' False.'
    if fault == 'unknown_field': proposal['anchors'][0]['status'] = 'supported'
    if fault in ('substitution', 'ambiguous', 'added_url', 'unbounded'):
        quote = proposal['anchors'][0]['source_quote']
        if fault == 'substitution': quote = quote.replace('require', 'avoid')
        if fault == 'ambiguous': source += '\n\n' + quote
        if fault == 'added_url': quote += ' https://evil.example/'
        if fault == 'unbounded': quote = quote.replace('policy', ' '.join(['extra'] * 40))
        if fault != 'ambiguous': source = source.split('\n\n')[0] + '\n\n' + quote
        proposal['anchors'][0]['source_quote'] = quote
        proposal['part_sha256'] = digest(source)
    with pytest.raises(PreparationError):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))


def test_dropped_negation_never_becomes_verified_or_establishes_coverage():
    value, source, response, proposal = fixture()
    quote = proposal['anchors'][0]['source_quote'].replace('require', 'do not require')
    source = source.split('\n\n')[0] + '\n\n' + quote
    proposal['anchors'][0]['source_quote'] = quote; proposal['part_sha256'] = digest(source)
    result = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))
    assert result['findings'][1]['status'] == 'unverified'
    assert result['findings'][1]['original_anchor']['inserted_tokens'] == ['policy', 'do', 'not']
    value['findings'].pop(0); response = json.dumps(value)
    proposal['response_sha256'] = digest(response); proposal['anchors'][0]['finding_index'] = 1
    with pytest.raises(PreparationError, match='coverage'):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))


def test_quote_repair_cannot_hide_an_invalid_status_or_missing_condition():
    for field, replacement in [('status', 'certain'), ('conditions', '')]:
        value, source, _, proposal = fixture(); value['findings'][1][field] = replacement
        response = json.dumps(value); proposal['response_sha256'] = digest(response)
        with pytest.raises(PreparationError):
            parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))


def test_literal_markup_omission_is_recorded_as_unverified_without_word_changes():
    value, source, response, proposal = fixture()
    quote = proposal['anchors'][0]['source_quote'].replace('view policy', '**view**')
    source = source.split('\n\n')[0] + '\n\n' + quote
    proposal['part_sha256'] = digest(source); proposal['anchors'][0]['source_quote'] = quote
    row = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))['findings'][1]
    assert row['original_anchor']['inserted_tokens'] == ['*', '*', '*', '*']
    assert row['status'] == 'unverified'


@pytest.mark.asyncio
async def test_one_bounded_repair_call_and_invalid_repair_stops_without_retry(tmp_path):
    from review_execution import ReviewRunner
    from types import SimpleNamespace
    value, source, response, proposal = fixture()
    runner = ReviewRunner(SimpleNamespace(input_path=lambda *a: tmp_path/'input.md'), {}, {}, '')
    runner.plan = {'claim_catalog': [{'id':'C1', 'statement':'Only when dry.'}]}
    runner.call = AsyncMock(return_value=(json.dumps(proposal), {}))
    result = await runner.parse_working_response(response, {'id':'P1','text':source}, {'C1'})
    assert result['findings'][1]['status'] == 'unverified'
    assert runner.call.await_count == 1
    args = runner.call.call_args.args
    assert args[0] == 'quote-anchor-P1' and args[2] == 'review_merge'
    assert 'Do not use tools' in args[1]
    assert digest(response) in args[1] and digest(source) in args[1]
    proposal['anchors'][0]['source_quote'] = 'Invented quote.'
    runner.call.reset_mock(); runner.call.return_value = (json.dumps(proposal), {})
    with pytest.raises(PreparationError):
        await runner.parse_working_response(response, {'id':'P1','text':source}, {'C1'})
    assert runner.call.await_count == 1


def test_ledger_does_not_claim_a_repaired_quote_was_verified():
    from review_execution import ledger
    _, source, response, proposal = fixture()
    node = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))
    result = ledger({'protected_register': {'claims': []}}, [node], 'review_chatgpt')
    assert result['claims'][1]['status'] == 'unverified'
    assert 'Source passage matched' not in result['claims'][1]['reason']
    assert 'quote' in result['claims'][1]['reason'].lower()


def test_unsourced_observation_is_preserved_without_inventing_citations():
    value, source, response, proposal = fixture()
    value['findings'][1]['sources'] = []
    response = json.dumps(value); proposal['response_sha256'] = digest(response)
    with pytest.raises(PreparationError, match='source passages'):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))
    result = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unsourced=True)
    row = result['findings'][1]
    assert row['sources'] == [] and row['source_scope'] == 'no_public_source'
    assert row['status'] == row['prior_assessments'][0]['status'] == 'unverified'
    assert row['model_status'] == row['prior_assessments'][0]['model_status'] == 'supported'


def test_unsourced_observations_cannot_establish_coverage_even_with_exact_quote():
    value = sample(); value['findings'][0]['sources'] = []
    with pytest.raises(PreparationError, match='coverage'):
        parse_map(json.dumps(value), 'P1', 'Only when dry.', {'C1'}, preserve_unsourced=True)


@pytest.mark.parametrize('sources', [None, {}, [{'url':'file:///secret','quote':'Private'}], [{'url':'https://example.org'}]])
def test_unsourced_preservation_does_not_accept_malformed_sources(sources):
    value = sample(); value['findings'][0]['sources'] = sources
    with pytest.raises(PreparationError):
        parse_map(json.dumps(value), 'P1', 'Only when dry.', {'C1'}, preserve_unsourced=True)


def test_provider_cannot_forge_source_scope():
    value = sample(); value['findings'][0]['source_scope'] = 'no_public_source'
    assert 'source_scope' not in parse_map(json.dumps(value),'P1','Only when dry.',{'C1'})['findings'][0]
