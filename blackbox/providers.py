"""Provider adapters. No tools, repository writes, or commands are exposed to models."""
import json
import math
import os
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from urllib.parse import urlparse
import httpx
from .investigation_schema import Findings
from .m4b3_ledger import (
    MAX_RESPONSE_BYTES, DispatchPermit, DispatchResponseReceipt,
    LedgerBlocked, canonical_bytes, sha256_hex,
)


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
        """Investigation adapter: the Findings schema is fixed and is never caller-supplied."""
        return self.structured(prompt, Findings.model_json_schema())

    def structured(self, prompt: str, schema: dict, system: str | None = None,
                   max_output_tokens: int | None = None) -> ProviderResult:
        """One structured completion against a caller-supplied JSON schema.

        The schema is used for constrained decoding, so a patch proposal cannot be an unbounded or
        free-form instruction stream. No tool or command channel exists.
        """
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
            prediction_budget = min(max_output_tokens or MAX_OUTPUT_TOKENS, output_budget(prompt, context_length))
            messages = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': prompt}]
            response = httpx.post(url.rstrip('/') + '/api/chat', json={'model': self.model, 'stream': False, 'think': False, 'truncate': False, 'shift': False,
                'options': {'num_ctx': context_length, 'num_predict': prediction_budget, 'temperature': 0}, 'format': schema,
                'messages': messages}, timeout=timeout_seconds, follow_redirects=False, trust_env=False)
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
                config = types.GenerateContentConfig(response_mime_type='application/json',
                    response_json_schema=schema, max_output_tokens=max_output_tokens or 2048,
                    system_instruction=system)
                response = client.models.generate_content(model=self.model, contents=prompt, config=config)
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


class M4B3TransportPhase(str, Enum):
    PREPARED = 'PREPARED'
    SEND_ENTERED = 'SEND_ENTERED'
    RESPONSE_HEADERS = 'RESPONSE_HEADERS'
    BODY_COMPLETE = 'BODY_COMPLETE'


@dataclass(frozen=True)
class PreparedRequest:
    """Fully serialized local request; construction happens before ledger markers."""
    request: httpx.Request
    run_id: str
    evaluation_id: str
    attempt_id: str
    request_hash: str
    body_sha256: str
    config_sha256: str
    effective_options: dict
    endpoint: str


@dataclass(frozen=True)
class TransportOutcome:
    """Typed observation from the one transport entry; never a retry signal."""
    phase: M4B3TransportPhase
    dispatch_event_id: str
    request_hash: str
    transport_entered: bool
    response_received: bool
    response_body_complete: bool
    status_code: int | None = None
    raw_body: bytes | None = None
    safe_headers: dict | None = None
    transport_error_type: str | None = None
    transport_error: str | None = None
    response_receipt: DispatchResponseReceipt | None = None
    observed_response_bytes: int = 0
    retained_prefix_sha256: str | None = None
    declared_content_length: int | None = None


def _http_request_hash(request: httpx.Request) -> str:
    """Hash method, URL, non-secret headers and the exact already-serialized body."""
    headers = sorted((key.lower(), value) for key, value in request.headers.items())
    return sha256_hex(canonical_bytes({
        'method': request.method,
        'url': str(request.url),
        'headers': headers,
        'body_sha256': sha256_hex(request.content),
    }))


