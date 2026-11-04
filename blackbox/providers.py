"""Provider adapters. No tools, repository writes, or commands are exposed to models."""
import json
import math
import os
from dataclasses import dataclass
from urllib.parse import urlparse
import httpx
from .investigation_schema import Findings


class ProviderError(Exception):
    def __init__(self, message: str, usage: dict | None = None):
        super().__init__(message)
        self.usage = usage


# The measured 768-token cap is kept for small prompts, but a large evidence prompt must leave room
# for a complete JSON object inside the fixed context window. No context increase is assumed.
MAX_OUTPUT_TOKENS = 768
MIN_OUTPUT_TOKENS = 320
CONTEXT_RESERVE_TOKENS = 64
PROMPT_CHARS_PER_TOKEN = 3.5


def output_budget(prompt: str, context_length: int) -> int:
    """Output tokens that fit after a deliberately conservative estimate of the prompt.

    The estimate over-counts tokens (3.5 characters per token against the measured 3.9-5.4 for
    these prompts) so generation is not cut off. Evidence is never dropped: when even the minimum
    useful output cannot fit, this raises a clear error instead of truncating the prompt.
    """
    estimated_prompt = math.ceil(len(prompt) / PROMPT_CHARS_PER_TOKEN)
    available = context_length - estimated_prompt - CONTEXT_RESERVE_TOKENS
    if available < MIN_OUTPUT_TOKENS:
        raise ProviderError('Evidence prompt does not fit safely in the configured context window; '
                            'raise BLACKBOX_OLLAMA_CONTEXT_LENGTH or reduce the frame evidence.')
    return min(MAX_OUTPUT_TOKENS, available)


@dataclass
class ProviderResult:
    text: str
    usage: dict


class Provider:
    def __init__(self, name: str, model: str, api_key: str | None = None):
        self.name, self.model, self.api_key = name, model, api_key

    def analyze(self, prompt: str) -> ProviderResult:
        if self.name == 'ollama':
            url = os.environ.get('BLACKBOX_OLLAMA_URL', 'http://127.0.0.1:11434')
            parsed = urlparse(url)
            if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1') or parsed.username or parsed.password:
                raise ProviderError('Ollama endpoint must be local HTTP')
            raw_context = os.environ.get('BLACKBOX_OLLAMA_CONTEXT_LENGTH', '2048')
            try:
                context_length = int(raw_context)
                if not 1024 <= context_length <= 32768:
                    raise ValueError
            except ValueError as exc:
                raise ProviderError('BLACKBOX_OLLAMA_CONTEXT_LENGTH must be between 1024 and 32768') from exc
            try:
                timeout_seconds = int(os.environ.get('BLACKBOX_OLLAMA_TIMEOUT_SECONDS', '60'))
                if not 1 <= timeout_seconds <= 600:
                    raise ValueError
            except ValueError as exc:
                raise ProviderError('BLACKBOX_OLLAMA_TIMEOUT_SECONDS must be between 1 and 600') from exc
            prediction_budget = output_budget(prompt, context_length)
            response = httpx.post(url.rstrip('/') + '/api/chat', json={'model': self.model, 'stream': False, 'think': False, 'truncate': False, 'shift': False,
                'options': {'num_ctx': context_length, 'num_predict': prediction_budget, 'temperature': 0}, 'format': Findings.model_json_schema(),
                'messages': [{'role': 'user', 'content': prompt}]}, timeout=timeout_seconds, follow_redirects=False, trust_env=False)
            response.raise_for_status()
            data = response.json()
            if data.get('done_reason') == 'length':
                raise ProviderError('Model output reached the token limit; no complete result returned',
                                    {'input_tokens': data.get('prompt_eval_count'), 'output_tokens': data.get('eval_count'),
                                     'output_limit': prediction_budget, 'estimated_cost': None})
            if not data.get('message', {}).get('content'):
                raise ProviderError('Model returned no final content')
            return ProviderResult(data['message']['content'], {'input_tokens': data.get('prompt_eval_count'), 'output_tokens': data.get('eval_count'), 'load_duration_ns': data.get('load_duration'), 'eval_duration_ns': data.get('eval_duration'), 'estimated_cost': None})
        if self.name == 'gemini':
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise ProviderError('Install google-genai to use Gemini') from exc
            client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=60000, retry_options=types.HttpRetryOptions(attempts=1)))
            try:
                response = client.models.generate_content(model=self.model, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type='application/json', response_json_schema=Findings.model_json_schema(), max_output_tokens=2048))
                usage = response.usage_metadata
                return ProviderResult(response.text or '', {'input_tokens': getattr(usage, 'prompt_token_count', None), 'output_tokens': getattr(usage, 'candidates_token_count', None), 'estimated_cost': None})
            finally:
                client.close()
        raise ProviderError('AI provider not configured')


def configured_provider() -> Provider:
    name = os.environ.get('BLACKBOX_AI_PROVIDER', '').lower()
    model = os.environ.get('BLACKBOX_AI_MODEL', '').strip()
    if name not in ('gemini', 'ollama') or not model:
        raise ProviderError('AI provider not configured: set BLACKBOX_AI_PROVIDER and BLACKBOX_AI_MODEL')
    key = os.environ.get('GEMINI_API_KEY') if name == 'gemini' else None
    if name == 'gemini' and not key:
        raise ProviderError('AI provider not configured: GEMINI_API_KEY is missing')
    return Provider(name, model, key)
