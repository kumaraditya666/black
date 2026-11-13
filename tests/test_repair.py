import copy
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from blackbox.investigator import investigate
from blackbox.providers import ProviderResult
from blackbox.repair.eligibility import evaluate, hypothesis_digest
from blackbox.repair.execution import Isolation
from blackbox.repair.fixtures import PROJECT_ROOT, get_fixture
from blackbox.repair.pipeline import run_repair
from blackbox.schemas import Event, Frame
from blackbox.store import Store

HEAD = subprocess.check_output(['git', '-C', str(PROJECT_ROOT), 'rev-parse', 'HEAD'], text=True).strip()
PROCESS = Isolation('process', True, 'test process jail')

DIVISION_FIX = [{
    'path': 'app.py',
    'find': "    return sum(values) / len(values)",
    'replace': "    if not values:\n        raise ValueError('average of an empty collection')\n    return sum(values) / len(values)",
    'explanation': 'Reject empty input before dividing.',
}]
OFF_BY_ONE_CORRECT = [{
    'path': 'app.py',
    'find': '    for index in range(len(items) + 1):',
    'replace': '    for index in range(len(items)):',
    'explanation': 'Stop the loop at the final element.',
}]
OFF_BY_ONE_NAIVE = [{
    'path': 'app.py',
    'find': '    for index in range(len(items) + 1):',
    'replace': '    for index in range(len(items) - 1):',
    'explanation': 'Shrink the loop instead of removing the extra step.',
}]


class CauseProvider:
    name = 'ollama'
    model = 'mock-investigator'

    def __init__(self, outcome='LIKELY_CAUSE'):
        self.outcome = outcome

    def analyze(self, prompt):
        snapshot = json.loads(prompt.split('UNTRUSTED EVIDENCE JSON:\n', 1)[1])
        event_id = next(item['id'] for item in snapshot['evidence'] if item['type'] == 'event')
        frame = next(item for item in snapshot['evidence']
                     if item.get('type') == 'stack_frame' and item.get('status') == 'resolved')
        data = {'outcome': self.outcome,
                'observed_failure': {'text': 'The recorded event failed.', 'evidence_ids': [event_id]},
                'observed_facts': [], 'hypotheses': [], 'alternatives': [],
                'missing_evidence': ['Runtime argument values were not recorded.'],
                'verification_steps': ['Inspect the recorded frame.']}
        if self.outcome == 'LIKELY_CAUSE':
            data['hypotheses'] = [{'explanation': 'The input reaches the operation without a guard.',
                                   'supporting_evidence': [event_id, frame['id']],
                                   'contradicting_evidence': []}]
        return ProviderResult(json.dumps(data), {'input_tokens': 10, 'output_tokens': 10})


class PatchProvider:
    name = 'ollama'
    model = 'mock-patch'

    def __init__(self, changes):
        self.changes = changes
        self.calls = 0

    def structured(self, prompt, schema, system=None):
        self.calls += 1
        return ProviderResult(json.dumps({'summary': 'Minimal guarded change.',
                                          'changes': self.changes,
                                          'risks': ['Only tested in the disposable fixture.']}),
                              {'input_tokens': 200, 'output_tokens': 50, 'estimated_cost': None})


def make_case(tmp_path, fixture_name, outcome='LIKELY_CAUSE'):
    store = Store(str(tmp_path / f'{fixture_name}-{uuid.uuid4().hex}.db'))
    fixture = get_fixture(fixture_name)
    event = Event(event_id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc), commit=HEAD,
                  exception_type=fixture['event']['exception_type'],
                  message=fixture['event']['message'], traceback='synthetic fixture failure',
                  frames=[Frame(**fixture['event']['frame'])])
    incident_id, _ = store.ingest(event)
    investigation, _ = investigate(store, PROJECT_ROOT, incident_id, CauseProvider(outcome))
    return store, investigation


def approve(store, investigation, index=0):
    hypothesis = investigation['findings']['hypotheses'][index]
    return store.add_repair_approval(investigation['id'], index, hypothesis_digest(hypothesis),
                                     investigation['evidence_hash'], 'test-reviewer', 'reviewed')


def attempt_for(tmp_path, fixture_name, changes):
    store, investigation = make_case(tmp_path, fixture_name)
    approve(store, investigation)
    provider = PatchProvider(changes)
    attempt = run_repair(store, PROJECT_ROOT, investigation['id'], fixture_name, provider, isolation=PROCESS)
    return store, attempt, provider


