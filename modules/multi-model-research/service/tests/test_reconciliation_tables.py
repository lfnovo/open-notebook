import copy
import json

import pytest

from context_preparation import PreparationError
from test_review_reconciliation import Runner, payload


def test_tables_round_trip_every_field_and_reserved_input_keys():
    from reconciliation_tables import pack, unpack, transport
    data = [{'id': 'P1:F1', 'status': 'unverified', 'negation': 'Not safe: Türkçe.',
             'conditions': ['Only if dry.', None, False, 0, -0.0],
             'other': {'$table': {'columns': ['malicious'], 'rows': []}, '$object': 'literal'}}] * 3
    original = copy.deepcopy(data)
    assert unpack(pack(data)) == original and data == original
    packet = transport(data)
    assert packet['encoding'] == 'lossless-json-tables-v1'
    assert unpack(packet['value']) == data
    assert packet['value']['$table']['columns'] == sorted(data[0])
    assert len(packet['value']['$table']['rows']) == 3


@pytest.mark.parametrize('value', [[], {}, [1, 'a', None], [{'a':1}, {'b':2}], [{},{}]])
def test_non_tabular_values_and_mixed_record_shapes_survive(value):
    from reconciliation_tables import pack, unpack
    assert unpack(pack(value)) == value


@pytest.mark.parametrize('bad', [
    {'$table': {'columns':['a','a'], 'rows':[[1,2]]}},
    {'$table': {'columns':['a'], 'rows':[[1,2]]}},
    {'$table': {'columns':['a'], 'rows':[[1]], 'extra':True}},
    {'$table': {'columns':[1], 'rows':[[1]]}},
    {'$table': {'columns':['a'], 'rows':['x']}},
    {'$object': [['a',1],['a',2]]},
    {'$object': [['a',1]], 'other':2},
])
def test_malformed_transport_never_reconstructs_silently(bad):
    from reconciliation_tables import unpack
    with pytest.raises(PreparationError): unpack(bad)


def test_transport_detects_any_roundtrip_loss(monkeypatch):
    import reconciliation_tables as tables
    monkeypatch.setattr(tables, 'unpack', lambda value: {})
    with pytest.raises(PreparationError, match='round trip'):
        tables.transport({'protected':'Never remove this.'})


class TableRunner(Runner):
    async def call(self, key, request, profile):
        from reconciliation_tables import unpack
        if not key.startswith('reconcile-tree-table-'):
            return await super().call(key,request,profile)
        assert self.engine.measure_input(request,{})['fits']
        if key in self.state['jobs']:
            assert self.state['jobs'][key]['input']==request
            return self.state['jobs'][key]['response'],{}
        self.requests.append((key,request))
        value=json.loads(request.split('BEGIN_REFERENCE_',1)[1].split('\n',1)[1].split('\nEND_REFERENCE_',1)[0])
        data=unpack(value['value'])
        raw=json.dumps({'coverage':data['coverage'],'reviewed_findings':data['finding_ids'],
                       'report':'All conclusions remain qualified and unverified.'})
        self.state['jobs'][key]={'input':request,'response':raw}
        return raw,{}


@pytest.mark.asyncio
async def test_table_fallback_converges_without_dropping_values_and_pins_resume():
    from review_reconciliation import reconcile
    runner=TableRunner(); data=payload(8); original=copy.deepcopy(data)
    original_measure=runner.engine.measure_input
    # Simulate a metadata-bound root: individual legacy children fit, a pair
    # needs columnar encoding. The decoded record content is exactly the same.
    def measure(request, child):
        if '"child_reports"' in request and '"lossless-json-tables-v1"' not in request:
            value=json.loads(request.split('BEGIN_REFERENCE_',1)[1].split('\n',1)[1].split('\nEND_REFERENCE_',1)[0])
            return {'fits':len(value['child_reports'])<=1}
        return original_measure(request,child)
    runner.engine.measure_input=measure
    report=await reconcile(runner,data,'Assess the evidence.\n')
    assert data==original and 'lossless-json-tables-v1' in report
    assert 'reconciliation_encodings' in runner.state
    jobs=copy.deepcopy(runner.state['jobs']); count=len(runner.requests)
    assert await reconcile(runner,data,'Assess the evidence.\n')==report
    assert runner.state['jobs']==jobs and len(runner.requests)==count
    runner.state['reconciliation_encodings']['1']['requests'][0]['input_sha256']='changed'
    with pytest.raises(PreparationError,match='encoding plan changed'):
        await reconcile(runner,data,'Assess the evidence.\n')


@pytest.mark.asyncio
async def test_fallback_does_not_loosen_capacity_if_tables_also_cannot_converge():
    from review_reconciliation import reconcile
    runner=TableRunner(); original=runner.engine.measure_input
    def measure(request,child):
        if any(version in request for version in ['"lossless-json-tables-v1"', '"lossless-json-text-tables-v1"']): return {'fits':False}
        if '"child_reports"' in request:
            value=json.loads(request.split('BEGIN_REFERENCE_',1)[1].split('\n',1)[1].split('\nEND_REFERENCE_',1)[0])
            return {'fits':len(value['child_reports'])<=1}
        return original(request,child)
    runner.engine.measure_input=measure
    with pytest.raises(PreparationError):await reconcile(runner,payload(8),'Assess.\n')
