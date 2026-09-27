"""A valid negative repair result is preserved, never accepted as evidence."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from context_preparation import PreparationError, digest
from review_contract import parse_map
from test_review_quote_repair import fixture


def declined():
    value, source, response, proposal = fixture()
    proposal['anchors'] = []
    return value, source, response, proposal


def test_declined_repair_preserves_every_field_without_fabricating_an_anchor():
    value, source, response, proposal = declined()
    result = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)
    row = result['findings'][1]
    for key in ('statement', 'original_quote', 'conditions', 'counter_evidence', 'limits', 'sources', 'prior_claim_ids'):
        assert row[key] == value['findings'][1][key]
    assert len(result['findings']) == len(value['findings'])
    assert row['status'] == row['prior_assessments'][0]['status'] == 'unverified'
    assert row['model_status'] == row['prior_assessments'][0]['model_status'] == 'supported'
    anchor = row['original_anchor']
    assert anchor['scope'] == 'unresolved_part_quote'
    assert anchor['counted_as_part_evidence'] is False
    assert anchor['model_quote_sha256'] == digest(row['original_quote'])
    assert anchor['repair_response_sha256'] == digest(json.dumps(proposal))
    assert anchor['part_sha256'] == digest(source)
    assert not {'text', 'start_byte', 'end_byte', 'claim_id'} & set(anchor)


def test_negative_repair_remains_rejected_without_explicit_preservation():
    _, source, response, proposal = declined()
    with pytest.raises(PreparationError):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))


@pytest.mark.parametrize('fault', ['response_hash', 'part_hash', 'extra_field', 'null', 'empty_object', 'partial'])
def test_preservation_does_not_accept_invalid_or_incomplete_repairs(fault):
    value, source, response, proposal = declined()
    if fault == 'response_hash': proposal['response_sha256'] = 'wrong'
    if fault == 'part_hash': proposal['part_sha256'] = 'wrong'
    if fault == 'extra_field': proposal['verified'] = True
    if fault == 'null': proposal['anchors'] = None
    if fault == 'empty_object': proposal['anchors'] = {}
    if fault == 'partial':
        value['findings'].append(copy.deepcopy(value['findings'][1]))
        response = json.dumps(value); proposal['response_sha256'] = digest(response)
        proposal['anchors'] = [{'finding_index': 2, 'source_quote': source.split('\n\n')[1]}]
    with pytest.raises(PreparationError):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)


def test_unresolved_quotes_never_satisfy_part_coverage():
    value, source, _, proposal = declined()
    value['findings'].pop(0); response = json.dumps(value)
    proposal['response_sha256'] = digest(response)
    with pytest.raises(PreparationError, match='coverage'):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)


def test_provider_cannot_forge_unresolved_provenance_or_hide_invalid_claim_ids():
    value, source, _, proposal = declined()
    value['findings'][0]['original_anchor'] = {'scope': 'unresolved_part_quote'}
    response = json.dumps(value); proposal['response_sha256'] = digest(response)
    result = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)
    assert 'original_anchor' not in result['findings'][0]
    value['findings'][1]['prior_claim_ids'] = ['invented']
    response = json.dumps(value); proposal['response_sha256'] = digest(response)
    with pytest.raises(PreparationError, match='invented'):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)


@pytest.mark.asyncio
async def test_runner_reuses_one_negative_repair_and_ledger_keeps_it_unverified(tmp_path):
    from review_execution import ReviewRunner, ledger, unresolved_quote_notice
    _, source, response, proposal = declined()
    runner = ReviewRunner(SimpleNamespace(input_path=lambda *a: tmp_path/'input.md'), {}, {}, '')
    runner.plan = {'claim_catalog': [{'id': 'C1', 'statement': 'Only when dry.'}]}
    runner.call = AsyncMock(return_value=(json.dumps(proposal), {}))
    node = await runner.parse_working_response(response, {'id': 'P1', 'text': source}, {'C1'})
    assert runner.call.await_count == 1
    assert runner.call.call_args.args[0] == 'quote-anchor-P1'
    claims = ledger({'protected_register': {'claims': []}}, [node], 'review_chatgpt')['claims']
    assert claims[1]['status'] == 'unverified'
    assert 'unresolved' in claims[1]['reason'].lower()
    assert 'Source passage matched' not in claims[1]['reason']
    assert '1' in unresolved_quote_notice([node])
    assert 'unverified' in unresolved_quote_notice([node])
    assert unresolved_quote_notice([]) == ''


@pytest.mark.asyncio
async def test_public_passage_matches_cannot_promote_unresolved_original_provenance(tmp_path):
    from review_execution import ReviewRunner
    _, source, response, proposal = declined()
    node = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)
    runner = ReviewRunner(SimpleNamespace(input_path=lambda *a: tmp_path/'input.md'), {}, {}, '')
    runner.state = {}; runner.progress = AsyncMock(); runner.persist = AsyncMock()
    runner.verify_source = AsyncMock(return_value={'verification': 'passage_matched_not_fact_checked'})
    await runner.check_sources(node, 'P1', {})
    row = node['findings'][1]
    assert row['verification']['unverified_sources'] == 0
    assert row['status'] == row['prior_assessments'][0]['status'] == 'unverified'
    assert row['model_status'] == row['prior_assessments'][0]['model_status'] == 'supported'
    assert row['original_anchor']['scope'] == 'unresolved_part_quote'


def test_changed_words_are_unresolved_not_accepted_as_an_exact_or_repaired_quote():
    value, source, _, proposal = fixture()
    value['findings'][1]['original_quote'] = value['findings'][1]['original_quote'].replace('require', 'avoid')
    response = json.dumps(value); proposal['response_sha256'] = digest(response)
    with pytest.raises(PreparationError, match='substituted'):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal))
    row = parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)['findings'][1]
    assert row['original_quote'] == value['findings'][1]['original_quote']
    assert row['status'] == 'unverified'
    assert row['original_anchor']['scope'] == 'unresolved_part_quote'
    assert row['original_anchor']['match'] == 'rejected_quote_repair'
    assert not {'text', 'start_byte', 'end_byte'} & set(row['original_anchor'])


@pytest.mark.parametrize('fault', ['invented_passage', 'new_url', 'too_large'])
def test_rejected_association_cannot_hide_an_invalid_passage(fault):
    value, source, _, proposal = fixture()
    value['findings'][1]['original_quote'] = value['findings'][1]['original_quote'].replace('require', 'avoid')
    quote = proposal['anchors'][0]['source_quote']
    if fault == 'invented_passage': quote += ' Invented.'
    if fault == 'new_url': quote += ' https://unknown.example/'
    if fault == 'too_large': quote += ' Extra.' * 2000
    if fault != 'invented_passage': source += '\n\n' + quote
    proposal['anchors'][0]['source_quote'] = quote
    response = json.dumps(value)
    proposal.update(response_sha256=digest(response), part_sha256=digest(source))
    with pytest.raises(PreparationError):
        parse_map(response, 'P1', source, {'C1'}, quote_repair=json.dumps(proposal), preserve_unanchored=True)
