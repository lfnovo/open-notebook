import copy
import json
import pytest
from synthesis_json_text import encode, restore
from context_preparation import PreparationError


@pytest.mark.parametrize('indent', [None, 0, 1, 2, 4, '\t'])
@pytest.mark.parametrize('ensure_ascii', [False, True])
def test_exact_report_bytes_key_order_and_all_evidence_survive(indent, ensure_ascii):
    data = {'z': [{'id':'C1','condition':'Not safe. İstisna, 🧪', 'n':2.5,'status':'unverified',
                   'urls':['https://example.org/a#b'], 'opposition':None, 'literal':{'$json_object':[0]}}], 'a':False}
    raw = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
    report = 'Original\n```evidence-ledger\n'+raw+'\n```\nEnd\r\n'
    value = {'findings':[{'report':report},{'report':report}], '$formatted_text':'literal collision'}
    original = copy.deepcopy(value); packet=encode(value)
    # Round trip through serialized storage too: sorted transport keys cannot reorder source keys.
    restored = restore(json.loads(json.dumps(packet,sort_keys=True,ensure_ascii=False)))
    assert restored == original and value == original
    assert restored['findings'][0]['report'].encode() == report.encode()


@pytest.mark.parametrize('raw', ['{"same":1,"same":2}', '{"x":NaN}', '{"n":1e+02}', 'not JSON'])
def test_unsupported_or_ambiguous_json_remains_literal(raw):
    value={'report':'```evidence-ledger\n'+raw+'\n```'}
    packet=encode(value)
    assert not packet['schema'] and restore(packet)==value


@pytest.mark.parametrize('raw', ['{ "x" : 1 }', '{"claims":[\n{"id":"C1","value":"a \\" b"},\n{"id":"C2","value":false}\n]}'.replace('a \\" b','a \\" b'), '{\n  "claims": [\n    {"id":"C1","value":1}\n  ]\n}'])
def test_hybrid_whitespace_is_encoded_and_reconstructed_exactly(raw):
    value={'report':'```evidence-ledger\n'+raw+'\n```'}
    packet=encode(value)
    assert packet['schema']
    assert restore(json.loads(json.dumps(packet,sort_keys=True)))==value


def test_multiple_blocks_and_repeated_records_are_not_deleted():
    row={'id':'C1','reason':'Only under the original condition.','status':'disputed'}
    raw=json.dumps({'claims':[row]*60},indent=2,ensure_ascii=False)
    value={'report':'```json\n'+raw+'\n```\n```evidence-ledger\n'+raw+'\n```'}
    packet=encode(value)
    assert restore(packet)==value
    assert len(json.dumps(packet)) < len(json.dumps(value))


@pytest.mark.parametrize('mutation',['hash','schema_order','schema_key','schema_missing','encoding','payload'])
def test_changed_format_or_content_cannot_be_accepted(mutation):
    packet=encode({'report':'```evidence-ledger\n'+json.dumps({'z':1,'a':2},indent=2)+'\n```'})
    if mutation=='hash':packet['original_sha256']='0'*64
    elif mutation=='schema_order':packet['schema'][0].reverse()
    elif mutation=='schema_key':packet['schema'][0][0]='changed'
    elif mutation=='schema_missing':packet['schema']=[]
    elif mutation=='encoding':packet['encoding']='other'
    else:packet['payload']['decoded_sha256']='changed'
    with pytest.raises(PreparationError):restore(packet)
