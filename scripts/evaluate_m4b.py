"""Frozen local fixtures only; refuses to run without Docker and exact content pins."""
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

REV = '6117eda7e74f0a27677483555add08f435b7f850'
REG = ROOT / 'fixtures/repair/m4b-registry.json'
DATA = ROOT / 'data/m4b-paired-results.json'
AUDIT = ROOT / 'data/m4b-fixture-audit.json'
DB = ROOT / 'data/m4b-paired.db'


def main():
    if any(p.exists() for p in (DATA, AUDIT, DB)):
        raise RuntimeError('refuse overwrite')
    for p in (REG, ROOT / 'fixtures/repair/m4b-ground-truth.json'):
        if p.read_bytes() != subprocess.check_output(['git', '-C', str(ROOT), 'show', REV + ':' + p.relative_to(ROOT).as_posix()]):
            raise RuntimeError('metadata differs from frozen revision')
    fixtures.REGISTRY_PATH = REG
    cases = fixtures.load_registry()
    isolation = detect_isolation()
    if isolation.mode != 'docker' or not isolation.available:
        raise RuntimeError('Docker required')
    logs = {}
    for fixture in cases:
        if not fixtures.trusted(ROOT, fixture)[0] or not fixtures.content_pinned(ROOT, REV, fixture)[0]:
            raise RuntimeError('fixture trust or hash mismatch')
        with tempfile.TemporaryDirectory(prefix='m4b-audit-') as tmp:
            fixtures.materialize(ROOT, REV, fixture, Path(tmp))
            result = run_tests(Path(tmp), fixture['reproduction']['test'], isolation).public()
        if result['environment_error'] or result['security_blocked'] or result['timed_out'] or result['isolation'] != 'docker':
            raise RuntimeError('security or execution failure')
        expected = 1 if fixture['reproduction']['reproducible'] else 0
        if result['returncode'] != expected or (expected and fixture['reproduction']['failure_marker'] not in result['output']):
            raise RuntimeError('unexpected reproduction')
        logs[fixture['name']] = result
    AUDIT.write_text(json.dumps({'revision': REV, 'cases': logs}, indent=2), encoding='utf8')
    store = Store(str(DB))
    provider = Provider('ollama', 'qwen3.5:4b')
    snapshots, incidents = {}, {}
    for fixture in cases:
        ev = fixture['event']
        evidence = logs[fixture['name']]['output']
        event = Event(event_id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc), commit=REV,
                      exception_type=ev['exception_type'], message=ev['message'], traceback=evidence,
                      frames=[Frame(**ev['frame'])])
        incident, _ = store.ingest(event)
        incidents[fixture['name']] = incident
        snapshots[fixture['name']] = investigator.collect(store, ROOT, incident)
    rows = []
    for i, fixture in enumerate(cases):
        name = fixture['name']
        for repeat, order in ((False, ('A', 'B') if i % 2 == 0 else ('B', 'A')),
                              (True, ('B', 'A') if i % 2 == 0 else ('A', 'B'))):
            if repeat and i >= 2:
                continue
            for arm in order:
                start = time.monotonic()
                if arm == 'A':
                    inv, _ = investigator.investigate(store, ROOT, incidents[name], provider, force=True, snapshot=snapshots[name])
                    run = {'investigation': inv, 'status': inv['status'], 'wall_ms': int((time.monotonic()-start)*1000)}
                else:
                    run = investigate_with_retrieval(store, ROOT, incidents[name], name, provider, snapshot=snapshots[name])
                rows.append({'case': name, 'arm': arm, 'repeat': repeat, 'run': run})
                DATA.write_text(json.dumps({'revision': REV, 'model': provider.model, 'rows': rows}, indent=2, ensure_ascii=False), encoding='utf8')
                print(name, arm, 'repeat' if repeat else 'primary', run['status'], flush=True)


if __name__ == '__main__':
    main()
