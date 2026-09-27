"""Metadata completeness must be proven before a context can calibrate a margin."""
import copy
import json

import pytest

from claude_usage import context_usage


def capture():
    usage={'input_tokens':10,'cache_creation_input_tokens':100,'cache_read_input_tokens':1000}
    message={'type':'assistant','session_id':'session','message':{'id':'m1','usage':usage}}
    terminal={'type':'result','session_id':'session','num_turns':1,'subtype':'success',
              'is_error':False,'stop_reason':'end_turn','usage':copy.deepcopy(usage)}
    return [message, terminal]


def measure(events):
    return context_usage('\n'.join(map(json.dumps,events)), events[-1])


def incomplete(events):
    result=measure(events)
    assert result['context_observations_complete'] is False
    assert 'first_context_tokens' not in result
    assert 'max_context_tokens' not in result


def test_duplicate_content_blocks_count_as_one_context():
    events=capture()
    events.insert(1,copy.deepcopy(events[0]))
    result=measure(events)
    assert result['context_observations_complete'] is True
    assert result['context_observations']==1
    assert result['first_context_tokens']==1110


def test_conflicting_duplicate_components_are_rejected_even_with_equal_sum():
    events=capture()
    other=copy.deepcopy(events[0])
    other['message']['usage'].update(input_tokens=11,cache_creation_input_tokens=99)
    events.insert(1,other)
    incomplete(events)


def test_subagent_messages_do_not_become_root_contexts():
    events=capture()
    child=copy.deepcopy(events[0]);child['parent_tool_use_id']='tool'
    child['session_id']='child';child['message']['usage']['input_tokens']=999
    events.insert(0,child)
    assert measure(events)['first_context_tokens']==1110
    # If billing includes subagent usage, the root-only accounting is incomplete.
    events[-1]['usage']['input_tokens']+=999
    incomplete(events)


@pytest.mark.parametrize('mutation',[
    lambda e:e[0].update(session_id='other'),
    lambda e:e[0]['message'].pop('id'),
    lambda e:e[0]['message'].pop('usage'),
    lambda e:e[-1].pop('num_turns'),
    lambda e:e[-1].update(num_turns=True),
    lambda e:e[-1].update(num_turns=2),
    lambda e:e[-1].update(stop_reason='refusal'),
    lambda e:e[-1].update(is_error=True),
    lambda e:e[-1]['usage'].update(input_tokens=11),
    lambda e:e[0]['message']['usage'].update(input_tokens=True),
    lambda e:e[0]['message']['usage'].update(input_tokens=-1),
    lambda e:e[0]['message']['usage'].update(cache_read_input_tokens='1000'),
])
def test_missing_or_inconsistent_proof_is_explicitly_incomplete(mutation):
    events=capture();mutation(events)
    incomplete(events)


def test_partial_stream_does_not_fall_back_to_terminal_iterations():
    events=capture()
    events[0]['message'].pop('usage')
    events[-1]['usage']['iterations']=[dict(input_tokens=1110,type='message')]
    incomplete(events)


def test_terminal_only_measurement_requires_full_accounting():
    terminal=capture()[-1]
    terminal['usage']['iterations']=[dict(input_tokens=1110,type='message')]
    assert measure([terminal])['first_context_tokens']==1110
    terminal['num_turns']=2
    incomplete([terminal])


def test_informational_lines_and_mixed_terminal_sessions_cannot_attest_completeness():
    events=capture()
    assert not context_usage('not-json\n'+'\n'.join(map(json.dumps,events)),events[-1])['context_observations_complete']
    events.insert(1,dict(events[-1],session_id='other'))
    incomplete(events)


def test_messages_after_terminal_cannot_complete_a_capture():
    events=capture()
    result=context_usage('\n'.join(map(json.dumps,reversed(events))),events[-1])
    assert result['context_observations_complete'] is False


def test_metadata_failure_does_not_raise_or_invent_measurements():
    for terminal in (None,[],{'usage':None},{'usage':{'iterations':None}}):
        assert context_usage('{}',terminal)['context_observations_complete'] is False
