import json

import pytest

from context_preparation import PreparationError, digest
from review_contract import parse_map, read_working_object
from test_account_review import sample


def test_provider_prose_surrounding_one_json_artifact_is_preserved():
    raw=json.dumps(sample(),ensure_ascii=False)
    prefix='Research is complete; compiling the structured artifact now.\n\n'
    suffix='\nCaution: the original trial did not cover wet conditions.\n'
    response=prefix+'```json\n'+raw+'\n```'+suffix
    parsed=parse_map(response,'P1','Only when dry.',{'C1'})
    envelope=parsed['provider_envelope']
    assert envelope['prefix']==prefix and envelope['suffix']==suffix
    assert envelope['response_sha256']==digest(response)
    assert response.encode()[envelope['start_byte']:envelope['end_byte']].decode()==raw+'\n'
    for k in ('statement','original_quote','conditions','sources','limits','counter_evidence'):
        assert parsed['findings'][0][k]==sample()['findings'][0][k]


@pytest.mark.parametrize('fault',['two_artifacts','unclosed_extra_fence','duplicate_key','invalid_json','non_object','non_finite'])
def test_ambiguous_or_invalid_fenced_artifacts_still_fail(fault):
    body=json.dumps(sample())
    if fault=='duplicate_key':body=body.replace('"coverage":','"coverage":[],"coverage":',1)
    if fault=='invalid_json':body=body[:-5]
    if fault=='non_object':body='[]'
    if fault=='non_finite':body='{"x": NaN}'
    response='A provider note.\n```json\n'+body+'\n```\n'
    if fault=='two_artifacts':response+='```json\n'+body+'\n```\n'
    if fault=='unclosed_extra_fence':response+='```json\n'
    with pytest.raises(PreparationError):read_working_object(response)


def test_normal_json_and_normal_fence_do_not_invent_wrapper_metadata():
    raw=json.dumps(sample())
    for text in (raw,'```json\n'+raw+'\n```'):
        assert 'provider_envelope' not in parse_map(text,'P1','Only when dry.',{'C1'})


def test_provider_cannot_forge_envelope_provenance():
    value=sample();value['provider_envelope']={'prefix':'Invented wrapper','response_sha256':'fake'}
    assert 'provider_envelope' not in parse_map(json.dumps(value),'P1','Only when dry.',{'C1'})


def test_multibyte_wrapper_offsets_and_body_hash_are_byte_exact():
    raw=json.dumps(sample(),ensure_ascii=False);text='Açıklama: yağış sınırı.\n```json\n'+raw+'\n```\n'
    _,wrapper=read_working_object(text)
    body=text.encode()[wrapper['start_byte']:wrapper['end_byte']].decode()
    assert body==raw+'\n' and digest(body)==wrapper['artifact_sha256']
