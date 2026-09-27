import hashlib
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from engine import AccountProvider, ServiceError


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


@pytest.mark.asyncio
@pytest.mark.parametrize('state', ['completed', 'failed', 'running', 'wrong_input', 'corrupt_result'])
async def test_receipt_recovery_is_read_only_and_checks_identity(tmp_path, monkeypatch, state):
    key = tmp_path / 'key'; key.write_text('test-key')
    provider = AccountProvider(key)
    stage = {'provider': 'ChatGPT', 'request_id': 'a' * 32, 'account_profile': 'research_review'}
    body = provider.request_body(stage, 'Frozen evidence')
    result = {'choices': [{'finish_reason': 'stop', 'message': {'content': 'Saved report'}}], 'usage': {}}
    receipt = {'state': state if state in ('completed', 'failed', 'running') else 'completed',
               'request_sha256': sha({k: v for k, v in body.items() if k != 'local_request_id'}),
               'result': result, 'result_sha256': sha(result), 'status': 502, 'message': 'CLI stopped'}
    if state == 'wrong_input': receipt['request_sha256'] = 'wrong'
    if state == 'corrupt_result': receipt['result']['choices'][0]['message']['content'] = 'Changed'
    get = AsyncMock(return_value=httpx.Response(200, json=receipt))
    post = AsyncMock(side_effect=AssertionError('Recovery must never submit'))
    monkeypatch.setattr(httpx.AsyncClient, 'get', get)
    monkeypatch.setattr(httpx.AsyncClient, 'post', post)
    if state == 'completed':
        assert (await provider.recover(stage, 'Frozen evidence'))[0] == 'Saved report'
    else:
        with pytest.raises(ServiceError) as error: await provider.recover(stage, 'Frozen evidence')
        assert error.value.settled == (state == 'failed')
        if state in ('wrong_input', 'corrupt_result'): assert error.value.kind == 'integrity_error'
    assert get.await_count == 1 and post.await_count == 0


@pytest.mark.asyncio
async def test_review_resumes_saved_response_without_resubmission(tmp_path):
    from review_execution import ReviewRunner
    from context_preparation import digest
    provider = type('Provider', (), {'recover': AsyncMock(return_value=('Saved report', {})),
                                   'synthesize': AsyncMock(side_effect=AssertionError('Duplicate request'))})()
    engine = type('Engine', (), {'provider': provider,
        'input_path': lambda *a: tmp_path / 'input.md', 'measure_input': lambda *a: {'fits': True}})()
    runner = ReviewRunner(engine, {'id': 'test'}, {'provider': 'ChatGPT'}, 'Input')
    runner.progress = AsyncMock()
    runner.state = {'jobs': {'P1': {'input_sha256': digest('Frozen evidence'),
                                  'status': 'in_flight', 'request_id': 'a' * 32}}}
    assert (await runner.call('P1', 'Frozen evidence', 'research_review'))[0] == 'Saved report'
    assert json.loads(runner.path.read_text())['jobs']['P1']['status'] == 'completed'
    assert provider.synthesize.await_count == 0
    assert runner.progress.call_args.args[-1] == 'a' * 32


@pytest.mark.asyncio
async def test_pending_recovery_observes_same_request_until_saved(tmp_path, monkeypatch):
    import engine
    provider=AccountProvider(tmp_path/'key')
    provider.recover=AsyncMock(side_effect=[
        ServiceError('Pending',409,kind='submission_uncertain',pending=True), ('Saved report',{})])
    sleep=AsyncMock();monkeypatch.setattr(engine.asyncio,'sleep',sleep)
    stage={'request_id':'a'*32}
    assert (await provider.recover_pending(stage,'Frozen input'))[0]=='Saved report'
    assert provider.recover.call_args_list[0]==provider.recover.call_args_list[1]
    assert sleep.await_count==1


@pytest.mark.asyncio
async def test_unknown_receipt_is_not_polled_or_resubmitted(tmp_path):
    provider=AccountProvider(tmp_path/'key')
    provider.recover=AsyncMock(side_effect=ServiceError('Unknown',409,kind='submission_uncertain'))
    with pytest.raises(ServiceError):await provider.recover_pending({'request_id':'a'*32},'Frozen input')
    assert provider.recover.await_count==1


