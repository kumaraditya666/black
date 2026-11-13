"""Disposable test execution with explicit isolation limits.

Docker (no network, read-only root, dropped capabilities, memory/CPU/PID limits) is used when an
image is configured and the daemon is reachable. Otherwise tests run in a cooperative process jail:
a temporary directory, a sanitized environment, a Python-level network block and a hard timeout.
That process jail is not OS-level confinement, so only the pinned trusted fixtures are executable;
general-purpose repair execution is blocked in this milestone.
"""
import os
import json
import re
import site
import uuid
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
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
    security_blocked: bool = False

    def public(self) -> dict:
        return {'returncode': self.returncode, 'timed_out': self.timed_out,
                'environment_error': self.environment_error, 'isolation': self.isolation,
                'output': self.output, 'security_blocked': self.security_blocked}


def detect_isolation() -> Isolation:
    requested = os.environ.get('BLACKBOX_REPAIR_ISOLATION', 'auto').lower()
    if requested not in ('auto', 'docker', 'process'):
        return Isolation('docker', False, 'invalid isolation configuration')
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
    return Isolation('docker', False, 'Docker unavailable; no automatic process-jail fallback')


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


def _site_packages() -> tuple[str, ...]:
    """Keep the parent interpreter's site packages available in the child."""
    candidates = [*site.getsitepackages(), site.getusersitepackages()]
    return tuple(str(Path(item)) for item in candidates if item and Path(item).is_dir())


