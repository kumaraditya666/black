"""Run a bounded streaming diagnostic against a stored incident and validate evidence."""
import argparse
import json
import sys
import time
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blackbox.investigator import SYSTEM, collect, validate
from blackbox.investigation_schema import Findings
from blackbox.store import Store

parser = argparse.ArgumentParser()
parser.add_argument('model')
parser.add_argument('--timeout', type=int, default=90)
args = parser.parse_args()
snapshot = collect(Store('data/events.db'), Path('sample_repo').resolve(), 1)
serialized = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
body = {'model': args.model, 'stream': True, 'think': False, 'format': Findings.model_json_schema(),
        'options': {'num_ctx': 2048, 'num_predict': 768, 'temperature': 0},
        'messages': [{'role': 'user', 'content': SYSTEM + '\nUNTRUSTED EVIDENCE JSON:\n' + serialized}]}
result = {'model': args.model, 'context': 2048, 'max_output_tokens': 768, 'think': False,
          'ttft_seconds': None, 'content': '', 'status': 'incomplete', 'schema_valid': False, 'evidence_valid': False}
start = time.monotonic()
try:
    with httpx.stream('POST', 'http://127.0.0.1:11434/api/chat', json=body, timeout=args.timeout, trust_env=False) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if time.monotonic() - start > args.timeout: raise TimeoutError('wall deadline')
            if not line: continue
            data = json.loads(line)
            content = data.get('message', {}).get('content', '')
            if content and result['ttft_seconds'] is None: result['ttft_seconds'] = round(time.monotonic()-start, 3)
            result['content'] += content
            if data.get('done'):
                for key in ('done_reason', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration'):
                    result[key] = data.get(key)
                result['tokens_per_second'] = round(data.get('eval_count', 0)/(data['eval_duration']/1e9), 2) if data.get('eval_duration') else None
                result['status'] = 'completed'
                break
    findings = Findings.model_validate_json(result['content'])
    result['schema_valid'] = True
    validate(findings, snapshot)
    result['evidence_valid'] = True
except Exception as exc:
    result['error_type'] = type(exc).__name__
    result['error'] = str(exc)[:500]
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)): result['status'] = 'timeout'
result['wall_seconds'] = round(time.monotonic()-start, 3)
print(json.dumps(result, ensure_ascii=False), flush=True)
