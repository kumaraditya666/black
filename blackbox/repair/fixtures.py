"""Trusted fixture registry and exact-revision materialization.

Fixtures are read from Git objects, never the working tree, so a repair attempt always tests the
recorded revision. Content hashes pinned in the registry make an unexpected file change a hard error.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / 'fixtures' / 'repair' / 'registry.json'


def load_registry(path: str | Path | None = None) -> list[dict]:
    return json.loads(Path(path or REGISTRY_PATH).read_text(encoding='utf8'))['fixtures']


def get_fixture(name: str, path: str | Path | None = None) -> dict:
    for fixture in load_registry(path):
        if fixture['name'] == name:
            return fixture
    raise KeyError(f'unknown repair fixture: {name}')


def fixture_path(fixture: dict) -> str:
    return 'fixtures/repair/' + fixture['name']


def _git(repo: Path, *args: str):
    env = os.environ.copy()
    env.update({'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                'GIT_NO_REPLACE_OBJECTS': '1'})
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=15,
                          env=env, check=False)


def revision_available(repo: Path, commit: str) -> bool:
    result = _git(Path(repo), 'cat-file', '-t', commit)
    return result.returncode == 0 and result.stdout.strip() == b'commit'


def blob_at(repo: Path, commit: str, relative: str) -> bytes | None:
    result = _git(Path(repo), 'show', f'{commit}:{fixture_path({"name": ""})}/{relative}'.replace('//', '/'))
    return result.stdout if result.returncode == 0 else None


def trusted(repo: Path, fixture: dict) -> tuple[bool, str]:
    if not fixture.get('approved_for_m3a'):
        return False, 'fixture is not approved for Milestone 3A'
    if Path(repo).resolve() != PROJECT_ROOT.resolve():
        return False, 'repository is not this project; arbitrary repositories are not executable in M3A'
    return True, 'trusted local fixture repository approved for Milestone 3A'


def content_pinned(repo: Path, commit: str, fixture: dict) -> tuple[bool, str]:
    """Every fixture file must exist at the revision with the registry's exact bytes."""
    if not revision_available(repo, commit):
        return False, 'recorded revision is not available'
    base = fixture_path(fixture)
    for relative, expected in fixture['files'].items():
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in ('', '..') for part in path.parts):
            return False, f'registry path is unsafe: {relative}'
        result = _git(Path(repo), 'show', f'{commit}:{base}/{relative}')
        if result.returncode:
            return False, f'{relative} is missing at the recorded revision'
        if hashlib.sha256(result.stdout).hexdigest() != expected:
            return False, f'{relative} does not match the pinned fixture content'
    return True, 'all fixture files match their pinned content hashes'


def materialize(repo: Path, commit: str, fixture: dict, destination: Path) -> dict[str, str]:
    """Write the pinned fixture files into a disposable directory and return path -> text."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    written = {}
    base = fixture_path(fixture)
    for relative, expected in fixture['files'].items():
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in ('', '..') for part in path.parts):
            raise ValueError('fixture registry contains an unsafe path')
        result = _git(Path(repo), 'show', f'{commit}:{base}/{relative}')
        if result.returncode:
            raise FileNotFoundError(f'{relative} is not present at {commit}')
        if hashlib.sha256(result.stdout).hexdigest() != expected:
            raise ValueError(f'{relative} at {commit} does not match the pinned fixture hash')
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.stdout)
        written[relative] = result.stdout.decode('utf8')
    return written
