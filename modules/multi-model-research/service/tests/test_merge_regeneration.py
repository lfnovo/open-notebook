import copy
import json

import pytest

from context_preparation import PreparationError, digest
from test_review_reconciliation import Runner, payload


def broken_runner(provider='Claude', repair_fails=False):
    runner=Runner(); runner.stage={'provider':provider}; original=runner.call
    async def call(key, request, profile):
        raw,usage=await original(key,request,profile)
        if key=='reconcile-batch-1' or (repair_fails and key.endswith('-artifact-retry-1')):
            raw='only the final fragment"}'
            runner.state['jobs'][key]['response']=raw
        return raw,usage
    runner.call=call
    return runner


@pytest.mark.asyncio
async def test_unrecoverable_merge_has_one_recorded_regeneration_and_never_repeats_on_resume():
    from review_reconciliation import reconcile
    runner=broken_runner(); data=payload(8); original=copy.deepcopy(data)
    result=await reconcile(runner,data,'Assess.\n')
    jobs=runner.state['jobs']; retry='reconcile-batch-1-artifact-retry-1'
    assert jobs[retry]['input']==jobs['reconcile-batch-1']['input']
    assert jobs['reconcile-batch-1']['response']=='only the final fragment"}'
    assert 'artifact_regeneration' in result and 'not reconstruction of lost output' in result
    assert digest(jobs['reconcile-batch-1']['response']) in result
    assert data==original
    count=len(runner.requests); saved=copy.deepcopy(jobs)
    assert await reconcile(runner,data,'Assess.\n')==result
    assert len(runner.requests)==count and runner.state['jobs']==saved


@pytest.mark.asyncio
async def test_second_invalid_artifact_stops_and_does_not_create_unbounded_retries():
    from review_reconciliation import reconcile
    runner=broken_runner(repair_fails=True)
    for _ in range(2):
        with pytest.raises(PreparationError):await reconcile(runner,payload(8),'Assess.\n')
    assert len([k for k in runner.state['jobs'] if 'artifact-retry' in k])==1
    assert len(runner.requests)==2


@pytest.mark.asyncio
async def test_other_providers_and_valid_but_incomplete_coverage_do_not_enter_tail_recovery():
    from review_reconciliation import reconcile
    runner=broken_runner('ChatGPT')
    with pytest.raises(PreparationError):await reconcile(runner,payload(8),'Assess.\n')
    assert len(runner.requests)==1
    runner=Runner();runner.stage={'provider':'Claude'};original=runner.call
    async def call(key,request,profile):
        raw,usage=await original(key,request,profile);value=json.loads(raw);value['reviewed_findings']=[]
        return json.dumps(value),usage
    runner.call=call
    with pytest.raises(PreparationError):await reconcile(runner,payload(8),'Assess.\n')
    assert len(runner.requests)==1


@pytest.mark.asyncio
@pytest.mark.parametrize('fault',['coverage','url','duplicate_json_key'])
async def test_regeneration_keeps_the_existing_integrity_gates(fault):
    from review_reconciliation import reconcile
    runner=broken_runner(); original=runner.call
    async def call(key,request,profile):
        raw,usage=await original(key,request,profile)
        if key.endswith('-artifact-retry-1'):
            value=json.loads(raw)
            if fault=='coverage': value['reviewed_findings']=[]
            if fault=='url': value['report']+=' https://invented.example/claim'
            raw=json.dumps(value)
            if fault=='duplicate_json_key': raw=raw.replace('{','{"coverage":[],',1)
        return raw,usage
    runner.call=call
    with pytest.raises(PreparationError):await reconcile(runner,payload(8),'Assess.\n')
    assert len(runner.requests)==2