class FakeStore:
    def __init__(self, investigation, approvals=()):
        self.record = investigation
        self.approvals = list(approvals)

    def investigation(self, investigation_id):
        return self.record

    def repair_approvals(self, investigation_id):
        return self.approvals


def approval_for(investigation):
    hypothesis = investigation['findings']['hypotheses'][0]
    return {'id': 'approval-1', 'hypothesis_index': 0,
            'hypothesis_sha256': hypothesis_digest(hypothesis),
            'evidence_hash': investigation['evidence_hash'], 'reviewer': 'test-reviewer'}


def reasons(eligibility):
    return {reason['code'] for reason in eligibility.summary()['reasons']}


def test_verified_patch_runs_the_same_test_before_and_after(tmp_path):
    store, attempt, provider = attempt_for(tmp_path, 'division_by_zero', DIVISION_FIX)
    assert attempt['status'] == 'VERIFIED_IN_TEST_ENVIRONMENT'
    assert attempt['commit'] == HEAD and attempt['fixture'] == 'division_by_zero'
    assert attempt['reproduction_before']['returncode'] == 1
    assert attempt['reproduction_after']['returncode'] == 0
    assert attempt['regression']['returncode'] == 0
    assert 'raise ValueError' in attempt['diff']
    assert attempt['isolation']['mode'] == 'process'
    assert provider.calls == 1
    assert store.repair_attempts()[0]['id'] == attempt['id']
    assert store.repair_attempt(attempt['id'])['timings']['total_ms'] >= 0


def test_patch_that_still_fails_the_reproduction_is_patch_failed(tmp_path):
    _, attempt, _ = attempt_for(tmp_path, 'division_by_zero', [{
        'path': 'app.py', 'find': "    return sum(values) / len(values)",
        'replace': '    return 0', 'explanation': 'Return a sentinel.'}])
    assert attempt['status'] == 'PATCH_FAILED'
    assert attempt['reproduction_before']['returncode'] == 1
    assert attempt['reproduction_after']['returncode'] == 1
    assert attempt['regression'] is None


def test_regression_suite_detects_a_naive_off_by_one_fix(tmp_path):
    _, attempt, _ = attempt_for(tmp_path, 'off_by_one', OFF_BY_ONE_NAIVE)
    assert attempt['status'] == 'PATCH_FAILED'
    assert attempt['reproduction_after']['returncode'] == 0
    assert attempt['regression']['returncode'] == 1
    assert 'regression' in attempt['error']
    # The correct fix, which handles a zero count, is verified by both suites.
    _, good, _ = attempt_for(tmp_path, 'off_by_one', OFF_BY_ONE_CORRECT)
    assert good['status'] == 'VERIFIED_IN_TEST_ENVIRONMENT'


def test_unreproducible_bug_is_unverified_without_calling_the_model(tmp_path):
    store, investigation = make_case(tmp_path, 'unreproducible')
    approve(store, investigation)
    provider = PatchProvider(DIVISION_FIX)
    attempt = run_repair(store, PROJECT_ROOT, investigation['id'], 'unreproducible', provider, isolation=PROCESS)
    assert attempt['status'] == 'UNVERIFIED'
    assert attempt['reproduction_before']['returncode'] == 0
    assert provider.calls == 0 and attempt['proposal'] is None


def test_repair_requires_a_matching_human_approval(tmp_path):
    store, investigation = make_case(tmp_path, 'division_by_zero')
    provider = PatchProvider(DIVISION_FIX)
    attempt = run_repair(store, PROJECT_ROOT, investigation['id'], 'division_by_zero', provider, isolation=PROCESS)
    assert attempt['status'] == 'ELIGIBILITY_BLOCKED'
    assert 'human_approval' in attempt['error']
    assert provider.calls == 0


@pytest.mark.parametrize('changes,detail', [
    ([{'path': 'tests/test_regression.py', 'find': 'def test_average_of_values():',
       'replace': 'def test_average_of_values():  # edited', 'explanation': 'Edit a test.'}],
     'not an approved source file'),
    ([{'path': 'app.py', 'find': '    return sum(values) / len(values)',
       'replace': '    import subprocess\n    return sum(values) / len(values)',
       'explanation': 'Spawn a process.'}], 'forbidden construct'),
    ([{'path': 'app.py', 'find': 'not present in the file', 'replace': 'x',
       'explanation': 'Mismatched find.'}], 'exactly one is required'),
])
def test_unsafe_or_unappliable_patches_are_rejected(tmp_path, changes, detail):
    _, attempt, _ = attempt_for(tmp_path, 'division_by_zero', changes)
    assert attempt['status'] == 'PATCH_REJECTED'
    assert detail in attempt['error']
    assert attempt['proposal'] and attempt['diff'] is None


