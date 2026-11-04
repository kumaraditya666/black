"""Disposable test execution with explicit isolation limits.

Docker (no network, read-only root, dropped capabilities, memory/CPU/PID limits) is used when an
image is configured and the daemon is reachable. Otherwise tests run in a cooperative process jail:
a temporary directory, a sanitized environment, a Python-level network block and a hard timeout.
That process jail is not OS-level confinement, so only the pinned trusted fixtures are executable;
general-purpose repair execution is blocked in this milestone.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROCESS_NOTICE = ('Process-jail mode: no OS-level network or filesystem confinement. Only pinned '
                  'trusted M3A fixtures are executable; general-purpose repair execution is blocked.')
GUARD = '''"""Best-effort network block for the repair process jail; not OS-level isolation.

socket.socket stays a class so modules such as ssl can subclass it, but no connection can be opened.
"""
import socket as _socket


def _blocked(*args, **kwargs):
    raise PermissionError('network access is disabled in the repair sandbox')


class _BlockedSocket(_socket.socket):
    def connect(self, *args, **kwargs):
        _blocked()

    def connect_ex(self, *args, **kwargs):
        _blocked()

    def sendto(self, *args, **kwargs):
        _blocked()


_socket.socket = _BlockedSocket
_socket.create_connection = _blocked
_socket.getaddrinfo = _blocked
'''


@dataclass
class Isolation:
    mode: str
    available: bool
    detail: str


@dataclass
class ExecutionResult:
    returncode: int | None
    output: str
    timed_out: bool
    environment_error: bool
    isolation: str

    def public(self) -> dict:
        return {'returncode': self.returncode, 'timed_out': self.timed_out,
                'environment_error': self.environment_error, 'isolation': self.isolation,
                'output': self.output}


@lru_cache(maxsize=1)
def detect_isolation() -> Isolation:
    requested = os.environ.get('BLACKBOX_REPAIR_ISOLATION', 'auto').lower()
    docker = shutil.which('docker')
    reachable = False
    if docker:
        try:
            check = subprocess.run([docker, 'info', '--format', '{{.ServerVersion}}'],
                                   capture_output=True, timeout=5, check=False)
            reachable = check.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            reachable = False
    if requested == 'process':
        return Isolation('process', True, PROCESS_NOTICE)
    if requested == 'docker':
        return Isolation('docker', reachable,
                         'container isolation requested' if reachable else 'Docker daemon is unavailable')
    if reachable:
        return Isolation('docker', True, 'Docker container isolation is available')
    return Isolation('process', True, PROCESS_NOTICE)


def _timeout() -> int:
    try:
        value = int(os.environ.get('BLACKBOX_REPAIR_TEST_TIMEOUT', '60'))
    except ValueError:
        return 60
    return min(300, max(5, value))


def _trim(output: str) -> str:
    if len(output) <= 16000:
        return output
    return output[:12000] + '\n... [output truncated] ...\n' + output[-4000:]


def _environment(workspace: Path, guard: Path) -> dict:
    allow = ('PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'NUMBER_OF_PROCESSORS',
             'PROCESSOR_ARCHITECTURE', 'LANG', 'LC_ALL', 'PYTHONIOENCODING')
    env = {key: os.environ[key] for key in allow if key in os.environ}
    env.update({'HOME': str(workspace), 'USERPROFILE': str(workspace), 'TEMP': str(workspace),
                'TMP': str(workspace), 'PYTHONPATH': os.pathsep.join([str(guard), str(workspace)]),
                'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_ADDOPTS': '', 'GIT_TERMINAL_PROMPT': '0',
                'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
    return env


def _docker_command(workspace: Path, node: str, image: str) -> list[str]:
    return ['docker', 'run', '--rm', '--network', 'none', '--memory', '256m', '--cpus', '0.5',
            '--pids-limit', '64', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--read-only', '--tmpfs', '/tmp:rw,noexec,nosuid',
            '-v', f'{workspace}:/workspace:rw', '-w', '/workspace',
            '-e', 'HOME=/tmp', '-e', 'PYTHONPATH=/workspace/.sandbox-guard:/workspace',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1', image,
            'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', node]


def run_tests(workspace: Path, node: str, isolation: Isolation | None = None) -> ExecutionResult:
    isolation = isolation or detect_isolation()
    workspace = Path(workspace)
    if not isolation.available:
        return ExecutionResult(None, '', False, True, f'{isolation.mode}: unavailable')
    if isolation.mode == 'docker':
        image = os.environ.get('BLACKBOX_REPAIR_DOCKER_IMAGE', '').strip()
        if not image:
            return ExecutionResult(None, '', False, True, 'docker: BLACKBOX_REPAIR_DOCKER_IMAGE is not configured')
        guard = workspace / '.sandbox-guard'
        guard.mkdir(parents=True, exist_ok=True)
        (guard / 'sitecustomize.py').write_text(GUARD, encoding='utf8')
        command = _docker_command(workspace, node, image)
        env = None
        cleanup = None
    else:
        cleanup = Path(tempfile.mkdtemp(prefix='blackbox-repair-guard-'))
        (cleanup / 'sitecustomize.py').write_text(GUARD, encoding='utf8')
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', node]
        env = _environment(workspace, cleanup)
    try:
        completed = subprocess.run(command, cwd=str(workspace), env=env, capture_output=True, text=True,
                                   encoding='utf8', errors='replace', timeout=_timeout(),
                                   stdin=subprocess.DEVNULL, shell=False)
        code = completed.returncode
        output = _trim((completed.stdout or '') + (completed.stderr or ''))
        return ExecutionResult(code, output, False, code in (2, 3, 4, 5), isolation.mode)
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or '') + (exc.stderr or '')
        if isinstance(partial, bytes):
            partial = partial.decode('utf-8', errors='replace')
        return ExecutionResult(None, _trim(partial), True, True, isolation.mode)
    except OSError:
        return ExecutionResult(None, '', False, True, isolation.mode)
    finally:
        if cleanup is not None:
            shutil.rmtree(cleanup, ignore_errors=True)
