"""Restricted end-to-end Proof-of-Fix pipeline.

Order is fixed: eligibility, reproduce at the pinned revision, generate, validate, apply only in a
disposable workspace, re-run the same reproduction test, then the regression suite. A verified status
is derived solely from those process exit codes and the recorded revision; it never comes from model
prose or confidence.
"""
import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from blackbox.providers import ProviderError

from .eligibility import evaluate
from .execution import detect_isolation, run_tests
from .fixtures import materialize
from .patch import PatchFormatError, PatchRejected, build_prompt, parse_proposal, validate_and_apply
from .schema import PatchProposal


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _workspace(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _drop(path: Path | None):
    if path is not None and os.environ.get('BLACKBOX_REPAIR_KEEP_WORKSPACE') != '1':
        shutil.rmtree(path, ignore_errors=True)


def run_repair(store, repo: Path, investigation_id: str, fixture_name: str, provider,
               hypothesis_index: int | None = None, isolation=None) -> dict:
    attempt_id = str(uuid.uuid4())
    created = _now()
    record = {
        'id': attempt_id, 'incident_id': None, 'investigation_id': investigation_id,
        'fixture': fixture_name, 'commit': None, 'status': 'ENVIRONMENT_FAILED',
        'approval_id': None, 'proposal': None, 'validation': None, 'diff': None,
        'reproduction_before': None, 'reproduction_after': None, 'regression': None,
        'isolation': None, 'error': None, 'timings': {}, 'usage': None, 'review': None,
        'created_at': created, 'updated_at': created,
    }
    timings: dict[str, int] = {}
    started = time.monotonic()

    def finish():
        timings['total_ms'] = _elapsed(started)
        record['timings'] = timings
        record['updated_at'] = _now()
        store.save_repair_attempt(record)

    try:
        eligibility = evaluate(store, repo, investigation_id, fixture_name, hypothesis_index)
        record['incident_id'] = (eligibility.investigation or {}).get('incident_id')
        record['commit'] = eligibility.commit
        record['approval_id'] = (eligibility.approval or {}).get('id')
        record['validation'] = {'eligibility': eligibility.summary()}
        if not eligibility.eligible:
            record['status'] = 'ELIGIBILITY_BLOCKED'
            record['error'] = 'eligibility gate failed: ' + ', '.join(
                reason['code'] for reason in eligibility.summary()['reasons'])
            finish()
            return store.repair_attempt(attempt_id)

        isolation = isolation or detect_isolation()
        record['isolation'] = {'mode': isolation.mode, 'detail': isolation.detail}
        if not isolation.available:
            record['status'] = 'ENVIRONMENT_FAILED'
            record['error'] = f'isolation is unavailable: {isolation.detail}'
            finish()
            return store.repair_attempt(attempt_id)

        fixture = eligibility.fixture
        commit = eligibility.commit
        reproduction = fixture['reproduction']
        marker = reproduction['failure_marker']
        before_dir = _workspace('blackbox-repair-before-')
        try:
            mark = time.monotonic()
            files = materialize(repo, commit, fixture, before_dir)
            timings['materialize_ms'] = _elapsed(mark)
            mark = time.monotonic()
            before = run_tests(before_dir, reproduction['test'], isolation)
            timings['reproduce_before_ms'] = _elapsed(mark)
        finally:
            _drop(before_dir)
        record['reproduction_before'] = before.public()

        if before.timed_out or before.environment_error:
            record['status'] = 'ENVIRONMENT_FAILED'
            record['error'] = 'the reproduction environment failed before a patch was attempted'
            finish()
            return store.repair_attempt(attempt_id)
        if before.returncode == 0:
            record['status'] = 'UNVERIFIED'
            record['error'] = 'the reproduction test already passes at the recorded revision; bug not reproduced'
            finish()
            return store.repair_attempt(attempt_id)
        if marker not in before.output:
            record['status'] = 'UNVERIFIED'
            record['error'] = 'the reproduction failed without the recorded failure signature'
            finish()
            return store.repair_attempt(attempt_id)

        try:
            system, prompt = build_prompt(eligibility, files)
        except PatchFormatError as exc:
            record['status'] = 'GENERATION_FAILED'
            record['error'] = str(exc)
            finish()
            return store.repair_attempt(attempt_id)
        mark = time.monotonic()
        try:
            response = provider.structured(prompt, PatchProposal.model_json_schema(), system=system)
            timings['generation_ms'] = _elapsed(mark)
            record['usage'] = response.usage
            proposal = parse_proposal(response.text)
        except PatchFormatError as exc:
            timings['generation_ms'] = _elapsed(mark)
            record['status'] = 'GENERATION_FAILED'
            record['error'] = str(exc)
            finish()
            return store.repair_attempt(attempt_id)
        except ProviderError as exc:
            timings['generation_ms'] = _elapsed(mark)
            record['status'] = 'GENERATION_FAILED'
            record['error'] = str(exc)[:300]
            if exc.usage:
                record['usage'] = exc.usage
            finish()
            return store.repair_attempt(attempt_id)
        except Exception:
            timings['generation_ms'] = _elapsed(mark)
            record['status'] = 'GENERATION_FAILED'
            record['error'] = 'provider request failed while generating a patch'
            finish()
            return store.repair_attempt(attempt_id)

        record['proposal'] = proposal.model_dump()
        after_dir = _workspace('blackbox-repair-after-')
        try:
            mark = time.monotonic()
            materialize(repo, commit, fixture, after_dir)
            try:
                updated, diff = validate_and_apply(proposal, fixture, files, after_dir)
            except PatchRejected as exc:
                record['status'] = 'PATCH_REJECTED'
                record['error'] = '; '.join(exc.errors)
                record['validation'] = {**record['validation'], 'rejected': exc.errors}
                finish()
                return store.repair_attempt(attempt_id)
            timings['apply_ms'] = _elapsed(mark)
            record['diff'] = diff
            record['validation'] = {**record['validation'], 'applied': True,
                                    'changed_files': sorted({change.path for change in proposal.changes})}

            mark = time.monotonic()
            after = run_tests(after_dir, reproduction['test'], isolation)
            timings['reproduce_after_ms'] = _elapsed(mark)
            record['reproduction_after'] = after.public()
            if after.timed_out or after.environment_error:
                record['status'] = 'ENVIRONMENT_FAILED'
                record['error'] = 'the reproduction environment failed after the patch was applied'
                finish()
                return store.repair_attempt(attempt_id)
            if after.returncode != 0:
                record['status'] = 'PATCH_FAILED'
                record['error'] = 'the reproduction test still fails after the patch'
                finish()
                return store.repair_attempt(attempt_id)

            mark = time.monotonic()
            regression = run_tests(after_dir, fixture['regression']['test'], isolation)
            timings['regression_ms'] = _elapsed(mark)
            record['regression'] = regression.public()
            if regression.timed_out or regression.environment_error:
                record['status'] = 'ENVIRONMENT_FAILED'
                record['error'] = 'the regression environment failed'
                finish()
                return store.repair_attempt(attempt_id)
            if regression.returncode != 0:
                record['status'] = 'PATCH_FAILED'
                record['error'] = 'the regression suite fails after the patch'
                finish()
                return store.repair_attempt(attempt_id)
            record['status'] = 'VERIFIED_IN_TEST_ENVIRONMENT'
            record['error'] = None
            finish()
            return store.repair_attempt(attempt_id)
        finally:
            _drop(after_dir)
    except Exception:
        record['status'] = 'ENVIRONMENT_FAILED'
        record['error'] = record['error'] or 'repair pipeline error; no result was verified'
        finish()
        return store.repair_attempt(attempt_id)