def test_gate_blocks_failed_and_abstained_investigations(tmp_path):
    store, investigation = make_case(tmp_path, 'division_by_zero')
    approval = approval_for(investigation)
    failed = copy.deepcopy(investigation)
    failed['status'], failed['outcome'] = 'failed', 'INVESTIGATION_FAILED'
    assert 'outcome_likely_cause' in reasons(evaluate(FakeStore(failed, [approval]), PROJECT_ROOT,
                                                     investigation['id'], 'division_by_zero'))
    abstained = copy.deepcopy(investigation)
    abstained['outcome'], abstained['findings']['hypotheses'] = 'INSUFFICIENT_EVIDENCE', []
    assert 'outcome_likely_cause' in reasons(evaluate(FakeStore(abstained, [approval]), PROJECT_ROOT,
                                                     investigation['id'], 'division_by_zero'))


def test_gate_blocks_missing_revision_unresolved_frame_and_bad_references(tmp_path):
    _, investigation = make_case(tmp_path, 'division_by_zero')
    approval = approval_for(investigation)
    missing = copy.deepcopy(investigation)
    missing['evidence']['evidence'][0]['commit'] = '0' * 40
    assert {'recorded_revision', 'source_pinned'} <= reasons(
        evaluate(FakeStore(missing, [approval]), PROJECT_ROOT, investigation['id'], 'division_by_zero'))
    unresolved = copy.deepcopy(investigation)
    frame = next(item for item in unresolved['evidence']['evidence'] if item.get('type') == 'stack_frame')
    frame['status'], frame['reason'] = 'unresolved', 'commit not found'
    assert 'resolved_source_frame' in reasons(
        evaluate(FakeStore(unresolved, [approval]), PROJECT_ROOT, investigation['id'], 'division_by_zero'))
    bad_reference = copy.deepcopy(investigation)
    bad_reference['findings']['hypotheses'][0]['supporting_evidence'].append('event:missing')
    assert 'evidence_references_valid' in reasons(
        evaluate(FakeStore(bad_reference, [approval]), PROJECT_ROOT, investigation['id'], 'division_by_zero'))


def test_gate_blocks_untrusted_repository_unknown_fixture_and_stale_approval(tmp_path):
    _, investigation = make_case(tmp_path, 'division_by_zero')
    approval = approval_for(investigation)
    assert 'repository_trusted' in reasons(evaluate(FakeStore(investigation, [approval]), tmp_path,
                                                    investigation['id'], 'division_by_zero'))
    assert 'fixture_known' in reasons(evaluate(FakeStore(investigation, [approval]), PROJECT_ROOT,
                                               investigation['id'], 'unknown_fixture'))
    stale = {**approval, 'evidence_hash': '0' * 64}
    assert 'human_approval' in reasons(evaluate(FakeStore(investigation, [stale]), PROJECT_ROOT,
                                                investigation['id'], 'division_by_zero'))
    changed = {**approval, 'hypothesis_sha256': '0' * 64}
    assert 'human_approval' in reasons(evaluate(FakeStore(investigation, [changed]), PROJECT_ROOT,
                                                investigation['id'], 'division_by_zero'))


def test_approval_is_idempotent_and_review_cannot_change_status(tmp_path):
    store, attempt, _ = attempt_for(tmp_path, 'division_by_zero', DIVISION_FIX)
    investigation_id = attempt['investigation_id']
    first = store.add_repair_approval(investigation_id, 0, 'a' * 64, 'b' * 64, 'reviewer')
    second = store.add_repair_approval(investigation_id, 0, 'a' * 64, 'b' * 64, 'reviewer')
    assert first['id'] == second['id'] and len(store.repair_approvals(investigation_id)) == 2
    reviewed = store.review_repair_attempt(attempt['id'], 'accept', 'developer', 'tests look right')
    assert reviewed['review']['decision'] == 'accept'
    assert reviewed['status'] == 'VERIFIED_IN_TEST_ENVIRONMENT'


def test_pipeline_never_mutates_the_fixture_repository(tmp_path):
    fixture_root = PROJECT_ROOT / 'fixtures' / 'repair'
    def contents():
        return {p.relative_to(fixture_root).as_posix(): p.read_bytes()
                for p in fixture_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    before = contents()
    attempt_for(tmp_path, 'missing_config', [{
        'path': 'app.py', 'find': "    return config['timeout']",
        'replace': "    return config.get('timeout', 30)", 'explanation': 'Use a default.'}])
    assert contents() == before
