"""Preregistered frozen-fixture, three-arm local model feasibility evaluation."""
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blackbox.investigator as investigator
import blackbox.repair.fixtures as fixtures
from blackbox.agent_retrieval import investigate_with_retrieval
from blackbox.providers import Provider
from blackbox.repair.execution import detect_isolation, run_tests
from blackbox.schemas import Event, Frame
from blackbox.store import Store

REV = '76564779c56068107aeccda8205147c6bbbea86e'
REG = ROOT / 'fixtures/repair/m4b1-registry.json'
LABELS = ROOT / 'fixtures/repair/m4b1-ground-truth.json'
AUDIT = ROOT / 'data/m4b1-fixture-audit.json'
OUT = ROOT / 'data/m4b1-results.json'
DB = ROOT / 'data/m4b1.db'


def main():
    if any(p.exists() for p in (AUDIT, OUT, DB)):
        raise RuntimeError('refuse overwrite')
    for p in (REG, LABELS):
        if p.read_bytes() != subprocess.check_output(['git', '-C', str(ROOT), 'show', REV + ':' + p.relative_to(ROOT).as_posix()]):
            raise RuntimeError('frozen metadata mismatch')
    fixtures.REGISTRY_PATH = REG
    cases = fixtures.load_registry()
    labels = {r['case']: r for r in json.loads(LABELS.read_text(encoding='utf8'))['labels']}
    isolation = detect_isolation()
    if isolation.mode != 'docker' or not isolation.available:
        raise RuntimeError('Docker required')
    logs = {}
    for fixture in cases:
        if not fixtures.trusted(ROOT, fixture)[0] or not fixtures.content_pinned(ROOT, REV, fixture)[0]:
            raise RuntimeError('fixture trust or pin mismatch')
        with tempfile.TemporaryDirectory(prefix='m4b1-audit-') as tmp:
            fixtures.materialize(ROOT, REV, fixture, Path(tmp))
            result = run_tests(Path(tmp), fixture['reproduction']['test'], isolation).public()
        if result['environment_error'] or result['security_blocked'] or result['timed_out'] or result['isolation'] != 'docker':
            raise RuntimeError('security or execution failure')
        expected = 1 if fixture['reproduction']['reproducible'] else 0
        if result['returncode'] != expected or (expected and fixture['reproduction']['failure_marker'] not in result['output']):
            raise RuntimeError('unexpected fixture result')
        logs[fixture['name']] = result
    AUDIT.write_text(json.dumps({'revision': REV, 'cases': logs}, indent=2), encoding='utf8')
    store = Store(str(DB))
    provider = Provider('ollama', 'qwen3.5:4b')
    snapshots, incidents = {}, {}
    for fixture in cases:
        ev = fixture['event']
        event = Event(event_id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc), commit=REV,
                      exception_type=ev['exception_type'], message=ev['message'], traceback=logs[fixture['name']]['output'],
                      frames=[Frame(**ev['frame'])])
        incident, _ = store.ingest(event)
        incidents[fixture['name']] = incident
        snapshots[fixture['name']] = investigator.collect(store, ROOT, incident)
        # Do not mistake already present source bodies for missing observations.
        for symbol in labels[fixture['name']]['useful_symbols']:
            source = '\n'.join(x.get('source', '') for x in snapshots[fixture['name']]['evidence'])
            if ('def ' + symbol + '(') in source:
                raise RuntimeError('preregistered target body already in initial evidence: ' + fixture['name'])
    rows = []
    versions = {'A': 'v1', 'B': 'v2', 'C': 'control'}
    orders = [('A','B','C'), ('B','C','A'), ('C','A','B')]
    for i, fixture in enumerate(cases):
        name = fixture['name']
        for arm in orders[i % 3]:
            run = investigate_with_retrieval(store, ROOT, incidents[name], name, provider,
                                              snapshot=snapshots[name], prompt_version=versions[arm], deadline_seconds=180)
            rows.append({'case': name, 'arm': arm, 'run': run})
            OUT.write_text(json.dumps({'revision': REV, 'model': provider.model, 'rows': rows}, indent=2, ensure_ascii=False), encoding='utf8')
            print(name, arm, run['status'], run.get('reason', ''), flush=True)
            if run['status'] == 'SECURITY_BLOCKED':
                raise RuntimeError('containment security block')


if __name__ == '__main__': main()
