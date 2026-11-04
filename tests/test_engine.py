import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from blackbox.app import create_app


@pytest.fixture
def setup(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    (repo / 'app.py').write_text('def fail():\n    return 1 / 0\n', encoding='utf8')
    subprocess.run(['git', '-C', str(repo), 'add', 'app.py'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    sha = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    db = tmp_path / 'events.db'
    client = TestClient(create_app(str(db), str(repo)))
    event = {'event_id': str(uuid.uuid4()), 'occurred_at': datetime.now(timezone.utc).isoformat(), 'commit': sha,
             'exception_type': 'ZeroDivisionError', 'message': 'password=hunter2',
             'traceback': 'token=hiddenvalue', 'frames': [{'path': 'app.py', 'line': 2, 'function': 'fail'}]}
    return client, event, db, repo


def test_exact_commit_and_redaction(setup):
    client, event, db, repo = setup
    (repo / 'app.py').write_text('modified working tree\n', encoding='utf8')
    result = client.post('/events', json=event)
    assert result.status_code == 201
    report = client.get(f"/incidents/{result.json()['incident_id']}/report").json()
    item = report['events'][0]
    assert item['source_evidence'][0]['source_line'] == '    return 1 / 0'
    assert item['source_evidence'][0]['commit'] == event['commit']
    assert 'hunter2' not in json.dumps(report) and 'hiddenvalue' not in json.dumps(report)
    assert b'hunter2' not in db.read_bytes() and b'hiddenvalue' not in db.read_bytes()


def test_idempotency_and_history(setup):
    client, event, _, _ = setup
    first = client.post('/events', json=event).json()
    assert client.post('/events', json=event).json()['created'] is False
    changed = {**event, 'message': 'different'}
    assert client.post('/events', json=changed).status_code == 409
    event['event_id'] = str(uuid.uuid4())
    other = client.post('/events', json=event).json()
    assert first['incident_id'] == other['incident_id']
    report = client.get(f"/incidents/{first['incident_id']}/report").json()
    assert report['event_count'] == 2


@pytest.mark.parametrize('field,value', [('commit', 'main'), ('occurred_at', '2026-01-01T00:00:00'), ('frames', []), ('event_id', 'invalid')])
def test_invalid_events(setup, field, value):
    client, event, _, _ = setup
    event[field] = value
    assert client.post('/events', json=event).status_code == 422


@pytest.mark.parametrize('path', ['../secret', '/absolute', 'C:/windows', '-bad', 'a\\b'])
def test_invalid_path(setup, path):
    client, event, _, _ = setup
    event['frames'][0]['path'] = path
    assert client.post('/events', json=event).status_code == 422


def test_unresolved_commit_file_and_line(setup):
    client, event, _, _ = setup
    event['commit'] = '0' * 40
    iid = client.post('/events', json=event).json()['incident_id']
    assert 'commit not found' in client.get(f'/incidents/{iid}/report').json()['events'][0]['source_evidence'][0]['reason']
    event['commit'] = subprocess.check_output(['git', '-C', str(setup[3]), 'rev-parse', 'HEAD'], text=True).strip()
    event['event_id'] = str(uuid.uuid4())
    event['frames'][0]['path'] = 'missing.py'
    iid = client.post('/events', json=event).json()['incident_id']
    assert 'file not found' in client.get(f'/incidents/{iid}/report').json()['events'][0]['source_evidence'][0]['reason']
    event['event_id'] = str(uuid.uuid4())
    event['frames'][0] = {'path': 'app.py', 'line': 100, 'function': 'fail'}
    iid = client.post('/events', json=event).json()['incident_id']
    assert 'line not present' in client.get(f'/incidents/{iid}/report').json()['events'][0]['source_evidence'][0]['reason']


def test_missing_incident(setup):
    assert setup[0].get('/incidents/999/report').status_code == 404


def test_distinct_stack_forms_distinct_incident(setup):
    client, event, _, _ = setup
    first = client.post('/events', json=event).json()['incident_id']
    event['event_id'] = str(uuid.uuid4())
    event['frames'][0]['line'] = 1
    second = client.post('/events', json=event).json()['incident_id']
    assert first != second


def test_source_lines_are_redacted(setup):
    client, event, _, repo = setup
    (repo / 'app.py').write_text('api_key=secretvalue\n', encoding='utf8')
    subprocess.run(['git', '-C', str(repo), 'add', 'app.py'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'secret fixture'], check=True)
    event['commit'] = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    event['frames'][0]['line'] = 1
    iid = client.post('/events', json=event).json()['incident_id']
    source = client.get(f'/incidents/{iid}/report').json()['events'][0]['source_evidence'][0]['source_line']
    assert source == 'api_key=[REDACTED]'


class MockProvider:
    name = 'ollama'
    model = 'mock-model'
    calls = 0
    assessment = 'insufficient_evidence'
    invalid = False

    def analyze(self, prompt):
        from blackbox.providers import ProviderResult
        self.calls += 1
        assert 'UNTRUSTED EVIDENCE JSON' in prompt
        snapshot = json.loads(prompt.split('UNTRUSTED EVIDENCE JSON:\n', 1)[1])
        event_ref = snapshot['evidence'][0]['id']
        data = {'outcome': 'LIKELY_CAUSE' if self.assessment == 'plausible' else 'INSUFFICIENT_EVIDENCE',
                'observed_failure': {'text': 'An event was recorded.', 'evidence_ids': [event_ref]},
                'observed_facts': [{'text': 'An event was received.', 'evidence_ids': ['fake-id' if self.invalid else 'occurrences']}],
                'hypotheses': ([{'explanation': 'Possible input issue', 'supporting_evidence': ['frame:0', event_ref], 'contradicting_evidence': []}] if self.assessment == 'plausible' else []),
                'alternatives': [], 'missing_evidence': ['Additional runtime context'], 'verification_steps': ['Inspect the input.']}
        return ProviderResult(json.dumps(data), {'input_tokens': None, 'output_tokens': None, 'estimated_cost': None})


def test_unconfigured_provider_and_external_consent(setup, monkeypatch):
    client, event, _, _ = setup
    iid = client.post('/events', json=event).json()['incident_id']
    monkeypatch.delenv('BLACKBOX_AI_PROVIDER', raising=False)
    assert client.post(f'/incidents/{iid}/investigations', json={}).status_code == 503
    provider = MockProvider()
    provider.name = 'gemini'
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: provider)
    assert client.post(f'/incidents/{iid}/investigations', json={}).status_code == 403
    preview = client.get(f'/incidents/{iid}/context').json()
    assert client.post(f'/incidents/{iid}/investigations', json={'consent_external': True, 'reviewed_evidence_hash': preview['evidence_hash']}).status_code == 200
    assert provider.calls == 1


def test_investigation_caching_and_new_evidence(setup, monkeypatch):
    client, event, _, _ = setup
    provider = MockProvider()
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: provider)
    iid = client.post('/events', json=event).json()['incident_id']
    first = client.post(f'/incidents/{iid}/investigations', json={}).json()
    assert first['investigation']['status'] == 'completed'
    assert client.get('/investigations/' + first['investigation']['id']).json()['findings']['outcome'] == 'INSUFFICIENT_EVIDENCE'
    assert client.post(f'/incidents/{iid}/investigations', json={}).json()['cached'] is True
    assert provider.calls == 1
    event['event_id'] = str(uuid.uuid4())
    client.post('/events', json=event)
    second = client.post(f'/incidents/{iid}/investigations', json={}).json()
    assert second['cached'] is False and provider.calls == 2
    assert second['investigation']['evidence']['evidence'][1]['count'] == 2
    assert len(client.get(f'/incidents/{iid}/investigations').json()) == 2


def test_fabricated_reference_persists_failure(setup, monkeypatch):
    client, event, _, _ = setup
    provider = MockProvider()
    provider.invalid = True
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: provider)
    iid = client.post('/events', json=event).json()['incident_id']
    result = client.post(f'/incidents/{iid}/investigations', json={}).json()['investigation']
    assert result['status'] == 'failed' and result['findings'] is None
    assert client.get('/investigations/' + result['id']).json()['status'] == 'failed'


