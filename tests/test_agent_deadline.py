import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from blackbox.agent_retrieval import investigate_with_retrieval
from blackbox.deadline_worker import Job
from blackbox.deadline_worker import run_contained
from blackbox.providers import Provider
from blackbox.repair import fixtures
from blackbox.schemas import Event, Frame
from blackbox.store import Store

ROOT = Path(__file__).resolve().parents[1]
REV = 'ee674ffb46dc83c5d78585ac23cd86217bcc2dec'
REGISTRY = ROOT / 'fixtures/repair/m3f-registry.json'
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows job containment')


def test_job_terminates_blocked_git_subprocess(tmp_path):
    pidfile = tmp_path / 'child.pid'
    code = ('import subprocess,sys,time; sys.stdin.readline(); '
            'p=subprocess.Popen(["git","cat-file","--batch"],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); '
            'open(sys.argv[1],"w").write(str(p.pid)); time.sleep(60)')
    job = Job()
    parent = subprocess.Popen([sys.executable, '-c', code, str(pidfile)], stdin=subprocess.PIPE)
    try:
        job.assign(parent)
        parent.stdin.write(b'go\n'); parent.stdin.flush()
        deadline = time.monotonic() + 10
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        assert pidfile.exists()
        child_pid = int(pidfile.read_text())
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, child_pid)
        assert handle, 'Git exited before the cancellation test'
        try:
            assert kernel.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT: still running
            job.terminate()
            parent.wait(timeout=5)
            assert kernel.WaitForSingleObject(handle, 5000) == 0
        finally:
            kernel.CloseHandle(handle)
    finally:
        job.close()
        if parent.poll() is None:
            parent.kill(); parent.wait()


def test_deadline_stops_worker_blocked_on_provider(tmp_path, monkeypatch):
    received, release = threading.Event(), threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.set()
            release.wait(10)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    monkeypatch.setenv('BLACKBOX_OLLAMA_URL', f'http://127.0.0.1:{server.server_port}')
    monkeypatch.setattr(fixtures, 'REGISTRY_PATH', REGISTRY)
    fixture = fixtures.get_fixture('m3f_feed_multi')
    ev = fixture['event']
    store = Store(str(tmp_path / 'store.db'))
    incident, _ = store.ingest(Event(event_id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc), commit=REV,
        exception_type=ev['exception_type'], message=ev['message'], traceback='recorded', frames=[Frame(**ev['frame'])]))
    start = time.monotonic()
    try:
        result = investigate_with_retrieval(store, ROOT, incident, fixture['name'], Provider('ollama', 'test'), deadline_seconds=4)
        assert received.is_set()
        assert result['reason'] == 'DEADLINE_EXCEEDED'
        assert time.monotonic()-start < 7
    finally:
        release.set(); server.shutdown(); server.server_close()


def test_user_cancellation_terminates_worker(monkeypatch):
    spawned = []
    original = subprocess.Popen.communicate
    def interrupted(process, *args, **kwargs):
        spawned.append(process)
        raise KeyboardInterrupt()
    monkeypatch.setattr(subprocess.Popen, 'communicate', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_contained({}, 10)
    assert spawned and spawned[0].poll() is not None
