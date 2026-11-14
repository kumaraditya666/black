import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import blackbox.cloud as cloud
from blackbox.cloud import create_cloud_app


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'repo'
    path.mkdir()
    subprocess.run(['git', 'init', '-q', str(path)], check=True)
    (path / 'app.py').write_text('def fail():\n    raise RuntimeError("cloud failure")\n', encoding='utf8')
    subprocess.run(['git', '-C', str(path), 'add', 'app.py'], check=True)
    subprocess.run(['git', '-C', str(path), '-c', 'user.name=Test',
                    '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    return path


@pytest.fixture
def client(tmp_path):
    return TestClient(create_cloud_app(tmp_path / 'cloud.db'))


def _signup(client, email='one@example.com', password='correct-horse'):
    response = client.post('/api/auth/signup', json={'email': email, 'password': password})
    assert response.status_code == 201, response.text
    return response


def _project(client, repo):
    response = client.post('/api/projects', json={'name': 'API', 'repo_path': str(repo)})
    assert response.status_code == 201, response.text
    return response.json()


def _event(repo):
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    return {
        'event_id': str(uuid.uuid4()),
        'occurred_at': datetime.now(timezone.utc).isoformat(),
        'commit': commit,
        'exception_type': 'RuntimeError',
        'message': 'cloud failure',
        'traceback': 'Traceback (most recent call last): ...',
        'frames': [{'path': 'app.py', 'line': 2, 'function': 'fail'}],
    }


def test_dashboard_and_auth_flow(client):
    assert client.get('/').status_code == 200
    assert client.get('/assets/app.js').status_code == 200
    assert client.get('/api/me').json() == {'user': None}

    _signup(client)
    me = client.get('/api/me').json()
    assert me['user']['email'] == 'one@example.com'

    client.post('/api/auth/logout')
    assert client.get('/api/me').json() == {'user': None}
    assert client.get('/api/projects').status_code == 401


def test_project_key_ingestion_and_issue_detail(client, repo):
    _signup(client)
    project = _project(client, repo)
    assert project['key'].startswith('bbx_')
    assert project['key_prefix'] == project['key'][:12]

    event = _event(repo)
    response = client.post('/api/ingest', json=event, headers={'X-Blackbox-Project-Key': project['key']})
    assert response.status_code == 201, response.text
    assert response.json()['duplicate'] is False

    duplicate = client.post('/api/ingest', json=event, headers={'X-Blackbox-Project-Key': project['key']})
    assert duplicate.json()['duplicate'] is True

    issues = client.get(f"/api/projects/{project['id']}/issues").json()
    assert len(issues) == 1
    assert issues[0]['event_count'] == 1
    detail = client.get(f"/api/issues/{issues[0]['id']}").json()
    assert detail['events'][0]['source_evidence'][0]['status'] == 'resolved'
    assert detail['events'][0]['source_evidence'][0]['source_line'] == '    raise RuntimeError("cloud failure")'


def test_another_account_cannot_read_the_project(client, tmp_path, repo):
    _signup(client, 'one@example.com')
    project = _project(client, repo)
    event = _event(repo)
    client.post('/api/ingest', json=event, headers={'X-Blackbox-Project-Key': project['key']})
    issue_id = client.get(f"/api/projects/{project['id']}/issues").json()[0]['id']

    other = TestClient(create_cloud_app(tmp_path / 'cloud.db'))
    _signup(other, 'two@example.com')
    assert other.get(f"/api/projects/{project['id']}/issues").status_code == 404
    assert other.get(f'/api/issues/{issue_id}').status_code == 404


def test_invalid_key_and_cross_origin_are_rejected(client, repo):
    _signup(client)
    project = _project(client, repo)
    event = _event(repo)
    assert client.post('/api/ingest', json=event, headers={'X-Blackbox-Project-Key': 'bad'}).status_code == 401
    response = client.post('/api/projects', json={'name': 'x'}, headers={'Origin': 'https://evil.example'})
    assert response.status_code == 403


def test_explain_uses_provider_and_persists_result(client, repo, monkeypatch):
    _signup(client)
    project = _project(client, repo)
    event = _event(repo)
    client.post('/api/ingest', json=event, headers={'X-Blackbox-Project-Key': project['key']})
    issue_id = client.get(f"/api/projects/{project['id']}/issues").json()[0]['id']

    class FakeProvider:
        def structured(self, *args, **kwargs):
            return type('Result', (), {'text': json.dumps({
                'summary': 'The handler raises on purpose.',
                'likely_cause': 'The fail function raises RuntimeError.',
                'fix': 'Handle the failure or stop raising.',
                'confidence': 'HIGH',
                'evidence': ['frame:0'],
            })})()

    monkeypatch.setattr(cloud, 'configured_provider', lambda: FakeProvider())
    response = client.post(f'/api/issues/{issue_id}/explain')
    assert response.status_code == 200, response.text
    assert response.json()['ai']['confidence'] == 'HIGH'
    detail = client.get(f'/api/issues/{issue_id}').json()
    assert detail['ai']['summary'] == 'The handler raises on purpose.'
