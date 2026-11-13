import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from blackbox.repair import execution as ex
from blackbox.repair.fixtures import PROJECT_ROOT, get_fixture, materialize

IMAGE = os.environ.get('BLACKBOX_M3B_TEST_IMAGE', '')
pytestmark = pytest.mark.skipif(not IMAGE, reason='set BLACKBOX_M3B_TEST_IMAGE to an approved local image ID')

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('BLACKBOX_REPAIR_DOCKER_IMAGE_ID', IMAGE)
    # Isolated journal for this test; all executed source remains from the pinned fixture.
    monkeypatch.setattr(ex, 'JOURNAL', tmp_path / 'journal' / 'pending')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, text=True).strip()
    fixture = get_fixture('argument_validation')
    path = tmp_path / 'fixture'
    materialize(PROJECT_ROOT, revision, fixture, path)
    return path, fixture


def assert_our_containers_gone():
    audit = ex.JOURNAL.parent / 'repair-container-audit.jsonl'
    identities = {json.loads(line)['identity'] for line in audit.read_text().splitlines()}
    out = subprocess.check_output(['docker','ps','-a','--filter','label='+ex.OWNER_LABEL,'--format','{{.Names}}'],text=True)
    assert not ({ex.NAME_PREFIX + identity for identity in identities} & set(out.splitlines()))


def test_success_and_failure_cleanup(workspace):
    path, fixture = workspace
    ok = ex.run_tests(path, 'tests/test_regression.py::test_numeric_string_port_is_parsed', ex.Isolation('docker',True,''))
    fail = ex.run_tests(path, fixture['reproduction']['test'], ex.Isolation('docker',True,''))
    assert (ok.returncode, fail.returncode) == (0, 1)
    assert not ok.security_blocked and not fail.security_blocked
    assert_our_containers_gone()


def test_actual_timeout_cleans_container(workspace, monkeypatch):
    path, fixture = workspace
    command = ex._docker_command
    def slow_fixture(*args):
        cmd = command(*args)
        cmd[-2] = ("import os,sys,time,pytest\n"
                   "assert os.geteuid()==65534 and os.getegid()==65534\n"
                   "class Slow:\n def pytest_runtest_call(self, item):\n  print('PINNED_TEST_STARTED', flush=True)\n  time.sleep(30)\n"
                   "sys.exit(pytest.main(['-s','-q','-p','no:cacheprovider',sys.argv[1]],plugins=[Slow()]))")
        return cmd
    monkeypatch.setattr(ex, '_docker_command', slow_fixture)
    monkeypatch.setattr(ex, '_timeout', lambda: 3)
    result = ex.run_tests(path, fixture['reproduction']['test'], ex.Isolation('docker', True, ''))
    assert result.timed_out and 'PINNED_TEST_STARTED' in result.output
    assert not result.security_blocked and not ex.JOURNAL.exists()
    assert_our_containers_gone()


def test_cancellation_cleans_container(workspace, monkeypatch):
    path, fixture = workspace
    real = ex._docker
    def interrupt(*args, **kwargs):
        if args[:2] == ('start', '-a'):
            # Start the real container, then interrupt the caller while cleanup is required.
            subprocess.run(['docker','start',args[2]],capture_output=True,check=True)
            raise KeyboardInterrupt()
        return real(*args, **kwargs)
    monkeypatch.setattr(ex, '_docker', interrupt)
    with pytest.raises(KeyboardInterrupt):
        ex.run_tests(path, fixture['reproduction']['test'], ex.Isolation('docker',True,''))
    assert not ex.JOURNAL.exists()
    assert_our_containers_gone()


def test_invalid_image_fails_closed(workspace, monkeypatch):
    monkeypatch.setenv('BLACKBOX_REPAIR_DOCKER_IMAGE_ID','sha256:'+'0'*64)
    r = ex.run_tests(workspace[0], workspace[1]['reproduction']['test'], ex.Isolation('docker',True,''))
    assert r.environment_error and not r.security_blocked and not ex.JOURNAL.exists()


def test_daemon_unavailable_fails_closed(workspace, monkeypatch):
    monkeypatch.setenv('DOCKER_HOST', 'npipe:////./pipe/blackbox-nonexistent-engine')
    monkeypatch.setenv('DOCKER_CONTEXT', '')
    r = ex.run_tests(workspace[0], workspace[1]['reproduction']['test'], ex.Isolation('docker',True,''))
    assert r.environment_error and not ex.JOURNAL.exists()


def test_cleanup_failure_blocks_and_recovers(workspace, monkeypatch):
    real = ex._docker
    def fail_remove(*args, **kwargs):
        if args[:2] == ('rm','-f'):
            return subprocess.CompletedProcess(args,1,'','simulated removal failure')
        return real(*args, **kwargs)
    monkeypatch.setattr(ex,'_docker',fail_remove)
    r=ex.run_tests(workspace[0],workspace[1]['reproduction']['test'],ex.Isolation('docker',True,''))
    assert r.security_blocked and ex.JOURNAL.exists()
    assert ex.run_tests(workspace[0],workspace[1]['reproduction']['test'],ex.Isolation('docker',True,'')).security_blocked
    monkeypatch.setattr(ex,'_docker',real)
    ex.recover_container()
    assert not ex.JOURNAL.exists()


def test_unowned_container_is_never_removed(workspace):
    identity='1'*32; name=ex.NAME_PREFIX+identity
    ex.JOURNAL.mkdir(parents=True)
    (ex.JOURNAL/'identity.json').write_text(json.dumps({'identity':identity,'name':name,'daemon_id': subprocess.check_output(['docker','info','--format','{{.ID}}'],text=True).strip()}))
    subprocess.run(['docker','create','--name',name,IMAGE,'python','-c','pass'],capture_output=True,check=True)
    try:
        with pytest.raises(RuntimeError, match='ownership mismatch'):
            ex.recover_container()
        assert subprocess.run(['docker','inspect',name],capture_output=True).returncode == 0
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,check=True)
        ex.recover_container()


def test_resource_settings_and_nonroot(workspace, monkeypatch):
    seen=[]; real=ex._validate_container
    def capture(item, image_id, path):
        real(item,image_id,path)
        seen.append(item)
    monkeypatch.setattr(ex,'_validate_container',capture)
    r=ex.run_tests(workspace[0], 'tests/test_regression.py::test_numeric_string_port_is_parsed', ex.Isolation('docker',True,''))
    assert r.returncode == 0 and seen[0]['Config']['User'] == '65534:65534'
    assert seen[0]['HostConfig']['Memory'] == 268435456 and seen[0]['HostConfig']['PidsLimit'] == 64