def _environment(workspace: Path, guard: Path) -> dict:
    allow = ('PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'NUMBER_OF_PROCESSORS',
             'PROCESSOR_ARCHITECTURE', 'LANG', 'LC_ALL', 'PYTHONIOENCODING')
    env = {key: os.environ[key] for key in allow if key in os.environ}
    env.update({'HOME': str(workspace), 'USERPROFILE': str(workspace), 'TEMP': str(workspace),
                'TMP': str(workspace),
                'PYTHONPATH': os.pathsep.join([str(guard), str(workspace), *_site_packages()]),
                'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_ADDOPTS': '', 'GIT_TERMINAL_PROMPT': '0',
                'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
    return env


# The journal serializes Docker executions and survives process interruption. A pending journal
# blocks new executions until an operator explicitly recovers the exact owned container.
JOURNAL = Path(__file__).resolve().parents[2] / 'data' / 'repair-container-pending'
OWNER_LABEL = 'ai.blackbox.repair.identity'
NAME_PREFIX = 'blackbox-repair-'
USER = '65534:65534'


def _docker(*args, timeout=15):
    return subprocess.run(['docker', *args], capture_output=True, text=True, encoding='utf8',
                          errors='replace', timeout=timeout, stdin=subprocess.DEVNULL, check=False)


def _journal_event(identity, result):
    path = JOURNAL.parent / 'repair-container-audit.jsonl'
    with path.open('a', encoding='utf8') as stream:
        stream.write(json.dumps({'identity': identity, 'result': result}) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def _inspect_owned(name, identity):
    """Return inspect data, None if absent, or raise on uncertain/foreign ownership."""
    listed = _docker('ps', '-a', '--no-trunc', '--filter', 'name=^/' + name + '$', '--format', '{{.ID}}')
    if listed.returncode:
        raise RuntimeError('Docker container listing failed')
    ids = listed.stdout.split()
    if not ids:
        return None
    if len(ids) != 1:
        raise RuntimeError('ambiguous container identity')
    inspected = _docker('inspect', ids[0])
    if inspected.returncode:
        raise RuntimeError('Docker inspection failed')
    item = json.loads(inspected.stdout)[0]
    if item['Name'] != '/' + name or item['Config']['Labels'].get(OWNER_LABEL) != identity:
        raise RuntimeError('container ownership mismatch')
    return item


def recover_container():
    """Explicit operator recovery of the single journaled container; never sweep by label."""
    record = json.loads((JOURNAL / 'identity.json').read_text(encoding='utf8'))
    identity = record['identity']
    daemon = _docker('info', '--format', '{{.ID}}')
    if daemon.returncode or not daemon.stdout.strip() or daemon.stdout.strip() != record.get('daemon_id'):
        raise RuntimeError('original Docker daemon is unavailable or has changed')
    if not re.fullmatch(r'[0-9a-f]{32}', identity) or record['name'] != NAME_PREFIX + identity:
        raise RuntimeError('invalid recovery identity')
    item = _inspect_owned(record['name'], identity)
    if item is not None:
        removed = _docker('rm', '-f', item['Id'])
        if removed.returncode:
            raise RuntimeError('owned container removal failed')
    if _inspect_owned(record['name'], identity) is not None:
        raise RuntimeError('container removal could not be confirmed')
    _journal_event(identity, 'removed and absence confirmed')
    (JOURNAL / 'identity.json').unlink()
    JOURNAL.rmdir()


def _docker_command(workspace: Path, node: str, image: str, name: str, identity: str) -> list[str]:
    # Override any image entrypoint and fail before pytest if the effective user is wrong.
    bootstrap = ("import os,sys; "
                 "assert os.geteuid()==65534 and os.getegid()==65534, 'non-root identity mismatch'; "
                 "s=dict(line.split(':',1) for line in open('/proc/self/status') if ':' in line); "
                 "assert int(s['CapEff'].strip(),16)==0 and s['NoNewPrivs'].strip()=='1' and s['Seccomp'].strip()=='2', 'security state mismatch'; "
                 "os.execvp('python', ['python','-m','pytest','-q','-p','no:cacheprovider',sys.argv[1]])")
    return ['docker', 'create', '--name', name, '--label', OWNER_LABEL + '=' + identity,
            '--pull', 'never', '--user', USER, '--network', 'none', '--memory', '256m',
            '--memory-swap', '256m', '--cpus', '0.5', '--pids-limit', '64', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--read-only',
            '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m', '--mount',
            f'type=bind,source={workspace},target=/workspace', '-w', '/workspace',
            '-e', 'HOME=/tmp', '-e', 'PYTHONPATH=/workspace/.sandbox-guard:/workspace',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1',
            '--entrypoint', 'python', image, '-c', bootstrap, node]


def _validate_container(item, image_id, workspace):
    c, h = item['Config'], item['HostConfig']
    mounts = item.get('Mounts') or []
    opts = h.get('SecurityOpt') or []
    if not (item['Image'] == image_id and c['User'] == USER and h['NetworkMode'] == 'none'
            and h['ReadonlyRootfs'] and h['Memory'] == 268435456 and h['MemorySwap'] == 268435456
            and h['NanoCpus'] == 500000000 and h['PidsLimit'] == 64
            and 'ALL' in (h.get('CapDrop') or []) and any(x.startswith('no-new-privileges') for x in opts)
            and (h.get('Tmpfs') or {}).get('/tmp') == 'rw,noexec,nosuid,size=32m'
            and not h['Privileged'] and not any('seccomp=unconfined' in x for x in opts) and len(mounts) == 1 and mounts[0]['Destination'] == '/workspace'
            and mounts[0]['Type'] == 'bind' and mounts[0]['RW']):
        raise RuntimeError('container security settings failed inspection')


def _run_docker(workspace, node):
    image = os.environ.get('BLACKBOX_REPAIR_DOCKER_IMAGE_ID', '').strip()
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        return ExecutionResult(None, 'Explicit approved local image ID required', False, True, 'docker')
    try:
        daemon = _docker('info', '--format', '{{.ID}}')
        if daemon.returncode or not daemon.stdout.strip():
            raise RuntimeError('Docker daemon unavailable')
        daemon_id = daemon.stdout.strip()
    except (OSError, subprocess.TimeoutExpired, RuntimeError):
        return ExecutionResult(None, 'Docker daemon unavailable', False, True, 'docker', JOURNAL.exists())
    identity = uuid.uuid4().hex
    name = NAME_PREFIX + identity
    try:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        JOURNAL.mkdir()  # Exclusive: pending or active work blocks all new executions.
    except FileExistsError:
        return ExecutionResult(None, 'Pending container requires explicit recovery', False, True, 'docker', True)
    except OSError:
        return ExecutionResult(None, 'Cannot create container journal', False, True, 'docker', True)
    result = ExecutionResult(None, '', False, True, 'docker')
    interrupted = None
    creation_uncertain = False
    try:
        with (JOURNAL / 'identity.json').open('x', encoding='utf8') as stream:
            json.dump({'identity': identity, 'name': name, 'daemon_id': daemon_id}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        _journal_event(identity, 'reserved')
        inspect_image = _docker('image', 'inspect', image)
        if inspect_image.returncode or json.loads(inspect_image.stdout)[0]['Id'] != image:
            raise RuntimeError('approved local image unavailable')
        guard = workspace / '.sandbox-guard'
        guard.mkdir(parents=True, exist_ok=True)
        (guard / 'sitecustomize.py').write_text(GUARD, encoding='utf8')
        command = _docker_command(workspace, node, image, name, identity)
        try:
            created = subprocess.run(command, capture_output=True, text=True, encoding='utf8', errors='replace',
                                     timeout=30, stdin=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired:
            creation_uncertain = True
            raise RuntimeError('container creation timed out; daemon state is uncertain')
        if created.returncode:
            raise RuntimeError('container creation failed: ' + created.stderr[:500])
        item = _inspect_owned(name, identity)
        if not item:
            raise RuntimeError('created container missing')
        _validate_container(item, image, workspace)
        _journal_event(identity, 'created and settings validated')
        try:
            completed = _docker('start', '-a', item['Id'], timeout=_timeout())
            state = _inspect_owned(name, identity)
            if not state or state['State']['Status'] != 'exited' or state['State']['ExitCode'] != completed.returncode:
                raise RuntimeError('container execution state could not be verified')
            result = ExecutionResult(completed.returncode, _trim(completed.stdout + completed.stderr),
                                     False, completed.returncode not in (0, 1), 'docker')
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or b''
            if isinstance(output, bytes):
                output = output.decode('utf8', errors='replace')
            result = ExecutionResult(None, _trim(output), True, True, 'docker')
    except KeyboardInterrupt as exc:
        interrupted = exc
    except (Exception, SystemExit) as exc:
        result = ExecutionResult(None, str(exc)[:1000], False, True, 'docker')
    finally:
        try:
            if creation_uncertain:
                raise RuntimeError('creation request may still be in flight; manual recovery required')
            recover_container()
        except (Exception, KeyboardInterrupt) as exc:
            result = ExecutionResult(None, 'Container cleanup unconfirmed: ' + str(exc)[:500],
                                     result.timed_out, True, 'docker', True)
            interrupted = None
    if interrupted is not None:
        raise interrupted
    return result


def run_tests(workspace: Path, node: str, isolation: Isolation | None = None) -> ExecutionResult:
    isolation = isolation or detect_isolation()
    workspace = Path(workspace).resolve()
    if not isolation.available:
        blocked = isolation.mode == 'docker' and JOURNAL.exists()
        return ExecutionResult(None, '', False, True, f'{isolation.mode}: unavailable', blocked)
    if isolation.mode == 'docker':
        return _run_docker(workspace, node)
    cleanup = Path(tempfile.mkdtemp(prefix='blackbox-repair-guard-'))
    (cleanup / 'sitecustomize.py').write_text(GUARD, encoding='utf8')
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', node]
    try:
        completed = subprocess.run(command, cwd=str(workspace), env=_environment(workspace, cleanup),
                                   capture_output=True, text=True, encoding='utf8', errors='replace',
                                   timeout=_timeout(), stdin=subprocess.DEVNULL, shell=False)
        return ExecutionResult(completed.returncode, _trim(completed.stdout + completed.stderr), False,
                               completed.returncode in (2, 3, 4, 5), isolation.mode)
    except subprocess.TimeoutExpired:
        return ExecutionResult(None, '', True, True, isolation.mode)
    except OSError:
        return ExecutionResult(None, '', False, True, isolation.mode)
    finally:
        shutil.rmtree(cleanup, ignore_errors=True)


if __name__ == '__main__':
    if sys.argv[1:] != ['--recover']:
        raise SystemExit('Usage: python -m blackbox.repair.execution --recover')
    recover_container()
    print('Journaled container removed or absent; cleanup confirmed.')
