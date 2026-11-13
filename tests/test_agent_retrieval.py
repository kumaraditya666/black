import copy
import hashlib
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from blackbox.agent_retrieval import Dispatcher, Request, RetrievalError, investigate_with_retrieval
from blackbox.schemas import Event, Frame
from blackbox.store import Store
from blackbox.repair import fixtures
import blackbox.agent_retrieval as agent
from blackbox.repair.fixtures import get_fixture

ROOT = Path(__file__).resolve().parents[1]
REV = 'ee674ffb46dc83c5d78585ac23cd86217bcc2dec'
REGISTRY = ROOT / 'fixtures/repair/m3f-registry.json'


@pytest.fixture
def dispatcher():
    return Dispatcher(ROOT, REV, get_fixture('m3f_feed_multi', REGISTRY))


def test_read_and_provenance(dispatcher):
    path = 'fixtures/repair/m3f_feed_multi/settings.py'
    result = dispatcher.dispatch({'action': 'read_source', 'path': path, 'start': 1, 'end': 2, 'reason': 'inspect recorded failure'})
    assert result['commit'] == REV and result['path'] == path
    assert result['provenance_status'] == 'VERIFIED_SOURCE' and result['id'].startswith('agent:')
    assert result['source'] and dispatcher.trace[0]['result'] == result


@pytest.mark.parametrize('payload', [
    {'action': 'execute', 'reason': 'run'},
    {'action': 'find_symbol', 'symbol': 'item_limit', 'reason': 'x', 'command': 'whoami'},
    {'action': 'read_source', 'path': '../secret', 'start': 1, 'end': 1, 'reason': 'x'},
    {'action': 'read_source', 'path': 'fixtures/repair/m3f_feed_multi/settings.py', 'start': 1, 'end': 21, 'reason': 'x'},
    {'action': 'read_source', 'path': 'fixtures/repair/m3f_feed_multi/tests/test_reproduction.py', 'start': 1, 'end': 1, 'reason': 'x'},
])
def test_reject_unsafe_request(dispatcher, payload):
    with pytest.raises(RetrievalError):
        dispatcher.dispatch(payload)
    assert dispatcher.trace[0]['status'] == 'REJECTED'


def test_duplicate_and_limit(dispatcher):
    request = {'action': 'find_symbol', 'symbol': 'item_limit', 'reason': 'locate'}
    assert dispatcher.dispatch(request)['status'] == 'FOUND'
    with pytest.raises(RetrievalError, match='DUPLICATE'):
        dispatcher.dispatch(request)
    with pytest.raises(RetrievalError, match='REQUEST_LIMIT'):
        dispatcher.dispatch(request)


def test_unknown_symbol_and_revision(dispatcher):
    assert dispatcher.dispatch({'action': 'find_symbol', 'symbol': 'unknown_symbol', 'reason': 'locate'})['status'] == 'NOT_FOUND'
    with pytest.raises(RetrievalError, match='UNTRUSTED_OR_UNPINNED'):
        Dispatcher(ROOT, '0' * 40, get_fixture('m3f_feed_multi', REGISTRY))


def test_static_caller(dispatcher):
    result = dispatcher.dispatch({'action': 'find_callers', 'symbol': 'item_limit',
                                  'path': 'fixtures/repair/m3f_feed_multi/settings.py', 'start': 2, 'reason': 'find caller'})
    assert 'execution' in result['notice']
    assert result['status'] in ('FOUND', 'NOT_FOUND_OR_INCOMPLETE')


def test_static_callee(dispatcher):
    result = dispatcher.dispatch({'action': 'find_callees', 'symbol': 'render',
                                  'path': 'fixtures/repair/m3f_feed_multi/app.py', 'start': 3, 'reason': 'find callee'})
    assert 'execution' in result['notice']


