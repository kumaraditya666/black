"""Windows job containment for the evaluation worker and its Git subprocesses."""
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


class _BasicLimits(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                ('flags', wintypes.DWORD), ('min_working', ctypes.c_size_t),
                ('max_working', ctypes.c_size_t), ('active_limit', wintypes.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]


class _IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ('reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic', _BasicLimits), ('io', _IOCounters), ('process_memory', ctypes.c_size_t),
                ('job_memory', ctypes.c_size_t), ('peak_process_memory', ctypes.c_size_t),
                ('peak_job_memory', ctypes.c_size_t)]


class Job:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Windows job containment is required')
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.k.CreateJobObjectW.restype = wintypes.HANDLE
        self.k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.k.SetInformationJobObject.restype = wintypes.BOOL
        self.k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.k.AssignProcessToJobObject.restype = wintypes.BOOL
        self.k.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.k.TerminateJobObject.restype = wintypes.BOOL
        self.k.CloseHandle.argtypes = [wintypes.HANDLE]
        self.k.CloseHandle.restype = wintypes.BOOL
        self.handle = self.k.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.k.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        if not self.k.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            raise ctypes.WinError(ctypes.get_last_error())

    def terminate(self):
        if self.handle and not self.k.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


def run_contained(payload, deadline_seconds):
    """Worker waits for stdin until after job assignment; the model never controls argv."""
    start = time.monotonic()
    process = None
    job = None
    try:
        job = Job()
        process = subprocess.Popen([sys.executable, '-m', 'blackbox.agent_worker'],
                                   cwd=str(Path(__file__).resolve().parents[1]),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        job.assign(process)
        remaining = max(0.001, deadline_seconds - (time.monotonic() - start))
        try:
            stdout, _ = process.communicate(json.dumps(payload, ensure_ascii=False).encode('utf8'), timeout=remaining)
        except subprocess.TimeoutExpired:
            job.terminate()
            process.communicate(timeout=5)
            return {'status': 'INVESTIGATION_FAILED', 'reason': 'DEADLINE_EXCEEDED', 'trace': [],
                    'wall_ms': int((time.monotonic()-start)*1000)}
        if process.returncode or len(stdout) > 1000000:
            return {'status': 'INVESTIGATION_FAILED', 'reason': 'WORKER_FAILED', 'trace': []}
        result = json.loads(stdout.decode('utf8'))
        result['contained_wall_ms'] = int((time.monotonic()-start)*1000)
        return result
    except KeyboardInterrupt:
        if job:
            job.terminate()
        if process:
            process.wait(timeout=5)
        raise
    except Exception:
        if process and process.poll() is None:
            if job:
                try:
                    job.terminate()
                except OSError:
                    process.kill()
            else:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return {'status': 'SECURITY_BLOCKED', 'reason': 'WORKER_CLEANUP_UNCONFIRMED', 'trace': []}
        return {'status': 'SECURITY_BLOCKED', 'reason': 'WORKER_CONTAINMENT_FAILED', 'trace': []}
    finally:
        if job:
            job.close()