@pytest.mark.parametrize('fault',[None,'artifact','tail','original_result','source_result'])
def test_derived_artifact_is_bound_to_original_receipt(fault):
    from context_preparation import digest
    text='{"coverage":["P4"],"findings":[]}'; tail='"findings":[]}'
    result={'choices':[{'message':{'content':tail},'finish_reason':'stop'}]}
    saved={'result':result,'result_sha256':sha(result),'artifact_recovery':{
        'kind':'claude-output-continuation-v1','text':text,'sha256':digest(text),
        'tail_sha256':digest(tail),'source_result_sha256':sha(result)}}
    if fault=='artifact':saved['artifact_recovery']['text']+='changed'
    if fault=='tail':saved['artifact_recovery']['tail_sha256']='wrong'
    if fault=='original_result':saved['result']['choices'][0]['message']['content']='different'
    if fault=='source_result':saved['artifact_recovery']['source_result_sha256']='wrong'
    if fault:
        with pytest.raises(ServiceError):AccountProvider.parse_artifact_recovery(saved)
    else:
        actual,usage=AccountProvider.parse_artifact_recovery(saved)
        assert actual==text and 'text' not in usage['artifact_recovery']
        assert saved['result']['choices'][0]['message']['content']==tail


@pytest.mark.asyncio
@pytest.mark.parametrize('profile',[None,'research_synthesis','research_review','review_merge'])
async def test_claude_recovery_profiles_use_verified_artifact(tmp_path,monkeypatch,profile):
    from context_preparation import digest
    key=tmp_path/'key';key.write_text('test')
    provider=AccountProvider(key)
    stage={'provider':'Claude','request_id':'b'*32}
    if profile is not None:stage['account_profile']=profile
    body=provider.request_body(stage,'Frozen')
    tail='"report":"Preserved"}';text='{"coverage":["P1"],'+tail
    result={'choices':[{'message':{'content':tail},'finish_reason':'stop'}]}
    saved={'state':'completed','request_sha256':sha({k:v for k,v in body.items() if k!='local_request_id'}),
           'result':result,'result_sha256':sha(result),'artifact_recovery':{
               'kind':'claude-output-continuation-v1','text':text,'sha256':digest(text),
               'tail_sha256':digest(tail),'source_result_sha256':sha(result)}}
    monkeypatch.setattr(httpx.AsyncClient,'get',AsyncMock(return_value=httpx.Response(200,json=saved)))
    monkeypatch.setattr(httpx.AsyncClient,'post',AsyncMock(side_effect=AssertionError('No resubmission')))
    actual,usage=await provider.recover(stage,'Frozen')
    assert actual==text and usage['artifact_recovery']['tail_sha256']==digest(tail)


@pytest.mark.asyncio
@pytest.mark.parametrize('profile',['research_review','review_merge'])
async def test_completed_fragment_is_recovered_once_without_replacing_it(tmp_path,profile):
    from review_execution import ReviewRunner
    from context_preparation import digest
    response='{"coverage":["P4"],"findings":[]}';tail='"findings":[]}'
    usage={'artifact_recovery':{'kind':'claude-output-continuation-v1',
        'sha256':digest(response),'tail_sha256':digest(tail)}}
    provider=type('Provider',(),{'recover':AsyncMock(return_value=(response,usage)),
        'synthesize':AsyncMock(side_effect=AssertionError('Never repeat the research'))})()
    engine=type('Engine',(),{'provider':provider,'input_path':lambda *a:tmp_path/'input.md',
        'measure_input':lambda *a:{'fits':True}})()
    runner=ReviewRunner(engine,{}, {'provider':'Claude'},'')
    job={'status':'completed','response':tail,'response_sha256':digest(tail),'usage':{},
         'input_sha256':digest('Frozen evidence'),'request_id':'a'*32}
    runner.state={'jobs':{'review-P4':job}}
    assert (await runner.call('review-P4','Frozen evidence',profile))[0]==response
    assert job['response']==tail and job['response_sha256']==digest(tail)
    assert (await runner.call('review-P4','Frozen evidence',profile))[0]==response
    assert provider.recover.await_count==1 and provider.synthesize.await_count==0
    job['artifact_response']+='corrupt'
    with pytest.raises(Exception,match='changed'):
        await runner.call('review-P4','Frozen evidence',profile)
