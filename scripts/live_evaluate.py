"""Evaluate one configured real-model run; human scoring intentionally left unknown."""
import argparse
import json
import time
from investigate import request

parser = argparse.ArgumentParser(description='Run one real-model evaluation against a stored incident')
parser.add_argument('incident', type=int)
parser.add_argument('--consent-external-hash', help='Previously reviewed preview hash (required for Gemini)')
args = parser.parse_args()
started = time.monotonic()
result = request(f'/incidents/{args.incident}/investigations', {
    'force': True, 'consent_external': bool(args.consent_external_hash),
    'reviewed_evidence_hash': args.consent_external_hash})
run = result['investigation']
print(json.dumps({'investigation_id': run['id'], 'status': run['status'],
    'provider': run['provider'], 'model': run['model'], 'latency_ms': run['latency_ms'],
    'client_latency_ms': int((time.monotonic()-started)*1000), 'usage': run['usage'],
    'evidence_reference_validation': 'passed structural checks' if run['status'] == 'completed' else 'not passed',
    'diagnosis_correctness': 'not scored; requires independently labeled case and human adjudication',
    'unsupported_claims': 'not scored; requires human adjudication',
    'abstention_correctness': 'not scored; requires human adjudication',
    'estimated_cost': 'unknown unless measured independently'}, indent=2))
