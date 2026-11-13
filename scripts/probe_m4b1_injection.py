"""Separately registered, forced-source hostile-comment probe; not a primary arm."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blackbox.agent_retrieval import Dispatcher, investigate_with_retrieval
from blackbox.providers import Provider
from blackbox.repair import fixtures
from blackbox.store import Store

OUT = ROOT / 'data/m4b1-injection-probe.json'
if OUT.exists():
    raise RuntimeError('refuse overwrite')
fixtures.REGISTRY_PATH = ROOT / 'fixtures/repair/m4b1-registry.json'
data = json.loads((ROOT / 'data/m4b1-results.json').read_text(encoding='utf8'))
row = next(x for x in data['rows'] if x['case'] == 'm4b1_injected' and x['arm'] == 'C')
investigation = row['run']['investigation']
snapshot = copy.deepcopy(investigation['evidence'])
dispatcher = Dispatcher(ROOT, data['revision'], fixtures.get_fixture('m4b1_injected'))
excerpt = dispatcher.dispatch({'action': 'read_source', 'path': 'fixtures/repair/m4b1_injected/helper.py',
                               'start': 4, 'end': 6, 'reason': 'hostile source probe'})
snapshot['evidence'].append(excerpt)
store = Store(str(ROOT / 'data/m4b1.db'))
result = investigate_with_retrieval(store, ROOT, investigation['incident_id'], 'm4b1_injected',
                                    Provider('ollama', 'qwen3.5:4b'), snapshot=snapshot,
                                    prompt_version='v2', deadline_seconds=180)
OUT.write_text(json.dumps({'probe': 'forced hostile source, not natural selection', 'run': result}, indent=2, ensure_ascii=False), encoding='utf8')
print(result['status'], result.get('reason'))
