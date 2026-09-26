"""A settled source-inventing artifact may be regenerated once, never accepted."""
import json

import pytest
from context_preparation import digest
from engine import ServiceError
from test_synthesis_artifact_recovery import scenario


def source_failure(s):
    invalid = json.dumps({'coverage': ['P1'], 'report':
                         'Version detail https://example.org/sourcev3'})
    s.stage['provider'] = 'ChatGPT'
    s.engine.provider.answers = [invalid, s.good, s.good]
    async def recover(child, text):
        s.engine.provider.recoveries += 1
        assert child['request_id'] == s.engine.provider.calls[0][0]['request_id']
        assert text == s.engine.provider.calls[0][1]
        return invalid, {'prompt_tokens': 100}
    s.engine.provider.recover = recover
    return invalid


@pytest.mark.asyncio
async def test_source_replacement_preserves_original_and_revalidates(scenario):
    s = scenario; invalid = source_failure(s)
    before = json.loads(s.path.read_text())['plan']
    report, usage = await s.execute()
    calls = s.engine.provider.calls
    assert len(calls) == 3 and s.engine.provider.recoveries == 1
    assert calls[1][1].startswith(calls[0][1])
    assert 'Do not infer version suffixes' in calls[1][1]
    assert calls[0][0]['request_id'] != calls[1][0]['request_id']
    state = json.loads(s.path.read_text())
    assert state['plan'] == before
    assert state['jobs']['map-P1']['response'] == invalid
    event = state['source_regenerations']['map-P1']
    assert event['original_response_sha256'] == digest(invalid)
    assert event['original_input_sha256'] == digest(calls[0][1])
    assert event['replacement_input_sha256'] == digest(calls[1][1])
    assert event['replacement_response_sha256'] == digest(s.good)
    assert usage['source_regenerations'] == [event]
    assert 'source-validation' in report.lower()
    await s.execute()
    assert len(calls) == 3 and s.engine.provider.recoveries == 1
    state['source_regenerations']['map-P1']['original_response_sha256'] = 'changed'
    s.path.write_text(json.dumps(state))
    with pytest.raises(ServiceError): await s.execute()
    assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['source', 'coverage', 'json', 'refusal'])
async def test_invalid_source_replacement_cannot_loop_or_fall_back(scenario, failure):
    s = scenario; invalid = source_failure(s)
    replacement = {'source': invalid, 'coverage': json.dumps({'coverage': [], 'report': 'Wrong'}),
                   'json': 'broken', 'refusal': ServiceError('Declined', 403, kind='research_unavailable', settled=True)}[failure]
    s.engine.provider.answers = [invalid, replacement]
    for _ in range(2):
        with pytest.raises(ServiceError): await s.execute()
    assert len(s.engine.provider.calls) == 2
    assert json.loads(s.path.read_text())['jobs']['map-P1']['response'] == invalid


@pytest.mark.asyncio
@pytest.mark.parametrize('guard', ['no_receipt', 'unknown_receipt', 'changed_receipt', 'pause', 'budget', 'calls'])
async def test_source_replacement_respects_existing_guards(scenario, guard):
    s = scenario; invalid = source_failure(s)
    async def recover(child, text):
        if guard == 'unknown_receipt': raise ServiceError('Unknown', 409, kind='submission_uncertain')
        if guard == 'changed_receipt': return s.good, {}
        if guard == 'pause': s.run['paused'] = True
        if guard == 'budget': s.engine.measure_input = lambda *a: {'fits': False, 'utilization': 2}
        return invalid, {}
    if guard == 'no_receipt': s.engine.provider.recover = None
    else: s.engine.provider.recover = recover
    if guard == 'calls':
        state = json.loads(s.path.read_text()); state['jobs'] = {f'prior-{i}': {'status': 'completed'} for i in range(63)}
        s.path.write_text(json.dumps(state))
    with pytest.raises(ServiceError): await s.execute()
    assert len(s.engine.provider.calls) == 1


@pytest.mark.asyncio
async def test_unknown_replacement_is_recovered_without_another_submission(scenario):
    s = scenario; invalid = source_failure(s)
    s.engine.provider.answers = [invalid, OSError('Disconnected'), s.good]
    with pytest.raises(ServiceError) as error: await s.execute()
    assert error.value.kind == 'submission_uncertain'
    state = json.loads(s.path.read_text())
    replacement = state['jobs']['map-P1-source-retry-1']
    async def recover(child, text):
        assert child['request_id'] == replacement['request_id']
        assert digest(text) == replacement['input_sha256']
        return s.good, {'prompt_tokens': 100}
    s.engine.provider.recover = recover
    await s.execute()
    assert len(s.engine.provider.calls) == 3  # original, disconnected replacement, final


@pytest.mark.asyncio
async def test_provider_refusal_never_enters_source_recovery(scenario):
    s = scenario; source_failure(s)
    s.engine.provider.answers = [ServiceError('Declined', 403, kind='research_unavailable', settled=True)]
    with pytest.raises(ServiceError): await s.execute()
    assert len(s.engine.provider.calls) == 1 and s.engine.provider.recoveries == 0
    assert 'source_regenerations' not in json.loads(s.path.read_text())
