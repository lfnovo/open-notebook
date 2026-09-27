"""Real processes and queues; no LLM calls."""
import concurrent.futures
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
import pytest
from cancellation import Jobs, RequestCancelled


def test_cancel_before_submit_and_reused_ids_never_spawn():
    jobs=Jobs();ident=uuid.uuid4().hex
    assert jobs.cancel(ident)['settled']
    with pytest.raises(RequestCancelled):
        with jobs.request(ident):pytest.fail('cancelled request launched')
    other=uuid.uuid4().hex
    with jobs.request(other):pass
    with pytest.raises(ValueError):
        with jobs.request(other):pytest.fail('duplicate request launched')


def test_cancel_kills_real_owned_process_and_child_without_touching_other_jobs(tmp_path):
    jobs=Jobs();ident=uuid.uuid4().hex;ready=threading.Event();holder={}
    child=tmp_path/'child.pid'
    code=('import subprocess,sys,time,pathlib,signal; '
          'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
          'p=subprocess.Popen([sys.executable,"-c","import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"]); '
          f'pathlib.Path({str(child)!r}).write_text(str(p.pid)); time.sleep(60)')
    def run():
        with jobs.request(ident):
            p=jobs.spawn([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            holder['process']=p;ready.set()
            p.communicate(timeout=20)
            jobs.check()
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result=pool.submit(run);assert ready.wait(2)
            deadline=time.monotonic()+3
            while not child.exists() and time.monotonic()<deadline:time.sleep(.02)
            assert child.exists()
            assert jobs.cancel(ident)['settled']
            with pytest.raises(RequestCancelled):result.result(timeout=5)
            assert holder['process'].poll() is not None
            assert unrelated.poll() is None
            # macOS can retain a dead grandchild as a zombie until init reaps it.
            state=subprocess.run(['ps','-o','stat=','-p',child.read_text()],capture_output=True,text=True).stdout.strip()
            assert not state or state.startswith('Z')
    finally:
        unrelated.terminate();unrelated.wait()
        if 'process' in holder and holder['process'].poll() is None:
            os.killpg(holder['process'].pid,signal.SIGKILL);holder['process'].wait()


def test_queued_cancel_does_not_take_account_slot(monkeypatch):
    import server
    jobs=Jobs();monkeypatch.setattr(server,'JOBS',jobs)
    queue=server.AccountQueue();queued=threading.Event();ident=uuid.uuid4().hex
    def run():
        with jobs.request(ident):
            queued.set()
            with queue.slot():pytest.fail('cancelled queue entry acquired account')
    with concurrent.futures.ThreadPoolExecutor() as pool:
        with queue.slot():
            future=pool.submit(run);assert queued.wait(2)
            assert jobs.cancel(ident)['settled']
            with pytest.raises(RequestCancelled):future.result(timeout=2)
            assert queue.status()=={'active':1,'waiting':0}


def test_bad_cancel_ids_cannot_select_processes():
    for ident in ('', '../1', 123, 'a'*31, 'x'*32):
        with pytest.raises(ValueError):Jobs().cancel(ident)


def test_restart_preserves_cancel_tombstone_and_refuses_to_claim_orphan_is_stopped(tmp_path):
    ident=uuid.uuid4().hex;cancelled=uuid.uuid4().hex
    jobs=Jobs(tmp_path);jobs.record(ident,'running');jobs.cancel(cancelled)
    restarted=Jobs(tmp_path)
    assert restarted.cancel(ident)=={'cancelled':False,'settled':False}
    with pytest.raises(RequestCancelled):
        with restarted.request(cancelled):pytest.fail('resubmitted cancelled request after restart')
