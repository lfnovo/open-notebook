import copy
import json
from types import SimpleNamespace

import pytest
from context_preparation import digest,envelope,plan_segments
from engine import Engine
import segmented_execution


@pytest.mark.parametrize('fault',[None,'input','plan','part','policy'])
def test_resume_validates_frozen_plan_without_repartitioning(tmp_path,monkeypatch,fault):
    body=envelope('Retained evidence and exceptions.\n'*20);prompt='Task\n'+body
    plan=plan_segments(body,lambda value:True)
    plan.update(protected_register={},source_inventory=[])
    stage={'id':'s','attempts':2,'mode':'account','preparation':dict(segmented_execution.summary(plan),
           status='running',current='map-P2',completed_calls=1)}
    state={'input_sha256':digest(prompt),'plan':copy.deepcopy(plan),'jobs':{}}
    if fault=='input':state['input_sha256']='wrong'
    if fault=='plan':state['plan']['source_inventory']=['https://changed.invalid']
    if fault=='part':state['plan']['parts'][0]['text']='changed'
    (tmp_path/'segmented-journal.json').write_text(json.dumps(state))
    engine=SimpleNamespace(segmented=True,budget=True,evidence_id=lambda p:{'format':'markdown'},
                           input_path=lambda *a:tmp_path/'input-packet.md')
    monkeypatch.setattr(segmented_execution,'plan_for',lambda *a:pytest.fail('Frozen plan must not be rebuilt'))
    policy={'blocked':True,'block_status':'integrity_error' if fault=='policy' else 'context_limit',
            'findings':[{'id':'ECA-011'}]}
    result=Engine.preparation_plan(engine,{'stages':[stage]},stage,prompt,policy)
    if fault:
        assert policy['blocked']
    else:
        assert result==stage['preparation'] and not policy['blocked']
