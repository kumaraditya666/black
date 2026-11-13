"""One explicitly fixture-approved experimental repair after diagnostic evaluation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blackbox.repair.fixtures as fixtures
from blackbox.providers import Provider
from blackbox.repair.eligibility import hypothesis_digest
from blackbox.repair.execution import detect_isolation
from blackbox.repair.pipeline import run_repair
from blackbox.store import Store

output = ROOT / 'data/m4b-proof.json'
if output.exists():
    raise RuntimeError('refuse overwrite')
data = json.loads((ROOT / 'data/m4b-paired-results.json').read_text(encoding='utf8'))
row = next(r for r in data['rows'] if r['case'] == 'm4b_average' and r['arm'] == 'B' and not r['repeat'])
investigation = row['run']['investigation']
if investigation['status'] != 'completed' or investigation['outcome'] != 'LIKELY_CAUSE':
    raise RuntimeError('not eligible for approval')
fixtures.REGISTRY_PATH = ROOT / 'fixtures/repair/m4b-registry.json'
isolation = detect_isolation()
if isolation.mode != 'docker' or not isolation.available:
    raise RuntimeError('Docker required')
store = Store(str(ROOT / 'data/m4b-paired.db'))
hypothesis = investigation['findings']['hypotheses'][0]
approval = store.add_repair_approval(investigation['id'], 0, hypothesis_digest(hypothesis), investigation['evidence_hash'],
                                     'm4b-fixture-evaluation', 'Explicit benchmark approval for this one trusted fixture only.')
result = run_repair(store, ROOT, investigation['id'], 'm4b_average', Provider('ollama', 'qwen3.5:4b'), isolation=isolation)
output.write_text(json.dumps({'approval': approval, 'attempt': result}, indent=2, ensure_ascii=False), encoding='utf8')
print(result['status'], result.get('error'))