class M4B3OllamaDispatcher:
    """M4B.3-only one-way HTTP boundary requiring a ledger-issued permit.

    The milestone guard rejects Ollama's normal port. The only allowed endpoint
    is an explicit loopback test receiver; real inference remains disabled.
    """

    def __init__(
        self,
        run_id: str,
        *,
        endpoint: str,
        timeout_seconds: float = 60,
    ):
        self._initialize(run_id, endpoint=endpoint, timeout_seconds=timeout_seconds,
                         transport=None, checkpoint=None)

    @classmethod
    def _for_tests(
        cls, run_id: str, *, endpoint: str, timeout_seconds: float = 60,
        transport: httpx.BaseTransport | None = None,
        checkpoint: Callable[[str], None] | None = None,
    ) -> "M4B3OllamaDispatcher":
        """Private transport/checkpoint injection seam for isolated local tests."""
        instance = cls.__new__(cls)
        instance._initialize(run_id, endpoint=endpoint, timeout_seconds=timeout_seconds,
                             transport=transport, checkpoint=checkpoint)
        return instance

    def _initialize(
        self, run_id: str, *, endpoint: str, timeout_seconds: float,
        transport: httpx.BaseTransport | None, checkpoint: Callable[[str], None] | None,
    ) -> None:
        parsed = urlparse(endpoint)
        if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ProviderError('M4B.3 test receiver must be explicit loopback HTTP')
        if parsed.port == 11434:
            raise ProviderError('M4B.3 live execution is disabled; Ollama port 11434 is blocked')
        if not 1 <= timeout_seconds <= 600:
            raise ProviderError('M4B.3 timeout must be between 1 and 600 seconds')
        self.run_id = run_id
        self.endpoint = endpoint.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.checkpoint = checkpoint
        # Supplying a transport is reserved for tests; the default explicitly has
        # zero connection retries and the client never follows redirects/trusts env.
        self._transport = transport if transport is not None else httpx.HTTPTransport(retries=0)
        self._client = httpx.Client(
            transport=self._transport, timeout=timeout_seconds,
            follow_redirects=False, trust_env=False,
        )
        self._closed = False

    def prepare(
        self,
        *,
        evaluation_id: str,
        attempt_id: str,
        model: str,
        prompt: str,
        schema: dict,
        context_length: int = 2048,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
        model_digest: str | None = None,
    ) -> PreparedRequest:
        if self._closed:
            raise ProviderError('M4B.3 dispatcher is closed')
        if not 1024 <= context_length <= 32768:
            raise ProviderError('M4B.3 context length must be between 1024 and 32768')
        budget = min(max_output_tokens, output_budget(prompt, context_length))
        options = {
            'num_ctx': context_length,
            'num_predict': budget,
            'temperature': 0,
        }
        payload = {
            'model': model,
            'stream': False,
            'think': False,
            'truncate': False,
            'shift': False,
            'options': options,
            'format': schema,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        body = canonical_bytes(payload)
        url = self.endpoint + '/api/chat'
        headers = {
            'content-type': 'application/json',
            'accept-encoding': 'identity',
            'x-blackbox-run-id': self.run_id,
            'x-blackbox-evaluation-id': evaluation_id,
            'x-blackbox-attempt-id': attempt_id,
        }
        request = httpx.Request('POST', url, headers=headers, content=body)
        request_hash = _http_request_hash(request)
        config = {
            'model': model,
            'model_digest': model_digest,
            'context_length': context_length,
            'max_output_tokens': budget,
            'temperature': 0,
            'thinking': False,
            'timeout_seconds': self.timeout_seconds,
            'redirects': False,
            'retries': 0,
            'endpoint_class': 'loopback_fake_receiver',
        }
        return PreparedRequest(
            request=request, run_id=self.run_id, evaluation_id=evaluation_id,
            attempt_id=attempt_id, request_hash=request_hash,
            body_sha256=sha256_hex(body), config_sha256=sha256_hex(canonical_bytes(config)),
            effective_options={**options, 'model': model, 'output_limit': budget},
            endpoint=self.endpoint,
        )

    def send_prepared(self, prepared: PreparedRequest, permit: DispatchPermit) -> TransportOutcome:
        if self._closed:
            raise ProviderError('M4B.3 dispatcher is closed')
        if not isinstance(prepared, PreparedRequest) or not isinstance(permit, DispatchPermit):
            raise LedgerBlocked('M4B.3 dispatch requires PreparedRequest and ledger DispatchPermit')
        if prepared.endpoint != self.endpoint or str(prepared.request.url) != self.endpoint + '/api/chat':
            raise LedgerBlocked('prepared request endpoint does not belong to this dispatcher')
        if _http_request_hash(prepared.request) != prepared.request_hash:
            raise LedgerBlocked('prepared HTTP request changed after fingerprinting')
        if prepared.body_sha256 != sha256_hex(prepared.request.content):
            raise LedgerBlocked('prepared request body changed after fingerprinting')
        if prepared.run_id != self.run_id:
            raise LedgerBlocked('prepared request belongs to another run')
        # Snapshot the validated request so later changes to the caller-owned Request cannot
        # change the bytes or destination after permit validation.
        transport_request = httpx.Request(
            prepared.request.method, str(prepared.request.url),
            headers=list(prepared.request.headers.multi_items()),
            content=bytes(prepared.request.content),
        )
        if _http_request_hash(transport_request) != prepared.request_hash:
            raise LedgerBlocked('prepared HTTP request changed while creating the transport snapshot')
        if (str(transport_request.url) != self.endpoint + '/api/chat'
                or prepared.endpoint != self.endpoint):
            raise LedgerBlocked('prepared request endpoint does not belong to this dispatcher')
        transport_prepared = PreparedRequest(
            request=transport_request, run_id=prepared.run_id,
            evaluation_id=prepared.evaluation_id, attempt_id=prepared.attempt_id,
            request_hash=prepared.request_hash, body_sha256=prepared.body_sha256,
            config_sha256=prepared.config_sha256, effective_options=prepared.effective_options,
            endpoint=prepared.endpoint,
        )
        ledger = getattr(permit, '_ledger', None)
        if ledger is None or not callable(getattr(ledger, 'dispatch_lease', None)):
            raise LedgerBlocked('dispatch permit is not bound to an open ledger session')
        with ledger.dispatch_lease(transport_prepared, permit):
            phase = M4B3TransportPhase.PREPARED
            try:
                if self.checkpoint:
                    self.checkpoint('before_transport')
            except BaseException as exc:
                return TransportOutcome(
                    phase=phase, dispatch_event_id=permit.dispatch_event_id,
                    request_hash=prepared.request_hash, transport_entered=False,
                    response_received=False, response_body_complete=False,
                    transport_error_type=type(exc).__name__, transport_error=str(exc)[:300],
                )
            # Recheck path and process ownership after the injectable test barrier
            # and immediately before crossing into the network transport.
            ledger._assert_lock_owned()
            phase = M4B3TransportPhase.SEND_ENTERED
            if (_http_request_hash(transport_request) != prepared.request_hash
                    or sha256_hex(bytes(transport_request.content)) != prepared.body_sha256):
                raise LedgerBlocked('transport request changed after permit validation')
            try:
                response = self._client.send(transport_request, stream=True)
            except BaseException as exc:
                return TransportOutcome(
                    phase=phase, dispatch_event_id=permit.dispatch_event_id,
                    request_hash=prepared.request_hash, transport_entered=True,
                    response_received=False, response_body_complete=False,
                    transport_error_type=type(exc).__name__, transport_error=str(exc)[:300],
                )

            phase = M4B3TransportPhase.RESPONSE_HEADERS
            safe_names = ('content-type', 'content-length', 'content-encoding',
                          'x-request-id', 'x-ollama-version')
            safe_headers = {key: response.headers[key] for key in safe_names if key in response.headers}
            content_encoding = response.headers.get('content-encoding', '').strip().lower()
            if content_encoding not in ('', 'identity'):
                response.close()
                return TransportOutcome(
                    phase=phase, dispatch_event_id=permit.dispatch_event_id,
                    request_hash=prepared.request_hash, transport_entered=True,
                    response_received=True, response_body_complete=False,
                    status_code=response.status_code, raw_body=b'', safe_headers=safe_headers,
                    transport_error_type='UnexpectedContentEncoding',
                    transport_error='compressed provider responses are not accepted',
                    observed_response_bytes=0, retained_prefix_sha256=sha256_hex(b''),
                )
            length_text = response.headers.get('content-length')
            declared_length = None
            if length_text is not None:
                try:
                    declared_length = int(length_text)
                    if declared_length < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    response.close()
                    return TransportOutcome(
                        phase=phase, dispatch_event_id=permit.dispatch_event_id,
                        request_hash=prepared.request_hash, transport_entered=True,
                        response_received=True, response_body_complete=False,
                        status_code=response.status_code, raw_body=b'', safe_headers=safe_headers,
                        transport_error_type='InvalidContentLength',
                        transport_error='response Content-Length is invalid',
                        retained_prefix_sha256=sha256_hex(b''), declared_content_length=None,
                    )
                if declared_length > MAX_RESPONSE_BYTES:
                    response.close()
                    return TransportOutcome(
                        phase=phase, dispatch_event_id=permit.dispatch_event_id,
                        request_hash=prepared.request_hash, transport_entered=True,
                        response_received=True, response_body_complete=False,
                        status_code=response.status_code, raw_body=b'', safe_headers=safe_headers,
                        transport_error_type='ResponseTooLarge',
                        transport_error=f'response Content-Length exceeds {MAX_RESPONSE_BYTES} byte limit',
                        observed_response_bytes=0, retained_prefix_sha256=sha256_hex(b''),
                        declared_content_length=declared_length,
                    )

            # 1 MiB bounds both persisted diagnostic bytes and in-memory accumulation. It is
            # independent of the model's registered generation-token limit.
            prefix = bytearray()
            observed = 0
            error = None
            oversized = False
            try:
                # The raw iterator yields transport-sized chunks. The accumulator copies only
                # the first MAX_RESPONSE_BYTES even if a custom transport yields one huge item.
                # Without chunk_size HTTPX yields the underlying raw stream chunks
                # directly; adding a chunk size would buffer until a full chunk and
                # could discard a short prefix when the stream is interrupted.
                for chunk in response.iter_raw():
                    size = len(chunk)
                    observed += size
                    remaining = MAX_RESPONSE_BYTES - len(prefix)
                    if remaining > 0:
                        prefix.extend(memoryview(chunk)[:remaining])
                    if observed > MAX_RESPONSE_BYTES:
                        oversized = True
                        break
            except BaseException as exc:
                error = exc
            finally:
                response.close()

            body = bytes(prefix)
            prefix_hash = sha256_hex(body)
            if oversized:
                return TransportOutcome(
                    phase=phase, dispatch_event_id=permit.dispatch_event_id,
                    request_hash=prepared.request_hash, transport_entered=True,
                    response_received=True, response_body_complete=False,
                    status_code=response.status_code, raw_body=body, safe_headers=safe_headers,
                    transport_error_type='ResponseTooLarge',
                    transport_error=f'response exceeded {MAX_RESPONSE_BYTES} byte limit',
                    observed_response_bytes=observed, retained_prefix_sha256=prefix_hash,
                    declared_content_length=declared_length,
                )
            if error is not None:
                return TransportOutcome(
                    phase=phase, dispatch_event_id=permit.dispatch_event_id,
                    request_hash=prepared.request_hash, transport_entered=True,
                    response_received=True, response_body_complete=False,
                    status_code=response.status_code, raw_body=body, safe_headers=safe_headers,
                    transport_error_type=type(error).__name__, transport_error=str(error)[:300],
                    observed_response_bytes=observed, retained_prefix_sha256=prefix_hash,
                    declared_content_length=declared_length,
                )
            if declared_length is not None and declared_length != observed:
                return TransportOutcome(
                    phase=phase, dispatch_event_id=permit.dispatch_event_id,
                    request_hash=prepared.request_hash, transport_entered=True,
                    response_received=True, response_body_complete=False,
                    status_code=response.status_code, raw_body=body, safe_headers=safe_headers,
                    transport_error_type='ContentLengthMismatch',
                    transport_error='response body length differs from Content-Length',
                    observed_response_bytes=observed, retained_prefix_sha256=prefix_hash,
                    declared_content_length=declared_length,
                )

            receipt = ledger._register_response_receipt(
                permit, response.status_code, body, safe_headers,
            )
            outcome = TransportOutcome(
                phase=M4B3TransportPhase.BODY_COMPLETE, dispatch_event_id=permit.dispatch_event_id,
                request_hash=prepared.request_hash, transport_entered=True,
                response_received=True, response_body_complete=True,
                status_code=response.status_code, raw_body=body, safe_headers=safe_headers,
                response_receipt=receipt, observed_response_bytes=observed,
                retained_prefix_sha256=prefix_hash, declared_content_length=declared_length,
            )
            if self.checkpoint:
                try:
                    self.checkpoint('after_receiver_receipt')
                except BaseException as exc:
                    return TransportOutcome(
                        phase=outcome.phase, dispatch_event_id=outcome.dispatch_event_id,
                        request_hash=outcome.request_hash, transport_entered=True,
                        response_received=True, response_body_complete=True,
                        status_code=outcome.status_code, raw_body=outcome.raw_body,
                        safe_headers=outcome.safe_headers, response_receipt=outcome.response_receipt,
                        observed_response_bytes=observed, retained_prefix_sha256=prefix_hash,
                        declared_content_length=declared_length,
                        transport_error_type=type(exc).__name__, transport_error=str(exc)[:300],
                    )
            return outcome

    def close(self) -> None:
        if not self._closed:
            self._client.close()
            self._closed = True

    def __enter__(self):
        if self._closed:
            raise ProviderError('M4B.3 dispatcher is closed')
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
