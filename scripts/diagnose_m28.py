"""Local diagnostic: show raw model output and the exact validation failure.

Nothing is persisted. Use only with a local Ollama model; the synthetic
evidence in the evaluation database contains no production data.
"""
import argparse
import json
import sys
from pathlib import Path

import httpx
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blackbox.investigator import SYSTEM, collect, normalize_abstention, validate
from blackbox.investigation_schema import Findings
from blackbox.providers import Provider, ProviderError
from blackbox.store import Store

parser = argparse.ArgumentParser(description='Diagnose one investigation without persisting output')
parser.add_argument('incident', type=int)
parser.add_argument('--db', default='data/milestone27-evaluation.db')
parser.add_argument('--repo', default='sample_repo')
parser.add_argument('--model', default='qwen3.5:4b')
args = parser.parse_args()

snapshot = collect(Store(args.db), Path(args.repo).resolve(), args.incident)
serialized = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
provider = Provider('ollama', args.model)
report = {'incident': args.incident, 'model': args.model}
try:
    response = provider.analyze(SYSTEM + '\nUNTRUSTED EVIDENCE JSON:\n' + serialized)
    report['usage'] = response.usage
    report['raw'] = response.text
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raw = json.loads(response.text)
    normalized = normalize_abstention(raw, snapshot)
    print('--- normalized keys changed:', sorted(set(normalized) ^ set(raw)))
    try:
        findings = Findings.model_validate(normalized)
    except ValidationError as exc:
        print('SCHEMA INVALID:', exc.errors(include_url=False))
        raise SystemExit(0)
    print('SCHEMA VALID: outcome =', findings.outcome)
    try:
        validate(findings, snapshot)
    except ValueError as exc:
        print('EVIDENCE INVALID:', exc)
    else:
        print('EVIDENCE VALID')
except (ProviderError, httpx.HTTPError, json.JSONDecodeError) as exc:
    report['provider_error'] = f'{type(exc).__name__}: {exc}'
    print(json.dumps(report, indent=2, ensure_ascii=False))
