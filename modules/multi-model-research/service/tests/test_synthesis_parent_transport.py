"""Parent transport must preserve evidence and previously dispatched requests."""
import copy
import json
import pytest

from context_preparation import PreparationError, digest
from synthesis_parent_transport import payload, packed, adopt_legacy, pin_level, reserve_calls
from synthesis_json_text import restore
from test_synthesis_register import register
from test_synthesis_artifact_recovery import scenario


def fixture():
    plan = {'source_sha256': 'a'*64, 'protected_register': register(4),
            'source_inventory': ['https://example.org/paper']}
    nodes = [{'ids': ['P1'], 'report': 'Never safe. 2.5%, 2026-09-27; https://example.org/paper'},
             {'ids': ['R1'], 'claim_ids': ['C0'], 'report': 'Unverified; unresolved opposition.'},
             {'ids': ['R2'], 'claim_ids': ['C1'], 'report': 'Counter-evidence remains.'}]
    return plan, nodes


def test_parent_transport_reconstructs_every_field_and_literal():
    plan, nodes = fixture(); before = copy.deepcopy((plan, nodes))
    data = payload(plan, nodes); encoded = packed(data)
    from packet_markdown import evidence_body
    body, _ = evidence_body(encoded)
    packet = json.loads(body.split('\n', 1)[1].rsplit('\nEND_', 1)[0])
    assert restore(packet) == data
    assert (plan, nodes) == before
    assert 'untrusted evidence' in encoded


def test_partial_catalog_retains_linked_claims_and_full_parent_is_unchanged():
    import synthesis_register as registry
    plan,nodes=fixture();plan['register_mode']=registry.VERSION
    plan['register_catalog']=registry.catalog(plan['protected_register'])
    nodes[0]['report']+=' C3 is disputed; C30 is not C2.'
    before=copy.deepcopy(plan)
    partial=payload(plan,nodes[:1],partial=True)
    assert [c['id'] for c in partial['evidence_register']['claims']]==['C2','C3']
    assert partial['register_scope']['kind']=='linked_claims_only'
    assert partial['register_scope']['complete_catalog_in_final'] is True
    assert partial['evidence_register']['claims']==plan['register_catalog']['claims'][2:]
    assert len(payload(plan,nodes)['evidence_register']['claims'])==4 and plan==before


@pytest.mark.asyncio
async def test_adoption_reuses_exact_legacy_requests_and_preserves_coverage():
    plan, nodes = fixture(); state = {'jobs': {'reduce-0-0': {'coverage': ['P1'], 'status': 'in_flight'}}}
    calls = []
    async def call(key, data, ids, claim_ids=()):
        calls.append((key, data, ids, claim_ids)); return 'Saved reduced narrative.'
    result = await adopt_legacy(state, plan, nodes, call)
    assert calls[0][0] == 'reduce-0-0' and calls[0][2] == ['P1']
    assert result == [{'ids': ['P1'], 'report': 'Saved reduced narrative.'}] + nodes[1:]
    assert state['jobs']['reduce-0-0']['status'] == 'in_flight'
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('coverage', [['R1'], ['P1', 'P1'], ['missing'], []])
async def test_legacy_adoption_rejects_omitted_reordered_or_invented_coverage(coverage):
    plan, nodes = fixture(); state = {'jobs': {'reduce-0-0': {'coverage': coverage}}}
    async def forbidden(*a, **kw): pytest.fail('Malformed lineage must not dispatch')
    with pytest.raises(PreparationError): await adopt_legacy(state, plan, nodes, forbidden)