def test_fake_file_reference_is_rejected(setup, monkeypatch):
    from blackbox.providers import ProviderResult
    client, event, _, _ = setup
    provider = MockProvider()
    def generate(prompt):
        event_ref = json.loads(prompt.split('UNTRUSTED EVIDENCE JSON:\n', 1)[1])['evidence'][0]['id']
        return ProviderResult(json.dumps({'outcome': 'INSUFFICIENT_EVIDENCE', 'observed_failure': {'text': 'An event occurred', 'evidence_ids': [event_ref]}, 'observed_facts': [
            {'text': 'Look in invented.py', 'evidence_ids': ['frame:0']}], 'hypotheses': [], 'alternatives': [],
            'missing_evidence': ['unknown'], 'verification_steps': ['inspect']}), {})
    provider.analyze = generate
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: provider)
    iid = client.post('/events', json=event).json()['incident_id']
    assert client.post(f'/incidents/{iid}/investigations', json={}).json()['investigation']['status'] == 'failed'


def test_ollama_local_only(monkeypatch):
    from blackbox.providers import Provider, ProviderError
    monkeypatch.setenv('BLACKBOX_OLLAMA_URL', 'http://example.com:11434')
    with pytest.raises(ProviderError, match='local HTTP'):
        Provider('ollama', 'configured-model').analyze('data')


