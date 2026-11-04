"""Bounded, local-only streaming diagnostics; output is not an accuracy benchmark."""
import argparse
import json
import time
import httpx

parser = argparse.ArgumentParser()
parser.add_argument('model')
parser.add_argument('--format', choices=['text', 'json'], default='text')
parser.add_argument('--think', choices=['off', 'on'], default='off')
parser.add_argument('--timeout', type=int, default=45)
args = parser.parse_args()
schema = {'type': 'object', 'properties': {'result': {'type': 'string'}}, 'required': ['result']}
body = {'model': args.model, 'stream': True, 'think': args.think == 'on',
        'messages': [{'role': 'user', 'content': 'Say hello in one short sentence.' if args.format == 'text' else 'Return a JSON object with result set to hello.'}],
        'options': {'num_ctx': 2048, 'num_predict': 128, 'temperature': 0}, 'keep_alive': '5m'}
if args.format == 'json': body['format'] = schema
start = time.monotonic()
result = {'model': args.model, 'format': args.format, 'think': args.think, 'context': 2048,
          'max_output_tokens': 128, 'ttft_seconds': None, 'content_ttft_seconds': None,
          'status': 'unknown', 'json_valid': None, 'content': '', 'thinking_chars': 0}
try:
    with httpx.stream('POST', 'http://127.0.0.1:11434/api/chat', json=body, timeout=args.timeout, trust_env=False) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if time.monotonic() - start > args.timeout:
                raise TimeoutError('wall deadline')
            if not line: continue
            msg = json.loads(line)
            part = msg.get('message', {})
            if (part.get('thinking') or part.get('content')) and result['ttft_seconds'] is None:
                result['ttft_seconds'] = round(time.monotonic() - start, 3)
            if part.get('content') and result['content_ttft_seconds'] is None:
                result['content_ttft_seconds'] = round(time.monotonic() - start, 3)
            result['thinking_chars'] += len(part.get('thinking', ''))
            result['content'] += part.get('content', '')
            if msg.get('done'):
                for key in ('done_reason', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration', 'total_duration'):
                    result[key] = msg.get(key)
                result['tokens_per_second'] = round(msg.get('eval_count', 0) / (msg['eval_duration'] / 1e9), 2) if msg.get('eval_duration') else None
                result['status'] = 'completed'
                break
    if result['status'] == 'completed' and args.format == 'json':
        try:
            output = json.loads(result['content'])
            result['json_valid'] = isinstance(output, dict) and isinstance(output.get('result'), str)
        except json.JSONDecodeError:
            result['json_valid'] = False
except (httpx.HTTPError, TimeoutError) as exc:
    result['status'] = 'timeout' if isinstance(exc, (httpx.TimeoutException, TimeoutError)) else 'error'
    result['error_type'] = type(exc).__name__
result['wall_seconds'] = round(time.monotonic() - start, 3)
print(json.dumps(result, ensure_ascii=False), flush=True)