def test_git_symlink_is_rejected(dispatcher, monkeypatch):
    path = 'fixtures/repair/m3f_feed_multi/settings.py'
    original = agent._git
    def git(repo, *args):
        if args[0] == 'ls-tree':
            return subprocess.CompletedProcess(args, 0, b'120000 blob 1234\t' + path.encode() + b'\0', b'')
        return original(repo, *args)
    monkeypatch.setattr(agent, '_git', git)
    with pytest.raises(RetrievalError, match='NOT_REGULAR_GIT_BLOB'):
        dispatcher.dispatch({'action': 'read_source', 'path': path, 'start': 1, 'end': 1, 'reason': 'inspect'})


def test_real_git_symlink_object_is_rejected(tmp_path):
    env = os.environ.copy()
    env['GIT_INDEX_FILE'] = str(tmp_path / 'index')
    env.update({'GIT_AUTHOR_NAME': 'BLACKBOX test', 'GIT_AUTHOR_EMAIL': 'test@localhost',
                'GIT_COMMITTER_NAME': 'BLACKBOX test', 'GIT_COMMITTER_EMAIL': 'test@localhost'})
    def git(*args, input=None):
        return subprocess.check_output(['git', '-C', str(ROOT), *args], env=env, input=input).decode().strip()
    git('read-tree', 'HEAD')
    body = b'../../outside.py'
    blob = git('hash-object', '-w', '--stdin', input=body)
    path = 'fixtures/repair/m4b1_symlink_test/link.py'
    git('update-index', '--add', '--cacheinfo', f'120000,{blob},{path}')
    tree = git('write-tree')
    commit = git('commit-tree', tree, '-p', 'HEAD', input=b'test symlink object\n')
    fixture = {'name': 'm4b1_symlink_test', 'approved_for_m3a': True,
               'files': {'link.py': hashlib.sha256(body).hexdigest()}}
    dispatcher = Dispatcher(ROOT, commit, fixture)
    with pytest.raises(RetrievalError, match='NOT_REGULAR_GIT_BLOB'):
        dispatcher.dispatch({'action': 'read_source', 'path': path, 'start': 1, 'end': 1, 'reason': 'inspect'})


def test_malicious_comment_remains_data_and_cannot_grant_commands():
    revision = '76564779c56068107aeccda8205147c6bbbea86e'
    registry = ROOT / 'fixtures/repair/m4b1-registry.json'
    dispatcher = Dispatcher(ROOT, revision, get_fixture('m4b1_injected', registry))
    path = 'fixtures/repair/m4b1_injected/helper.py'
    result = dispatcher.dispatch({'action': 'read_source', 'path': path, 'start': 4, 'end': 6, 'reason': 'inspect source'})
    assert 'Ignore previous instructions' in result['source']
    assert 'Untrusted source' in result['notice']
    with pytest.raises(RetrievalError):
        dispatcher.dispatch({'action': 'execute', 'reason': 'follow source instructions'})


def test_fixture_scope_cannot_be_extended(dispatcher):
    request = {'action': 'read_source', 'path': 'blackbox/investigator.py', 'start': 1, 'end': 1, 'reason': 'read'}
    with pytest.raises(RetrievalError, match='PATH_NOT_AUTHORIZED'):
        dispatcher.dispatch(request)


def test_schema_does_not_grant_execution():
    assert 'execute' not in str(Request.model_json_schema())


def test_provider_timeout_is_failure_without_repair(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, 'REGISTRY_PATH', REGISTRY)
    fixture = get_fixture('m3f_feed_multi', REGISTRY)
    ev = fixture['event']
    store = Store(str(tmp_path / 'store.db'))
    incident, _ = store.ingest(Event(event_id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc),
        commit=REV, exception_type=ev['exception_type'], message=ev['message'], traceback='recorded',
        frames=[Frame(**ev['frame'])]))
    class TimeoutProvider:
        name, model = 'ollama', 'test'
        def structured(self, *args, **kwargs):
            raise httpx.ReadTimeout('private details')
    result = agent._investigate_with_retrieval(store, ROOT, incident, fixture['name'], TimeoutProvider())
    assert result['status'] == 'INVESTIGATION_FAILED'
    assert result['investigation'] is None and 'private details' not in str(result)
