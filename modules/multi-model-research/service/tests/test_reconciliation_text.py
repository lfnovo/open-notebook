import copy
import json

import pytest

from context_preparation import PreparationError
from test_review_reconciliation import Runner, payload


def source():
    from reconciliation_tables import encoded
    repeated = 'Never promote this finding: only valid in dry conditions. https://example.com/a?x=1'
    notes = {'records': [{'id': f'P1:F{i}', 'status': 'unverified', 'reason': repeated,
                         'condition': [False, None, 0, -0.0, 'Türkçe olumsuzluk']} for i in range(40)]}
    return {'report': 'Keep the complete narrative.\n\n```json\n' + encoded(notes) + '\n```\nAfterword.',
            'same': [repeated] * 10, 'literal': {'$text': 'literal', '$strings': 2, '$string': 0,
                                              '$text_object': [], '$string_object': [], '$table': {'rows': []}}}


def test_full_reconstruction_preserves_narrative_json_values_repetitions_and_reserved_markers():
    from reconciliation_text import transport, restore
    from reconciliation_tables import encoded
    value = source(); original = copy.deepcopy(value)
    packet = transport(value)
    assert encoded(restore(packet)) == encoded(original)
    assert value == original
    assert len(encoded(packet)) < len(encoded(value))
    assert packet['encoding'] == 'lossless-json-text-tables-v1'


@pytest.mark.parametrize('block', [
    '{"a":1,"a":2}', '{ "a": 1 }', '{"n":NaN}', 'not JSON',
    '{"$text":[{"json":{"k":1}}]}', '{"a":"\\n```\\n"}',
])
def test_arbitrary_json_and_marker_text_is_never_rewritten(block):
    from reconciliation_text import transport, restore
    value = {'report': 'Before\n```json\n' + block + '\n```\nAfter'}
    assert restore(transport(value)) == value


def test_text_transport_rejects_tampering_and_unknown_version():
    from reconciliation_text import transport, restore
    value = transport(source())
    for field, changed in [('decoded_sha256', '0'*64), ('encoding', 'unknown')]:
        invalid = copy.deepcopy(value); invalid[field] = changed
        with pytest.raises(PreparationError): restore(invalid)
    invalid = copy.deepcopy(value); invalid['strings'][0] += ' altered'
    with pytest.raises(PreparationError): restore(invalid)


@pytest.mark.parametrize('value', ['~01', '~-1', '~3', '~1.0', '~True'])
def test_invalid_dictionary_references_are_not_guessed(value):
    from reconciliation_text import restore_strings
    with pytest.raises(PreparationError): restore_strings(value, ['one'])


@pytest.mark.parametrize('value', [{'$text':[{'text':'x','json':{}}]}, {'$text':'x'},
    {'$text':[{'unknown':'x'}]}, {'$text_object':[['a',1],['a',2]]}])
def test_invalid_text_fragments_are_not_silently_joined(value):
    from reconciliation_text import restore_text
    with pytest.raises(PreparationError): restore_text(value)


def test_transport_checks_reconstruction_before_use(monkeypatch):
    import reconciliation_text as codec
    monkeypatch.setattr(codec, 'restore_text', lambda value: {})
    with pytest.raises(PreparationError, match='reconstruction'): codec.transport(source())


class TextRunner(Runner):
    async def call(self, key, request, profile):
        if not key.startswith('reconcile-tree-text-'):
            return await super().call(key, request, profile)
        from reconciliation_text import restore
        if key in self.state['jobs']:
            assert self.state['jobs'][key]['input'] == request
            return self.state['jobs'][key]['response'], {}
        self.requests.append((key, request))
        packet = json.loads(request.split('BEGIN_REFERENCE_',1)[1].split('\n',1)[1].split('\nEND_REFERENCE_',1)[0])
        data = restore(packet)
        raw = json.dumps({'coverage': data['coverage'], 'reviewed_findings': data['finding_ids'],
                          'report':'All conclusions remain qualified and unverified.'})
        self.state['jobs'][key] = {'input': request, 'response': raw}
        return raw, {}


@pytest.mark.asyncio
async def test_text_fallback_is_bounded_immutable_and_resumes_without_new_calls():
    from review_reconciliation import reconcile
    runner = TextRunner(); data = payload(8); original = copy.deepcopy(data)
    measure = runner.engine.measure_input
    def limited(request, child):
        if '"child_reports"' in request and '"lossless-json-text-tables-v1"' not in request:
            return {'fits':False}
        return measure(request, child)
    runner.engine.measure_input = limited
    report = await reconcile(runner, data, 'Assess.\n')
    assert data == original and 'lossless-json-text-tables-v1' in report
    jobs = copy.deepcopy(runner.state['jobs']); count = len(runner.requests)
    assert await reconcile(runner, data, 'Assess.\n') == report
    assert runner.state['jobs'] == jobs and len(runner.requests) == count
    runner.state['reconciliation_encodings']['1']['requests'][0]['decoded_sha256'] = 'tampered'
    with pytest.raises(PreparationError, match='encoding plan changed'):
        await reconcile(runner, data, 'Assess.\n')


@pytest.mark.asyncio
async def test_oversized_text_transport_still_stops_before_parent_dispatch():
    from review_reconciliation import reconcile
    runner = TextRunner(); measure = runner.engine.measure_input
    runner.engine.measure_input = lambda request, child: {'fits':False} if '"child_reports"' in request else measure(request,child)
    with pytest.raises(PreparationError): await reconcile(runner, payload(8), 'Assess.\n')
    assert not any(key.startswith('reconcile-tree-') for key, _ in runner.requests)


def test_literal_tildes_and_keys_are_never_mistaken_for_dictionary_references():
    from reconciliation_text import transport, restore
    value = {'~0':['~0','~~1','~literal','~~','~9999999999999999999999999999'],
             'repeated':['~a repeated literal string']*10}
    assert restore(transport(value)) == value
