"""Local developer interface for the restricted Proof-of-Fix pipeline.

There is no merge, remote write, PR or deployment action here. `review` records a developer decision
but cannot change the test-derived verification status.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blackbox.providers import ProviderError, configured_provider
from blackbox.repair.eligibility import evaluate, hypothesis_digest
from blackbox.repair.execution import detect_isolation
from blackbox.repair.fixtures import PROJECT_ROOT
from blackbox.repair.pipeline import run_repair
from blackbox.store import Store

NOTICE = 'Verification is limited to the disposable test environment; it is not production proof.'


def _store(args) -> Store:
    return Store(args.db)


def _repo(args) -> Path:
    return Path(args.repo).resolve()


def _investigation_or_exit(store: Store, investigation_id: str):
    investigation = store.investigation(investigation_id)
    if not investigation:
        print(f'investigation not found: {investigation_id}', file=sys.stderr)
        raise SystemExit(2)
    return investigation


def command_eligibility(args):
    eligibility = evaluate(_store(args), _repo(args), args.investigation, args.fixture)
    print(json.dumps(eligibility.summary(), indent=2))
    return 0 if eligibility.eligible else 1


def command_approve(args):
    store = _store(args)
    investigation = _investigation_or_exit(store, args.investigation)
    findings = investigation.get('findings') or {}
    hypotheses = findings.get('hypotheses') or []
    if not 0 <= args.hypothesis < len(hypotheses):
        print(f'no hypothesis {args.hypothesis}; investigation has {len(hypotheses)}', file=sys.stderr)
        return 2
    hypothesis = hypotheses[args.hypothesis]
    digest = hypothesis_digest(hypothesis)
    print('Investigation outcome:', investigation.get('outcome'))
    print('Hypothesis:', hypothesis.get('explanation'))
    print('Supporting evidence:', hypothesis.get('supporting_evidence'))
    print('Hypothesis hash:', digest)
    if investigation.get('outcome') != 'LIKELY_CAUSE':
        print('Warning: this outcome is not eligible for repair; the approval cannot unblock it.', file=sys.stderr)
    if not args.confirm_hash:
        print('Review the text above, then re-run with --confirm-hash', digest)
        return 2
    if args.confirm_hash != digest:
        print('Refusing: the confirmed hash does not match the current hypothesis.', file=sys.stderr)
        return 2
    approval = store.add_repair_approval(investigation['id'], args.hypothesis, digest,
                                         investigation['evidence_hash'], args.reviewer, args.note)
    print(json.dumps(approval, indent=2))
    return 0


def command_attempt(args):
    store = _store(args)
    try:
        provider = configured_provider()
    except ProviderError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    isolation = detect_isolation()
    attempt = run_repair(store, _repo(args), args.investigation, args.fixture, provider, isolation=isolation)
    if attempt is None:
        print('repair attempt was not recorded', file=sys.stderr)
        return 2
    print('Attempt:', attempt['id'])
    print('Status:', attempt['status'])
    print('Isolation:', (attempt.get('isolation') or {}).get('mode'), '-', (attempt.get('isolation') or {}).get('detail'))
    print('Revision:', attempt.get('commit'))
    if attempt.get('error'):
        print('Error:', attempt['error'])
    if attempt.get('diff'):
        print('\nProposed diff:\n')
        print(attempt['diff'])
    print(NOTICE)
    return 0 if attempt['status'] == 'VERIFIED_IN_TEST_ENVIRONMENT' else 3


def _print_execution(label: str, result: dict | None):
    if not result:
        print(f'{label}: not run')
        return
    print(f"{label}: returncode={result.get('returncode')} timed_out={result.get('timed_out')} "
          f"environment_error={result.get('environment_error')}")
    output = (result.get('output') or '').strip().splitlines()
    if output:
        print('  ' + '\n  '.join(output[-12:]))


def command_show(args):
    store = _store(args)
    attempt = store.repair_attempt(args.attempt)
    if not attempt:
        print(f'repair attempt not found: {args.attempt}', file=sys.stderr)
        return 2
    investigation = store.investigation(attempt['investigation_id']) or {}
    findings = investigation.get('findings') or {}
    events = store.events(attempt['incident_id']) if attempt.get('incident_id') else []
    event = events[-1] if events else {}
    approval = next((item for item in store.repair_approvals(attempt['investigation_id'])
                     if item['id'] == attempt.get('approval_id')), None)
    print('=' * 78)
    print('REPAIR ATTEMPT', attempt['id'])
    print('Status:', attempt['status'], '| Fixture:', attempt['fixture'], '| Revision:', attempt.get('commit'))
    print('Isolation:', json.dumps(attempt.get('isolation')))
    print('\nORIGINAL INCIDENT')
    print(' ', event.get('exception_type'), '-', event.get('message'))
    print('  commit:', event.get('commit'))
    for index, frame in enumerate(event.get('frames') or []):
        print(f"  frame:{index} {frame['function']}@{frame['path']}:{frame['line']}")
    print('\nAPPROVED ROOT-CAUSE HYPOTHESIS')
    hypotheses = findings.get('hypotheses') or []
    if hypotheses:
        print(' ', hypotheses[0].get('explanation'))
        print('  evidence:', hypotheses[0].get('supporting_evidence'))
        print('  verification:', hypotheses[0].get('verification_status'))
    if approval:
        print('  reviewed by:', approval['reviewer'], 'at', approval['created_at'])
    else:
        print('  no matching review record')
    print('\nPROPOSED PATCH')
    proposal = attempt.get('proposal') or {}
    print(' ', proposal.get('summary'))
    for change in proposal.get('changes') or []:
        print(f"  {change['path']}: {change.get('explanation')}")
    print('  risks:', proposal.get('risks'))
    print('\nDIFF')
    print(attempt.get('diff') or '  (no diff)')
    print('\nREPRODUCTION BEFORE PATCH')
    _print_execution('  before', attempt.get('reproduction_before'))
    print('\nREPRODUCTION AFTER PATCH')
    _print_execution('  after', attempt.get('reproduction_after'))
    print('\nREGRESSION TESTS')
    _print_execution('  regression', attempt.get('regression'))
    print('\nVERIFICATION')
    print(' ', attempt['status'], '-', attempt.get('error') or 'no error recorded')
    print('  timings:', json.dumps(attempt.get('timings')))
    print('  usage:', json.dumps(attempt.get('usage')))
    print('  developer review:', json.dumps(attempt.get('review')))
    print('\n' + NOTICE)
    return 0


def command_review(args):
    store = _store(args)
    attempt = store.review_repair_attempt(args.attempt, args.decision, args.reviewer, args.note)
    if not attempt:
        print(f'repair attempt not found: {args.attempt}', file=sys.stderr)
        return 2
    print(json.dumps(attempt['review'], indent=2))
    print('Verification status is unchanged:', attempt['status'])
    return 0


def command_list(args):
    attempts = _store(args).repair_attempts()
    if not attempts:
        print('no repair attempts recorded')
        return 0
    for attempt in attempts:
        print(f"{attempt['id']}  {attempt['status']:<30} {attempt['fixture']:<22} {attempt['commit'] or '-'}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Restricted local Proof-of-Fix review interface')
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--db', default=os.environ.get('BLACKBOX_DB', 'data/events.db'))
    common.add_argument('--repo', default=str(PROJECT_ROOT))
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('eligibility', parents=[common], help='show the repair eligibility gate')
    p.add_argument('investigation')
    p.add_argument('--fixture', required=True)
    p.set_defaults(func=command_eligibility)

    p = sub.add_parser('approve', parents=[common], help='record a human review of one hypothesis')
    p.add_argument('investigation')
    p.add_argument('--hypothesis', type=int, default=0)
    p.add_argument('--reviewer', required=True)
    p.add_argument('--confirm-hash')
    p.add_argument('--note')
    p.set_defaults(func=command_approve)

    p = sub.add_parser('attempt', parents=[common], help='run reproduction, generation, patching and tests')
    p.add_argument('investigation')
    p.add_argument('--fixture', required=True)
    p.set_defaults(func=command_attempt)

    p = sub.add_parser('show', parents=[common], help='show one complete repair report')
    p.add_argument('attempt')
    p.set_defaults(func=command_show)

    p = sub.add_parser('review', parents=[common], help='record a developer decision on an attempt')
    p.add_argument('attempt')
    p.add_argument('--decision', choices=('accept', 'reject'), required=True)
    p.add_argument('--reviewer', required=True)
    p.add_argument('--note')
    p.set_defaults(func=command_review)

    p = sub.add_parser('list', parents=[common], help='list repair attempts')
    p.set_defaults(func=command_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