def test_pinned_level_detects_changed_children_and_grouping():
    _, nodes = fixture(); state = {}; groups = [nodes[:2], nodes[2:]]
    pin_level(state, 0, nodes, groups, ['one', 'two'])
    before = copy.deepcopy(state)
    pin_level(state, 0, nodes, groups, ['one', 'two'])
    assert state == before
    for field in ['report', 'ids']:
        changed = copy.deepcopy(nodes); changed[0][field] = 'different'
        with pytest.raises(PreparationError): pin_level(state, 0, changed, groups, ['one','two'])
    with pytest.raises(PreparationError): pin_level(state, 0, nodes, [nodes], ['new'])
    with pytest.raises(PreparationError): pin_level(state, 0, nodes, groups, ['changed','two'])


def test_call_reservation_counts_old_attempts_and_reserves_final():
    state = {'jobs': {str(i): {} for i in range(62)}}
    reserve_calls(state, ['new'], final=False)
    with pytest.raises(PreparationError): reserve_calls(state, ['new','another'], final=False)
    reserve_calls(state, ['new','another'], final=True)
    state['jobs']['new'] = {}
    reserve_calls(state, ['new'], final=False)


@pytest.mark.asyncio
@pytest.mark.parametrize('prior_state', ['completed', 'in_flight'])
async def test_execution_preserves_legacy_receipt_and_pins_new_transport(scenario, prior_state):
    from context_preparation import result_instructions
    from synthesis_parent_transport import legacy
    from engine import ServiceError
    s = scenario; s.engine.provider.answers = [s.good, s.good]
    await s.execute()
    state = json.loads(s.path.read_text()); old = state['jobs'].pop('final-0')
    nodes = [{'ids': ['P1'], 'report': 'Preserved conditions and uncertainty.'}]
    old['input'] = 'Task\n' + result_instructions(['P1']) + legacy(payload(state['plan'], nodes))
    old['input_sha256'] = digest(old['input']); old['status'] = prior_state
    if prior_state == 'in_flight':
        for k in ['response', 'response_sha256', 'usage']: old.pop(k, None)
    state['jobs']['reduce-0-0'] = old
    s.path.write_text(json.dumps(state)); original_plan = copy.deepcopy(state['plan'])
    calls_before = len(s.engine.provider.calls); recovered = []
    async def recover(child, text):
        assert child['request_id'] == old['request_id'] and text == old['input']
        recovered.append(child['request_id']); return s.good, {}
    s.engine.provider.recover = recover
    s.engine.provider.answers = [s.good]
    def measure(text, stage):
        util = .2 if 'lossless-json-text-tables-v1' in text else .99
        return {'fits': True, 'utilization': util}
    s.engine.measure_input = measure
    _, usage = await s.execute()
    assert len(s.engine.provider.calls) == calls_before + 1
    assert len(recovered) == (prior_state == 'in_flight')
    saved = json.loads(s.path.read_text())
    assert saved['plan'] == original_plan
    assert saved['jobs']['reduce-0-0']['input'] == old['input']
    assert saved['jobs']['reduce-0-0']['request_id'] == old['request_id']
    assert 'packed-final-0' in saved['jobs'] and usage['parent_transport_levels']
    before = len(s.engine.provider.calls); await s.execute()
    assert len(s.engine.provider.calls) == before
    saved['parent_transport']['nodes_sha256'] = 'tampered'
    s.path.write_text(json.dumps(saved))
    with pytest.raises(ServiceError, match='seed changed'): await s.execute()
    assert len(s.engine.provider.calls) == before


@pytest.mark.parametrize('mutation', ['omit', 'duplicate', 'reverse', 'empty', 'request_count'])
def test_new_group_plan_must_cover_each_child_exactly_once(mutation):
    _, nodes = fixture(); groups=[nodes[:2],nodes[2:]];requests=['one','two']
    if mutation=='omit':groups=groups[:1];requests=requests[:1]
    elif mutation=='duplicate':groups[1]=groups[0]
    elif mutation=='reverse':groups.reverse()
    elif mutation=='empty':groups.append([]);requests.append('empty')
    else:requests.pop()
    with pytest.raises(PreparationError):pin_level({},0,nodes,groups,requests)
