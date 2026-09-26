"""A lost continuation may be regenerated once, never silently repaired."""
import asyncio
import json
from types import SimpleNamespace

import pytest
import segmented_execution
from context_preparation import PreparationError, digest, envelope, parse_result, plan_segments
from engine import ServiceError


@pytest.fixture
def scenario(tmp_path):
    body = envelope('Original conditions and uncertainty. https://example.org/source')
    prompt = 'Task\n' + body
    plan = plan_segments(body, lambda s: True)
    plan.update(protected_register={}, source_inventory=['https://example.org/source'])
    stage = {'id': 's', 'round': 4, 'provider': 'Claude', 'account_profile': 'research_synthesis'}
    run = {'id': 'r', 'paused': False, 'stages': [stage]}
    path = tmp_path / 'segmented-journal.json'
    path.write_text(json.dumps({'version': 'segmented-evidence-v1', 'input_sha256': digest(prompt),
                                'plan': plan, 'jobs': {}}))
    good = json.dumps({'coverage': ['P1'], 'report': 'Preserved conditions and uncertainty.'})
    class Provider:
        def __init__(self):
            self.calls = []; self.answers = ['broken JSON', good, good]; self.recoveries = 0
        async def synthesize(self, child, text):
            self.calls.append((dict(child), text))
            answer = self.answers.pop(0)
            if isinstance(answer, Exception): raise answer
            return answer, {'prompt_tokens': 100}
        async def recover(self, child, text):
            self.recoveries += 1
            assert child['request_id'] == self.calls[0][0]['request_id']
            assert text == self.calls[0][1]
            return 'broken JSON', {'prompt_tokens': 100}
    class Store:
        async def save(self, value): pass
    class Engine:
        lock = asyncio.Lock(); store = Store()
        async def get(self, rid): return run
        def stage(self, r, sid): return stage
        def input_path(self, r, s): return tmp_path / 'input-packet.md'
        def measure_input(self, text, s): return {'fits': True, 'utilization': .1}
    engine = Engine(); engine.provider = Provider()
    return SimpleNamespace(engine=engine, run=run, stage=stage, prompt=prompt, path=path, good=good,
                           execute=lambda: segmented_execution.execute(engine, run, stage, prompt))


@pytest.mark.asyncio
async def test_one_regeneration_preserves_original_and_exact_frozen_input(scenario):
    s = scenario
    report, usage = await s.execute()
    calls = s.engine.provider.calls
    assert len(calls) == 3 and calls[0][1] == calls[1][1]
    assert calls[0][0]['request_id'] != calls[1][0]['request_id']
    state = json.loads(s.path.read_text()); old = state['jobs']['map-P1']
    assert old['response'] == 'broken JSON' and old['response_sha256'] == digest('broken JSON')
    event = state['artifact_regenerations']['map-P1']
    assert event['same_input_sha256'] == old['input_sha256']
    assert event['replacement_job'] == 'map-P1-artifact-retry-1'
    assert event['replacement_response_sha256'] == digest(s.good)
    assert usage['artifact_regenerations'] == [event] and 'regenerated' in report
    assert usage['calls'] == 3
    await s.execute()
    assert len(calls) == 3
    # The replacement record cannot be rewritten and accepted as a new generation.
    state['artifact_regenerations']['map-P1']['same_input_sha256'] = 'tampered'
    s.path.write_text(json.dumps(state))
    with pytest.raises(ServiceError, match='regeneration'): await s.execute()
    assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize('replacement', ['still invalid', 'coverage', 'source', 'refusal'])
async def test_failed_replacement_is_not_repeated_on_resume(scenario, replacement):
    s = scenario
    alternatives = {'coverage': json.dumps({'coverage': [], 'report': 'Wrong'}),
                    'source': json.dumps({'coverage': ['P1'], 'report': 'https://invented.invalid'}),
                    'refusal': ServiceError('Declined', 403, kind='provider_error', settled=True)}
    s.engine.provider.answers = ['broken JSON', alternatives.get(replacement, replacement)]
    for _ in range(2):
        with pytest.raises(ServiceError): await s.execute()
    assert len(s.engine.provider.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('invalid', [
    '{"coverage":[],"report":"Missing coverage"}',
    '{"coverage":["P1"],"report":"old","report":"new"}',
    '{"coverage":["P1"],"report":"ok","value":NaN}',
    '[]',
])
async def test_semantic_schema_and_duplicate_key_failures_never_regenerate(scenario, invalid):
    s = scenario; s.engine.provider.answers = [invalid]
    with pytest.raises(ServiceError): await s.execute()
    assert len(s.engine.provider.calls) == 1 and s.engine.provider.recoveries == 0


@pytest.mark.asyncio
async def test_saved_stream_artifact_recovered_without_resubmission(scenario):
    s = scenario
    async def recover(child, text):
        return s.good, {'prompt_tokens': 100, 'artifact_recovery': {
            'kind': 'claude-output-continuation-v1', 'tail_sha256': digest('broken JSON'),
            'sha256': digest(s.good)}}
    s.engine.provider.recover = recover
    report, usage = await s.execute()
    assert report == 'Preserved conditions and uncertainty.'
    assert len(s.engine.provider.calls) == 2
    job = json.loads(s.path.read_text())['jobs']['map-P1']
    assert job['response'] == 'broken JSON' and job['artifact_response'] == s.good
    await s.execute()
    assert len(s.engine.provider.calls) == 2
    state = json.loads(s.path.read_text()); state['jobs']['map-P1']['artifact_response'] += ' '
    s.path.write_text(json.dumps(state))
    with pytest.raises(ServiceError): await s.execute()


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['recovery_unavailable', 'changed_receipt', 'uncertain', 'paused', 'limit', 'other_provider'])
async def test_guards_do_not_allow_blind_replacement(scenario, mode):
    s = scenario
    async def recover(child, text):
        if mode == 'recovery_unavailable': raise ServiceError('Receipt unavailable', 409, kind='submission_uncertain')
        if mode == 'changed_receipt': return 'different invalid', {}
        if mode == 'paused': s.run['paused'] = True
        if mode == 'limit':
            # Inject through the runner's initial journal rather than external mutation.
            pass
        return 'broken JSON', {}
    s.engine.provider.recover = recover
    if mode == 'uncertain': s.engine.provider.answers = [OSError('Disconnected')]
    if mode == 'other_provider': s.stage['provider'] = 'ChatGPT'
    if mode == 'limit':
        state = json.loads(s.path.read_text())
        state['jobs'] = {f'prior-{i}': {'status': 'completed'} for i in range(63)}
        s.path.write_text(json.dumps(state))
    with pytest.raises(ServiceError): await s.execute()
    assert len(s.engine.provider.calls) == 1


@pytest.mark.parametrize('text', [
    '{"coverage":["P1"],"report":"first","report":"second"}',
    '{"coverage":["P1"],"report":"x","x":Infinity}',
])
def test_strict_result_parser_does_not_misclassify_ambiguous_json_as_truncation(text):
    with pytest.raises(PreparationError) as error: parse_result(text, ['P1'])
    assert not isinstance(error.value.__cause__, json.JSONDecodeError)
