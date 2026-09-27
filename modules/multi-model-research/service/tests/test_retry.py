"""Automatic backoff retry and the user-triggered retry.

The schedule is 1, 5, 30, 90 and 250 minutes. What must never happen is a stall that
needs a person, or an uncertain submission, being repeated on a timer.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import uuid
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from engine import Engine, ServiceError
from workflow import AUTO_RETRY, RETRY_BACKOFF, STAGES
from test_workflow import engine, settle  # noqa: F401  (pytest fixtures)


def stage_of(run, stage_id):
    return next(s for s in run['stages'] if s['id'] == stage_id)


async def failing_run(engine, stage_id='synthesis_chatgpt'):
    """Drive a run to the point where one account stage has failed."""
    engine.provider.fail.add(stage_id)
    run = await engine.create({'question': 'Backoff denemesi', 'scope': '', 'language': 'Türkçe',
                               'auto_synthesize': True, 'notebook_id': None}, uuid.uuid4().hex)
    for sid, _, rnd, _ in STAGES:
        if rnd <= 2:
            packet = await engine.packet(run['id'], sid)
            await engine.import_report(run['id'], sid, 'Rapor ' + sid + ' https://example.org/' + sid,
                                       [], '', packet['sha256'], [])
    await settle(engine)
    return await engine.get(run['id'])


# --------------------------------------------------------------------------
# The schedule
# --------------------------------------------------------------------------
def test_backoff_is_one_five_thirty_ninety_and_two_hundred_fifty_minutes():
    assert [s // 60 for s in RETRY_BACKOFF] == [1, 5, 30, 90, 250]


def test_each_failure_arms_the_next_interval_then_stops():
    stage = {'status': 'failed', 'retry_index': 0, 'next_retry_at': None}
    seen = []
    for _ in RETRY_BACKOFF:
        before = datetime.now(timezone.utc)
        Engine.arm_retry(stage)
        gap = datetime.fromisoformat(stage['next_retry_at']) - before
        seen.append(round(gap.total_seconds() / 60))
    assert seen == [1, 5, 30, 90, 250]
    # The schedule is exhausted: the stage now waits for the user.
    Engine.arm_retry(stage)
    assert stage['next_retry_at'] is None


@pytest.mark.parametrize('status', ['submission_uncertain', 'login_required', 'verification_required',
                                    'context_limit', 'research_unavailable', 'interrupted', 'quota_wait'])
def test_states_that_need_a_person_are_never_rearmed(status):
    assert status not in AUTO_RETRY
    stage = {'status': status, 'retry_index': 0, 'next_retry_at': 'x'}
    Engine.arm_retry(stage)
    assert stage['next_retry_at'] is None
    assert Engine.retry_due(stage) is False


@pytest.mark.parametrize('status', AUTO_RETRY)
def test_transient_states_are_rearmed(status):
    stage = {'status': status, 'retry_index': 0, 'next_retry_at': None}
    Engine.arm_retry(stage)
    assert stage['next_retry_at'] is not None


# --------------------------------------------------------------------------
# The timer
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_failed_stage_is_armed_and_not_run_before_it_is_due(engine):
    run = await failing_run(engine)
    stage = stage_of(run, 'synthesis_chatgpt')
    assert stage['status'] == 'failed' and stage['next_retry_at'] and stage['retry_index'] == 1
    engine.provider.calls.clear()
    assert await engine.sweep_retries() == [], 'a stage that is not due yet must not run'
    assert not engine.provider.calls


@pytest.mark.asyncio
async def test_a_due_stage_runs_itself_again(engine):
    run = await failing_run(engine)
    async with engine.lock:
        stored = await engine.get(run['id'])
        stage_of(stored, 'synthesis_chatgpt')['next_retry_at'] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        await engine.store.save(stored)
    engine.provider.fail.clear()
    engine.provider.calls.clear()
    assert await engine.sweep_retries() == [run['id']]
    await settle(engine)
    assert 'synthesis_chatgpt' in [c[0] for c in engine.provider.calls]
    after = stage_of(await engine.get(run['id']), 'synthesis_chatgpt')
    assert after['status'] == 'completed'
    assert after['retry_index'] == 0 and after['next_retry_at'] is None


@pytest.mark.asyncio
async def test_a_paused_run_does_not_retry_itself(engine):
    run = await failing_run(engine)
    await engine.action(run['id'], 'pause')
    async with engine.lock:
        stored = await engine.get(run['id'])
        stage_of(stored, 'synthesis_chatgpt').update(
            status='failed', next_retry_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
        await engine.store.save(stored)
    engine.provider.calls.clear()
    assert await engine.sweep_retries() == []
    assert not engine.provider.calls


# --------------------------------------------------------------------------
# The button
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_manual_retry_runs_now_and_resets_the_schedule(engine):
    run = await failing_run(engine)
    engine.provider.fail.clear()
    engine.provider.calls.clear()
    result = await engine.retry_stage(run['id'], 'synthesis_chatgpt')
    await settle(engine)
    assert 'synthesis_chatgpt' in [c[0] for c in engine.provider.calls]
    stage = stage_of(await engine.get(run['id']), 'synthesis_chatgpt')
    assert stage['retry_index'] == 0 and stage['next_retry_at'] is None
    assert result['status'] in ('running', 'completed', 'needs_attention', 'ready')


@pytest.mark.asyncio
async def test_manual_retry_refuses_a_running_or_healthy_stage(engine):
    run = await failing_run(engine)
    # A completed stage is not a stall.
    with pytest.raises(ServiceError):
        await engine.retry_stage(run['id'], 'research_gemini')
    async with engine.lock:
        stored = await engine.get(run['id'])
        stage_of(stored, 'synthesis_claude')['status'] = 'running'
        await engine.store.save(stored)
    with pytest.raises(ServiceError):
        await engine.retry_stage(run['id'], 'synthesis_claude')


@pytest.mark.asyncio
async def test_manual_retry_does_not_resume_the_whole_run(engine):
    run = await failing_run(engine)
    await engine.action(run['id'], 'pause')
    engine.provider.calls.clear()
    with pytest.raises(ServiceError):await engine.retry_stage(run['id'], 'synthesis_chatgpt')
    assert (await engine.get(run['id']))['paused']
    assert not engine.provider.calls

@pytest.mark.asyncio
async def test_quota_wait_drops_legacy_timer_on_restart_and_never_retries(engine):
    run=await failing_run(engine)
    async with engine.lock:
        run=await engine.get(run['id'])
        stage_of(run,'synthesis_chatgpt').update(status='quota_wait',next_retry_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        await engine.store.save(run)
    engine.provider.calls.clear()
    await engine.recover()
    assert stage_of(await engine.get(run['id']),'synthesis_chatgpt')['next_retry_at'] is None
    assert not await engine.sweep_retries()
    assert not engine.provider.calls

@pytest.mark.asyncio
async def test_account_quota_displays_reported_reset_without_echoing_raw_error(tmp_path,monkeypatch):
    import httpx
    from engine import AccountProvider
    reset=(datetime.now(timezone.utc)+timedelta(days=4)).replace(second=0,microsecond=0)
    client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(429,json={
        'error':{'message':'private provider diagnostic','retry_at':reset.isoformat()}})))
    monkeypatch.setattr('engine.httpx.AsyncClient',lambda **kwargs:client)
    key=tmp_path/'key';key.write_text('isolated-test-key')
    with pytest.raises(ServiceError) as error:
        await AccountProvider(key).synthesize({'provider':'Gemini'},'test brief')
    assert error.value.kind=='quota_wait'
    assert reset.strftime('%Y-%m-%d %H:%M UTC') in str(error.value)
    assert 'private provider diagnostic' not in str(error.value)