def test_ollama_adapter_uses_structured_output(monkeypatch):
    from blackbox.providers import Provider
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': '{}'}, 'prompt_eval_count': 4, 'eval_count': 5}
    def post(url, **kwargs):
        captured.update(kwargs)
        return Response()
    monkeypatch.setattr('blackbox.providers.httpx.post', post)
    result = Provider('ollama', 'configured-model').analyze('evidence')
    assert captured['json']['stream'] is False and 'properties' in captured['json']['format']
    assert captured['json']['options']['num_ctx'] == 2048
    assert captured['json']['think'] is False and captured['json']['options']['num_predict'] == 768
    assert captured['json']['truncate'] is False and captured['json']['shift'] is False
    assert captured['follow_redirects'] is False and captured['trust_env'] is False
    assert result.usage['input_tokens'] == 4


def test_ollama_rejects_truncated_completion(monkeypatch):
    from blackbox.providers import Provider, ProviderError
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': '{'}, 'done_reason': 'length'}
    monkeypatch.setattr('blackbox.providers.httpx.post', lambda *a, **kw: Response())
    with pytest.raises(ProviderError, match='token limit'):
        Provider('ollama', 'test-model').analyze('evidence')


def test_gemini_adapter_configures_structured_response(monkeypatch):
    from google import genai
    from blackbox.providers import Provider
    captured = {}
    class Response:
        text = '{}'
        usage_metadata = None
    class Models:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return Response()
    class Client:
        def __init__(self, **kwargs):
            self.models = Models()
            captured['client'] = kwargs
        def close(self): captured['closed'] = True
    monkeypatch.setattr(genai, 'Client', Client)
    result = Provider('gemini', 'configured-model', 'test-key').analyze('fixture only')
    assert result.text == '{}' and captured['model'] == 'configured-model'
    assert captured['config'].response_mime_type == 'application/json'
    assert captured['config'].response_json_schema is not None and captured['closed']


def test_static_caller_is_pinned_and_not_runtime_assertion(setup):
    client, event, _, repo = setup
    (repo / 'app.py').write_text('def fail(value):\n    return 1 / value\n\ndef caller():\n    return fail(0)\n', encoding='utf8')
    subprocess.run(['git', '-C', str(repo), 'add', 'app.py'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'caller'], check=True)
    event['commit'] = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    (repo / 'app.py').write_text('different working tree', encoding='utf8')
    iid = client.post('/events', json=event).json()['incident_id']
    evidence = client.get(f'/incidents/{iid}/context').json()['context']['evidence']
    static = [x for x in evidence if x['type'] == 'static_call']
    assert len(static) == 1 and static[0]['source_line'] == '    return fail(0)'
    assert 'execution' in static[0]['notice'] and static[0]['commit'] == event['commit']


def test_model_cannot_assert_verified_root_cause(setup, monkeypatch):
    from blackbox.providers import ProviderResult
    client, event, _, _ = setup
    class Unsupported(MockProvider):
        def analyze(self, prompt):
            data = json.loads(super().analyze(prompt).text)
            data['outcome'] = 'ROOT_CAUSE_SUPPORTED'
            ref = data['observed_failure']['evidence_ids'][0]
            data['hypotheses'] = [{'explanation': 'guess', 'supporting_evidence': [ref, 'frame:0'], 'contradicting_evidence': []}]
            return ProviderResult(json.dumps(data), {})
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: Unsupported())
    iid = client.post('/events', json=event).json()['incident_id']
    result = client.post(f'/incidents/{iid}/investigations', json={}).json()['investigation']
    assert result['status'] == 'failed' and result['outcome'] == 'INVESTIGATION_FAILED'


