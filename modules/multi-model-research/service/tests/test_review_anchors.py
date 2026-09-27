import json

import pytest

from context_preparation import PreparationError
from review_contract import parse_map
from test_account_review import sample


def test_inline_identifier_markup_keeps_exact_source_anchor():
    value = sample()
    value['findings'][0]['original_quote'] = 'ToolCallEnd is not tool completion.'
    original = 'Türkçe ığüş. `ToolCallEnd` is not tool completion. Other text.'
    result = parse_map(json.dumps(value), 'P1', original, {'C1'})
    row = result['findings'][0]
    assert row['original_quote'] == value['findings'][0]['original_quote']
    anchor = row['original_anchor']
    assert anchor['scope'] == 'part'
    assert anchor['text'] == '`ToolCallEnd` is not tool completion.'
    assert original.encode()[anchor['start_byte']:anchor['end_byte']].decode() == anchor['text']


def test_catalog_quote_must_link_a_claim_referenced_by_this_part():
    value = sample()
    local = sample()['findings'][0]; local['original_quote'] = 'Local source inventory.'
    value['findings'].append(local)
    original = 'Local source inventory.'
    result = parse_map(json.dumps(value), 'P1', original, {'C1'},
                       claim_catalog=[{'id':'C1','statement':'Only when dry.'}])
    row = result['findings'][0]
    assert row['original_quote'] == 'Only when dry.'
    assert row['original_anchor']['scope'] == 'claim_catalog'
    assert row['original_anchor']['claim_id'] == 'C1'
    assert row['original_anchor']['text'] == 'Only when dry.'
    assert row['original_anchor']['counted_as_part_evidence'] is False
    assert row['status'] == 'unverified' and row['model_status'] == 'supported'
    assert row['prior_assessments'][0]['status'] == 'unverified'


@pytest.mark.parametrize('original,catalog', [
    ('Unrelated part', [{'id':'C1','statement':'Only when dry.'}]),
    ('| C10 | Another claim |', [{'id':'C1','statement':'Only when dry.'}]),
    ('| C1 | Inventory |', [{'id':'C2','statement':'Only when dry.'}]),
    ('| C1 | Inventory |', [{'id':'C1','statement':'Always safe.'}]),
])
def test_wrong_scope_or_unlinked_catalog_cannot_validate_quote(original, catalog):
    with pytest.raises(PreparationError):
        parse_map(json.dumps(sample()), 'P1', original, {'C1'}, claim_catalog=catalog)


@pytest.mark.parametrize('quote,original', [
    ('ToolCallEnd is tool completion.', '`ToolCallEnd` is not tool completion.'),
    ('Always safe.', 'Only when dry.'),
    ('x < y', '`x <= y`'),
    ('ToolCallEnd is safe.', '```ToolCallEnd``` is safe.'),
    ('ToolCallEnd is safe.', 'Intro\n```text\n`ToolCallEnd` is safe.\n```'),
])
def test_anchor_matching_cannot_paraphrase_negation_operators_or_fences(quote,original):
    value=sample();value['findings'][0]['original_quote']=quote
    with pytest.raises(PreparationError):parse_map(json.dumps(value),'P1',original,{'C1'})


def test_provider_cannot_forge_validator_provenance():
    value=sample();row=value['findings'][0]
    row.update(original_anchor={'scope':'claim_catalog','claim_id':'invented'},
               model_status='certain',verification={'unverified_sources':0})
    row['prior_assessments'][0]['model_status']='certain'
    parsed=parse_map(json.dumps(value),'P1','Only when dry.',{'C1'})['findings'][0]
    assert not {'original_anchor','model_status','verification'} & parsed.keys()
    assert 'model_status' not in parsed['prior_assessments'][0]
