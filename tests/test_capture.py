import importlib.util
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import blackbox.capture as capture
from blackbox.capture import build_event, install_blackbox


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'repo'
    path.mkdir()
    subprocess.run(['git', 'init', '-q', str(path)], check=True)
    (path / 'app.py').write_text(
        'def fail():\n    raise RuntimeError("real failure")\n',
        encoding='utf8',
    )
    (path / 'route.py').write_text(
        'def route_boom():\n    raise RuntimeError("route failed")\n',
        encoding='utf8',
    )
    subprocess.run(['git', '-C', str(path), 'add', 'app.py', 'route.py'], check=True)
    subprocess.run(
        ['git', '-C', str(path), '-c', 'user.name=Test',
         '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'],
        check=True,
    )
    return path


def _raise_from_repo(repo):
    namespace = {}
    source = (repo / 'app.py').read_text(encoding='utf8')
    exec(compile(source, str(repo / 'app.py'), 'exec'), namespace)
    with pytest.raises(RuntimeError) as caught:
        namespace['fail']()
    return caught.value


def test_build_event_maps_only_repository_frames(repo):
    event = build_event(_raise_from_repo(repo), repo)

    assert event['exception_type'] == 'RuntimeError'
    assert event['message'] == 'real failure'
    assert event['frames'] == [{'path': 'app.py', 'line': 2, 'function': 'fail'}]
    assert event['commit'] == subprocess.check_output(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True
    ).strip()


def test_build_event_rejects_an_exception_without_repository_frames(repo):
    with pytest.raises(ValueError, match='No traceback frame'):
        build_event(_raise_outside(repo), repo)


def _raise_outside(repo):
    try:
        raise RuntimeError('outside')
    except RuntimeError as exc:
        return exc


def test_fastapi_middleware_sends_the_event_and_preserves_the_error(repo, monkeypatch):
    sent = []

    def fake_send(payload, api_url=None, timeout=0):
        sent.append((payload, api_url, timeout))

    monkeypatch.setattr(capture, 'send_event', fake_send)
    app = FastAPI()
    install_blackbox(app, repo=repo, api_url='http://127.0.0.1:8000/events')
    spec = importlib.util.spec_from_file_location('capture_route', repo / 'route.py')
    route = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(route)
    app.add_api_route('/boom', route.route_boom)

    response = TestClient(app, raise_server_exceptions=False).get('/boom')

    assert response.status_code == 500
    assert len(sent) == 1
    payload, endpoint, _ = sent[0]
    assert endpoint == 'http://127.0.0.1:8000/events'
    assert payload['message'] == 'route failed'
    assert any(frame['path'] == 'route.py' for frame in payload['frames'])


def test_capture_rejects_a_non_loopback_endpoint(repo):
    with pytest.raises(RuntimeError, match='loopback'):
        install_blackbox(FastAPI(), repo=repo, api_url='http://example.com/events')