def test_abstention_requires_missing_information_and_no_primary_hypothesis():
    from pydantic import ValidationError
    from blackbox.investigation_schema import Findings
    data = {'outcome': 'INSUFFICIENT_EVIDENCE', 'observed_failure': {'text':'failure','evidence_ids':['event:1']},
            'observed_facts': [], 'hypotheses': [], 'alternatives': [], 'missing_evidence': ['missing source'], 'verification_steps': ['inspect']}
    assert Findings.model_validate(data).outcome == 'INSUFFICIENT_EVIDENCE'
    with pytest.raises(ValidationError):
        Findings.model_validate({**data, 'missing_evidence': []})
    with pytest.raises(ValidationError):
        Findings.model_validate({**data, 'hypotheses': [{'explanation':'guess','supporting_evidence':['event:1'],'contradicting_evidence':[]}]})


def test_likely_cause_requires_resolved_source_and_event(setup, monkeypatch):
    from blackbox.providers import ProviderResult
    client, event, _, _ = setup
    class NoSource(MockProvider):
        def analyze(self, prompt):
            data = json.loads(super().analyze(prompt).text)
            data['outcome'] = 'LIKELY_CAUSE'
            data['hypotheses'] = [{'explanation': 'guess', 'supporting_evidence': [data['observed_failure']['evidence_ids'][0]], 'contradicting_evidence': []}]
            return ProviderResult(json.dumps(data), {})
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: NoSource())
    iid = client.post('/events', json=event).json()['incident_id']
    result = client.post(f'/incidents/{iid}/investigations', json={}).json()['investigation']
    assert result['outcome'] == 'INVESTIGATION_FAILED'


def test_missing_evidence_record_is_citeable(setup):
    client, event, _, _ = setup
    event['commit'] = '0' * 40
    iid = client.post('/events', json=event).json()['incident_id']
    evidence = client.get(f'/incidents/{iid}/context').json()['context']['evidence']
    missing = next(x for x in evidence if x['id'] == 'missing_evidence')
    assert any('commit not found' in item for item in missing['items'])


CASES = json.loads((Path(__file__).parent / 'fixtures' / 'investigation_cases.json').read_text(encoding='utf8'))


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
def test_mocked_scenarios(setup, monkeypatch, case):
    client, event, _, _ = setup
    provider = MockProvider()
    provider.assessment = case['expected']
    monkeypatch.setattr('blackbox.app.configured_provider', lambda: provider)
    event['message'] = case['message']
    if case.get('missing_file'): event['frames'][0]['path'] = 'missing.py'
    if case.get('missing_commit'): event['commit'] = '0' * 40
    iid = client.post('/events', json=event).json()['incident_id']
    if case.get('repeat'):
        event['event_id'] = str(uuid.uuid4())
        client.post('/events', json=event)
    result = client.post(f'/incidents/{iid}/investigations', json={}).json()['investigation']
    assert result['status'] == 'completed'
    assert result['findings']['outcome'] == ('LIKELY_CAUSE' if case['expected'] == 'plausible' else 'INSUFFICIENT_EVIDENCE')
    if case.get('missing_file') or case.get('missing_commit'):
        assert any('frame:0' in x for x in result['evidence']['missing_evidence'])
