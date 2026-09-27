"""Transmission, not an archive-only sidecar, must contain every original byte."""
import copy
import json
import pytest
from context_compaction import compact_packet, expand_prompt
from packet_markdown import markdown_packet


def packet(text):
    return {'question':'Question?', 'scope':'Preserve exceptions', 'reports':[
        {'stage':'research_chatgpt','content':text,'citations':[],'evidence':[]}]}


def test_exact_repetition_is_referenced_without_mutating_report_or_provenance():
    original=packet(('An exact long assertion with its qualification; independent repetition is not independent evidence. '*4+'\r\n')*30)
    saved=copy.deepcopy(original)
    result=compact_packet(original,1,len)
    assert result['audit']['referenced_blocks']>0
    assert result['audit']['saved_tokens']>0
    assert expand_prompt(result['prompt'])==markdown_packet(original)
    assert result['packet']==original==saved
    assert result['audit']['removed_sentences']==0


@pytest.mark.parametrize('text',[
    'The assertion below is false.\nThis is safe.\n',
    'Yalnız yetişkinlerde.\r\nÇocuklarda hiçbir zaman kullanılmaz.\r\n',
    '```mermaid\ngraph TD; A-->B\n```\n```evidence-ledger\n{"claims":[]}\n```\n',
    'https://a.test/x?x=1\nhttps://a.test/x?x=2\n',
    '## 2. Önemli koşullar\nÜç örnek vardır.\nI cannot verify this source.\n',
])
def test_unique_content_never_disappears(text):
    original=packet(text);result=compact_packet(original,1,len)
    assert result['packet']==original
    assert expand_prompt(result['prompt'])==markdown_packet(original)
    assert not result['fits']


def test_dictionary_tampering_cannot_pass_the_round_trip():
    original=packet(('Unique protected exception. '*12+'\n')*40)
    result=compact_packet(original,1,len)
    corrupted=result['prompt'].replace('Unique protected exception.','Wrong assertion.',1)
    with pytest.raises(ValueError):expand_prompt(corrupted)


def test_already_fitting_and_nonshrinking_inputs_remain_unchanged():
    original=packet('hello')
    result=compact_packet(original,999999,len)
    assert result['prompt']==markdown_packet(original)
    assert result['fits']
    result=compact_packet(original,1,lambda _:100)
    assert result['prompt']==markdown_packet(original)


def test_references_cannot_add_or_remove_occurrences():
    original=packet(('A long repeated observation. '*15+'\n')*15)
    result=compact_packet(original,1,len)
    body=result['prompt'];meta=json.loads(body.split('\n',3)[2])
    ref=next(iter(meta['dictionary']))
    with pytest.raises(ValueError):expand_prompt(body.replace(ref,'MISSING',1))


def test_same_content_has_stable_encoding():
    original=packet(('Evidence with qualifiers '*20+'\n')*30)
    a=compact_packet(original,1,len);b=compact_packet(copy.deepcopy(original),1,len)
    assert a['prompt']==b['prompt']
    assert expand_prompt(a['prompt'])==markdown_packet(original)
