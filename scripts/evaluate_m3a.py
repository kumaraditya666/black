"""Measure the restricted Proof-of-Fix pipeline against the pinned trusted fixtures.

Fixture-level approvals recorded here exist to exercise the patch stage. They are labelled
`m3a-benchmark` and are not evidence of human judgement for a production repair.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blackbox.investigator import investigate
from blackbox.providers import ProviderError, configured_provider
from blackbox.repair.eligibility import evaluate, hypothesis_digest
from blackbox.repair.execution import detect_isolation
from blackbox.repair.fixtures import get_fixture
from blackbox.repair.pipeline import run_repair
from blackbox.schemas import Event, Frame
from blackbox.store import Store

CASES = ['division_by_zero', 'argument_validation', 'off_by_one', 'missing_config', 'unreproducible']


def head(repo: Path) -> str:
    return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()


def make_incident(store: Store, fixture: dict, commit: str) -> int:
    event = Event(event_id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc), commit=commit,
                  exception_type=fixture['event']['exception_type'],
                  message=fixture['event']['message'],
                  traceback='Synthetic M3A fixture failure; client-reported frames.',
                  frames=[Frame(**fixture['event']['frame'])])
    incident_id, _ = store.ingest(event)
    return incident_id


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run the real local model through the M3A repair pipeline')
    parser.add_argument('--db', default=str(ROOT / 'data' / ('m3a-evaluation-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.db')))
    parser.add_argument('--output', default=str(ROOT / 'data' / 'milestone3a-run.json'))
    parser.add_argument('--cases', nargs='*', default=CASES, choices=CASES)
    parser.add_argument('--reviewer', default='m3a-benchmark')
    parser.add_argument('--approve-all', action='store_true',
                        help='record labelled fixture-level approvals so the patch stage runs')
    args = parser.parse_args(argv)

    try:
        provider = configured_provider()
    except ProviderError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    isolation = detect_isolation()
    commit = head(ROOT)
    store = Store(args.db)
    runs = []
    for name in args.cases:
        fixture = get_fixture(name)
        started = time.monotonic()
        case = {'case': name, 'commit': commit, 'fixture_description': fixture['description']}
        incident_id = make_incident(store, fixture, commit)
        mark = time.monotonic()
        investigation, _ = investigate(store, ROOT, incident_id, provider)
        case['investigation'] = {
            'id': investigation['id'], 'status': investigation['status'],
            'outcome': investigation.get('outcome'), 'error': investigation.get('error'),
            'latency_ms': investigation.get('latency_ms'), 'usage': investigation.get('usage'),
        }
        case['investigation_ms'] = int((time.monotonic() - mark) * 1000)
        approval = None
        if args.approve_all and investigation['status'] == 'completed' and investigation.get('outcome') == 'LIKELY_CAUSE':
            hypothesis = investigation['findings']['hypotheses'][0]
            approval = store.add_repair_approval(
                investigation['id'], 0, hypothesis_digest(hypothesis), investigation['evidence_hash'],
                args.reviewer, 'Fixture-level benchmark approval; not a production review.')
        case['approval'] = {'recorded': bool(approval), 'reviewer': args.reviewer if approval else None,
                            'mode': 'fixture-level benchmark' if approval else None}
        eligibility = evaluate(store, ROOT, investigation['id'], name)
        case['eligibility'] = eligibility.summary()
        if eligibility.eligible:
            mark = time.monotonic()
            attempt = run_repair(store, ROOT, investigation['id'], name, provider, isolation=isolation)
            case['repair_ms'] = int((time.monotonic() - mark) * 1000)
            case['attempt'] = {key: attempt.get(key) for key in
                               ('id', 'status', 'error', 'commit', 'diff', 'proposal', 'timings', 'usage',
                                'reproduction_before', 'reproduction_after', 'regression', 'isolation')}
            if attempt.get('reproduction_before'):
                case['reproduction_before_failed'] = attempt['reproduction_before'].get('returncode') == 1
            if attempt.get('reproduction_after'):
                case['reproduction_after_passed'] = attempt['reproduction_after'].get('returncode') == 0
            if attempt.get('regression'):
                case['regression_passed'] = attempt['regression'].get('returncode') == 0
            case['patch_generated'] = bool(attempt.get('proposal'))
            case['patch_rejected'] = attempt['status'] == 'PATCH_REJECTED'
        case['total_ms'] = int((time.monotonic() - started) * 1000)
        runs.append(case)
        print(f"{name:22} inv={case['investigation']['outcome']} "
              f"repair={(case.get('attempt') or {}).get('status', 'not attempted')} "
              f"total={case['total_ms']}ms", flush=True)

    attempted = [run['attempt'] for run in runs if run.get('attempt')]
    statuses = {}
    for attempt in attempted:
        statuses[attempt['status']] = statuses.get(attempt['status'], 0) + 1
    summary = {
        'cases': len(runs),
        'eligible': sum(1 for run in runs if run['eligibility']['eligible']),
        'attempted': len(attempted),
        'verified': statuses.get('VERIFIED_IN_TEST_ENVIRONMENT', 0),
        'patch_failed': statuses.get('PATCH_FAILED', 0),
        'patch_rejected': statuses.get('PATCH_REJECTED', 0),
        'unverified': statuses.get('UNVERIFIED', 0),
        'environment_failed': statuses.get('ENVIRONMENT_FAILED', 0),
        'generation_failed': statuses.get('GENERATION_FAILED', 0),
        'reproduction_confirmed': sum(1 for run in runs if run.get('reproduction_before_failed')),
        'reproduction_passed_after': sum(1 for run in runs if run.get('reproduction_after_passed')),
        'regression_passed': sum(1 for run in runs if run.get('regression_passed')),
        'total_ms_median': int(statistics.median([run['total_ms'] for run in runs])) if runs else None,
    }
    latencies = [run['attempt']['usage'].get('eval_duration_ns', 0) / 1e6
                 for run in runs if run.get('attempt') and run['attempt'].get('usage')]
    summary['model_generation_ms'] = [round(value) for value in latencies]
    payload = {
        'milestone': '3A', 'created_at': datetime.now(timezone.utc).isoformat(),
        'model': provider.model, 'provider': provider.name, 'revision': commit,
        'isolation': {'mode': isolation.mode, 'detail': isolation.detail},
        'context_length': int(os.environ.get('BLACKBOX_OLLAMA_CONTEXT_LENGTH', '2048')),
        'approval_mode': 'fixture-level benchmark; not a production review',
        'database': args.db,
        'summary': summary, 'cases': runs,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps(summary, indent=2))
    print('saved', args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
