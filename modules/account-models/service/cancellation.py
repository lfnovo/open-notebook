"""Cancellation of bridge-owned process groups, scoped to a single request ID.

Tombstones close the cancel-before-submit race. No process discovery or broad kills.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time


class RequestCancelled(Exception):
    pass


@dataclass
class Job:
    cancelled: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    processes: list = field(default_factory=list)
    created: float = field(default_factory=time.monotonic)
    claimed: bool = False


class Jobs:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else None
        self.lock = threading.RLock()
        self.entries = {}
        self.local = threading.local()

    def recorded(self, ident):
        if self.directory and (self.directory / ident).is_file():
            return (self.directory / ident).read_text()
        return None

    def record(self, ident, state):
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = self.directory / ident
            temp = path.with_suffix('.tmp')
            with open(temp, 'w', opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
                stream.write(state); stream.flush(); os.fsync(stream.fileno())
            temp.replace(path)

    def validate(self, ident):
        if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{32}', ident):
            raise ValueError('Invalid local request ID')

    def current(self):
        return getattr(self.local, 'job', None)

    def check(self, job=None):
        job = job or self.current()
        if job and job.cancelled.is_set():
            raise RequestCancelled('Account request cancelled by the user.')

    @contextmanager
    def request(self, ident):
        if ident is None:
            yield
            return
        self.validate(ident)
        with self.lock:
            self.entries = {k: j for k, j in self.entries.items()
                            if not j.done.is_set() or time.monotonic() - j.created < 86400}
            if ident not in self.entries and self.recorded(ident):
                raise RequestCancelled('This request ID already exists; it will not be submitted again.')
            job = self.entries.setdefault(ident, Job())
            self.check(job)
            if job.claimed:
                raise ValueError('Local request ID was already used')
            self.record(ident, 'running')
            job.claimed = True
            self.local.job = job
        try:
            yield
        finally:
            with self.lock:
                self.record(ident, 'finished')
                job.done.set()
                self.local.job = None

    def spawn(self, *args, **kwargs):
        with self.lock:
            self.check()
            proc = subprocess.Popen(*args, **kwargs)
            job = self.current()
            if job:
                job.processes.append(proc)
            return proc

    @staticmethod
    def signal(proc, sig, force=False):
        # Popen is retained; the PID cannot be reused while its child is alive.
        if force or proc.poll() is None:
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                pass

    def cancel(self, ident):
        self.validate(ident)
        with self.lock:
            if ident not in self.entries and self.recorded(ident) == 'running':
                # A crash may leave an orphan CLI. Do not pretend its cancellation is confirmed.
                return {'cancelled': False, 'settled': False}
            job = self.entries.setdefault(ident, Job())
            if self.recorded(ident) == 'finished':job.done.set()
            job.cancelled.set()
            if not job.claimed:
                self.record(ident, 'cancelled')
                job.done.set()
            processes = [] if job.done.is_set() else list(job.processes)
            for proc in processes:
                self.signal(proc, signal.SIGTERM)
        if not job.done.wait(3):
            for proc in processes:
                self.signal(proc, signal.SIGKILL, force=True)
            job.done.wait(3)
        return {'cancelled': True, 'settled': job.done.is_set()}

    def shutdown(self):
        with self.lock:
            ids = [ident for ident, job in self.entries.items() if not job.done.is_set()]
        for ident in ids:
            self.cancel(ident)


JOBS = Jobs()
