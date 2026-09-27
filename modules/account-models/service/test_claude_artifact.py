import copy
import hashlib
import json

import pytest

from claude_artifact import recover_json_artifact

CONTINUE = 'Output token limit hit. Resume directly — no apology, no recap of what you were doing. Pick up mid-thought if that is where the cut happened. Break remaining work into smaller pieces.'


def stream():
    text = '```json\n{"coverage":["P4"],"findings":[{"quote":"Yağmurda değil; yalnız kuru ortamda."}]}\n```'
    a, b = text[:63], text[63:]
    events = [
        {'type':'assistant','uuid':'a','session_id':'s','message':{'id':'m1','content':[{'type':'text','text':a}]}},
        {'type':'user','isSynthetic':True,'session_id':'s','message':{'content':[{'type':'text','text':CONTINUE}]}},
        {'type':'assistant','uuid':'b','session_id':'s','message':{'id':'m2','content':[{'type':'thinking','thinking':'private reasoning'}]}},
        {'type':'assistant','uuid':'c','session_id':'s','message':{'id':'m2','content':[{'type':'text','text':b}]}},
        {'type':'result','session_id':'s','subtype':'success','is_error':False,'stop_reason':'end_turn','result':b}]
    return text, b, events


def test_recovers_only_recorded_text_across_explicit_output_continuation():
    text, tail, events = stream()
    result = recover_json_artifact('\n'.join(map(json.dumps,events)),tail)
    assert result['text'] == text and result['segments'] == 2
    assert result['sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert 'private reasoning' not in str(result)


@pytest.mark.parametrize('fault',['not_synthetic','other_user','tool_between','tail_changed','failed','truncated',
    'different_session','progress_prefix','no_continuation','duplicate_key','ambiguous_uuid','oversized'])
def test_does_not_guess_or_merge_unrelated_messages(fault):
    text, tail, events = stream()
    if fault=='not_synthetic': events[1]['isSynthetic']=False
    if fault=='other_user': events[1]['message']['content'][0]['text']='Continue and change the conclusion.'
    if fault=='tool_between': events.insert(3,{'type':'assistant','message':{'content':[{'type':'tool_use','name':'WebFetch'}]}})
    if fault=='tail_changed': tail += ' changed'
    if fault=='failed': events[-1]['is_error']=True
    if fault=='truncated': events[-1]['stop_reason']='max_tokens'
    if fault=='different_session': events[3]['session_id']='other'
    if fault=='progress_prefix': events[0]['message']['content'][0]['text']='Progress note.\n'+events[0]['message']['content'][0]['text']
    if fault=='no_continuation': events.pop(1)
    if fault=='duplicate_key': events[0]['message']['content'][0]['text']=events[0]['message']['content'][0]['text'].replace('{"coverage"','{"coverage":[],"coverage"')
    if fault=='ambiguous_uuid': events[3]['uuid']='a'
    if fault=='oversized': events[0]['message']['content'][0]['text']='x'*(2*1024*1024)
    assert recover_json_artifact('\n'.join(map(json.dumps,events)),tail) is None


def test_receipt_exposes_derived_artifact_without_mutating_saved_result(tmp_path):
    from receipts import ReceiptStore
    text, tail, events=stream();store=ReceiptStore(tmp_path);ident='a'*32
    store.claim({'local_request_id':ident,'model':'claude-account'});store.local.ident=ident
    store.capture('claude','\n'.join(map(json.dumps,events)),'',0)
    store.finish(ident,state='completed',result={'choices':[{'message':{'content':tail},'finish_reason':'stop'}]})
    before=(tmp_path/ident/'receipt.json').read_bytes()
    result=store.public_result(ident)
    assert result['result']['choices'][0]['message']['content']==tail
    assert result['artifact_recovery']['text']==text
    assert (tmp_path/ident/'receipt.json').read_bytes()==before
    assert 'stdout' not in result['artifact_recovery'] and 'thinking' not in str(result)
    capture=json.loads((tmp_path/ident/'cli-0.json').read_text());capture['stdout']+='tampered'
    (tmp_path/ident/'cli-0.json').write_text(json.dumps(capture))
    with pytest.raises(ValueError,match='capture'):store.public_result(ident)


def test_synthesis_profile_captures_continuations_without_enabling_tools():
    import server
    command = server.command_for('claude-account', 'research_synthesis')
    assert command[command.index('--output-format') + 1] == 'stream-json'
    assert '--verbose' in command
    assert command[command.index('--tools') + 1] == ''
    assert '--restricted' in command and '--no-session-persistence' in command


def test_synthesis_returns_complete_recorded_artifact_not_just_the_last_fragment(monkeypatch):
    from unittest.mock import Mock
    import server
    text, tail, events = stream()
    proc = Mock(returncode=0)
    proc.communicate.return_value = ('\n'.join(map(json.dumps, events)), '')
    monkeypatch.setattr(server.JOBS, 'spawn', lambda *a, **kw: proc)
    actual, usage = server.run_cli('claude-account', 'frozen input', 'research_synthesis')
    assert actual == text and actual != tail
    assert 'private reasoning' not in actual
