"""One OpenAI-compatible provider adapter behind an explicit live gate.

No provider is configured by default and ``LIVE_INFERENCE_ENABLED`` remains
false. The adapter accepts only the model-visible packet, validates the returned
``InvestigationResult``, and never scores or approves a case. Tests use an
injected transport; this module does not read labels.
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from .errors import BDB5Error
from .models import CaseId, EvidencePacket, InvestigationResult
from .scoring import canonical_json, digest
from .spec import LIVE_INFERENCE_ENABLED
from .validation import validate_result_contract


MAX_CONTEXT_LENGTH = 1_048_576
DEFAULT_CONTEXT_LENGTH = 4_096
MAX_TIMEOUT_SECONDS = 1_800


class ProviderError(BDB5Error):
    """The provider call is disabled, misconfigured or returned invalid data."""


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 60.0
    max_output_tokens: int = 2_048
    protocol: Literal["openai", "ollama"] = "openai"
    context_length: int = DEFAULT_CONTEXT_LENGTH

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        base_url = os.environ.get("BLACKBOX_BDB5_PROVIDER_URL", "").strip()
        model = os.environ.get("BLACKBOX_BDB5_MODEL", "").strip()
        key = os.environ.get("BLACKBOX_BDB5_API_KEY", "").strip() or None
        protocol = os.environ.get("BLACKBOX_BDB5_PROTOCOL", "openai").strip().lower()
        if not base_url or not model:
            raise ProviderError(
                "provider not configured: set BLACKBOX_BDB5_PROVIDER_URL and BLACKBOX_BDB5_MODEL"
            )
        if protocol not in ("openai", "ollama"):
            raise ProviderError("BLACKBOX_BDB5_PROTOCOL must be 'openai' or 'ollama'")
        try:
            context_length = int(
                os.environ.get("BLACKBOX_BDB5_CONTEXT_LENGTH", str(DEFAULT_CONTEXT_LENGTH))
            )
            timeout_seconds = float(os.environ.get("BLACKBOX_BDB5_TIMEOUT_SECONDS", "60"))
        except ValueError as exc:
            raise ProviderError(
                "BLACKBOX_BDB5_CONTEXT_LENGTH and BLACKBOX_BDB5_TIMEOUT_SECONDS must be numeric"
            ) from exc
        return cls(
            base_url=base_url,
            model=model,
            api_key=key,
            protocol=protocol,
            context_length=context_length,
            timeout_seconds=timeout_seconds,
        )

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ProviderError("provider URL must be an absolute http(s) URL")
        if parsed.username or parsed.password:
            raise ProviderError("provider URL must not contain credentials")
        if self.timeout_seconds <= 0 or self.timeout_seconds > MAX_TIMEOUT_SECONDS:
            raise ProviderError(
                f"provider timeout must be between 0 and {MAX_TIMEOUT_SECONDS} seconds"
            )
        if not 128 <= self.max_output_tokens <= 32_768:
            raise ProviderError("provider output budget is outside the allowed range")
        if not 1_024 <= self.context_length <= MAX_CONTEXT_LENGTH:
            raise ProviderError(
                f"provider context length must be between 1024 and {MAX_CONTEXT_LENGTH}"
            )
        if self.protocol == "ollama":
            if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
                raise ProviderError("Ollama must use explicit loopback HTTP")
        if self.base_url.rstrip("/").endswith("/chat/completions"):
            raise ProviderError("provider URL must be the API base, not the chat endpoint")


@dataclass(frozen=True)
class LiveExecutionGate:
    """An explicit, scoped gate. The default is closed."""

    enabled: bool = False
    approval_hash: str | None = None
    case_id: str | None = None

    def require_open(self, case_id: str) -> None:
        if not LIVE_INFERENCE_ENABLED:
            raise ProviderError("live inference is disabled by LIVE_INFERENCE_ENABLED")
        if not self.enabled or not self.approval_hash:
            raise ProviderError("live provider calls require an open gate and approval hash")
        if self.case_id not in (None, case_id):
            raise ProviderError("gate belongs to a different case")


@dataclass(frozen=True)
class ProviderRun:
    case_id: str
    result: InvestigationResult
    request_hash: str
    response_hash: str
    usage: dict[str, Any]
    provider_calls: int = 1
    scored: bool = False
    approved: bool = False

    def payload(self) -> dict[str, Any]:
        return {
            "mode": "REAL_CASE_PROVIDER_ENVELOPE",
            "case_id": self.case_id,
            "status": "PROVIDER_RESULT_READY_FOR_REVIEW",
            "provider_calls": self.provider_calls,
            "scored": self.scored,
            "approved": self.approved,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash,
            "usage": self.usage,
            "result_hash": digest(self.result.model_dump(mode="json")),
            "model_visible_only": True,
        }


def provider_result_schema() -> dict[str, Any]:
    """Return the result schema with the abstention key always required.

    The model may still return ``null``. The provider contract rejects that
    when causation is not established. Requiring the key keeps it from
    disappearing entirely from a constrained JSON response.
    """
    schema = copy.deepcopy(InvestigationResult.model_json_schema())
    required = schema.setdefault("required", [])
    if "abstention" not in required:
        required.append("abstention")
    prop = schema.get("properties", {}).get("abstention")
    if isinstance(prop, dict):
        prop["description"] = (
            "Required in every response. Use a structured object when "
            "l2_causal_status is NOT_ESTABLISHED; otherwise null."
        )
    abstention_def = schema.get("$defs", {}).get("Abstention")
    if isinstance(abstention_def, dict):
        abstention_required = abstention_def.setdefault("required", [])
        for field in (
            "scope",
            "reason",
            "missing_evidence",
            "source_not_established",
            "application_source_not_established",
        ):
            if field not in abstention_required:
                abstention_required.append(field)
    return schema


def build_prompt(visible: dict[str, Any]) -> str:
    schema = provider_result_schema()
    return (
        "You are investigating one BDB-5 case. Use only the supplied evidence. "
        "Return one JSON object matching the InvestigationResult schema. Do not "
        "claim execution, tests, or runtime behavior unless the packet records it. "
        "Do not invent citations or source revisions.\n\n"
        "ABSTENTION CONTRACT:\n"
        "- If the evidence does not establish an application, service or source "
        "cause, set l2_causal_status to NOT_ESTABLISHED and fill the structured "
        "`abstention` object with scope, reason, missing_evidence, and the "
        "matching source_not_established or application_source_not_established "
        "flag.\n"
        "- Do not emit a SERVICE_CAUSE, SOURCE_CAUSE or "
        "APPLICATION_SOURCE_CAUSE claim for a cause the evidence does not "
        "establish; use an OBSERVATION or HARNESS_CAUSE claim instead.\n"
        "- Do not put an abstention only in a Claim. The top-level `abstention` "
        "field must be non-null when causation is not established.\n"
        "- If `abstention` is non-null, do not set l2_causal_status to "
        "SUPPORTED or ESTABLISHED.\n"
        "- Only include a TestExecution when the packet records it. A PASS "
        "requires an artifact_sha256. A REPRODUCTION_BEFORE or "
        "REPRODUCTION_AFTER execution also requires an artifact_sha256. If no "
        "artifact_sha256 is available for an execution, omit that TestExecution "
        "entirely; do not invent one.\n\n"
        "REQUIRED ABSTENTION SHAPE (when l2_causal_status is NOT_ESTABLISHED):\n"
        '  "abstention": {\n'
        '    "scope": "APPLICATION_SOURCE",\n'
        '    "reason": "The evidence does not establish an application-source cause.",\n'
        '    "missing_evidence": ["application stack trace"],\n'
        '    "source_not_established": false,\n'
        '    "application_source_not_established": true\n'
        "  }\n"
        "The `abstention` key is required in every response; use null only "
        "when l2_causal_status is not NOT_ESTABLISHED.\n\n"
        "INVESTIGATION RESULT SCHEMA:\n"
        + canonical_json(schema)
        + "\n\nMODEL-VISIBLE PACKET:\n"
        + canonical_json(visible)
    )


def _response_content(data: dict[str, Any]) -> str:
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("provider response has no choices[0].message.content") from exc
    if isinstance(content, list):
        text = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    else:
        text = content
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("provider returned empty content")
    return text


class OpenAICompatibleProvider:
    """A minimal no-tools chat-completions adapter.

    The caller must pass a ``LiveExecutionGate``. The default gate is closed, and
    the module-level switch must also be enabled. No approval record is created
    here; the gate's hash is only checked for presence.
    """

    def __init__(
        self,
        config: ProviderConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        client: httpx.Client | None = None,
    ):
        config.validate()
        self.config = config
        self._client = client or httpx.Client(
            transport=transport or httpx.HTTPTransport(retries=0),
            timeout=config.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def close(self) -> None:
        self._client.close()

    def respond(
        self,
        visible: dict[str, Any],
        *,
        gate: LiveExecutionGate | None = None,
    ) -> ProviderRun:
        packet = EvidencePacket.model_validate(visible)
        gate = gate or LiveExecutionGate()
        gate.require_open(packet.case_id.value)
        if gate.case_id is not None and gate.case_id != packet.case_id.value:
            raise ProviderError("gate case does not match the visible packet")

        prompt = build_prompt(visible)
        messages = [
            {
                "role": "system",
                "content": "Return only strict JSON. No tools, commands, or file access.",
            },
            {"role": "user", "content": prompt},
        ]
        if self.config.protocol == "ollama":
            body = {
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "format": provider_result_schema(),
                "options": {
                    "temperature": 0,
                    "num_ctx": self.config.context_length,
                    "num_predict": self.config.max_output_tokens,
                },
            }
            url = self.config.base_url.rstrip("/") + "/api/chat"
        else:
            body = {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": self.config.max_output_tokens,
                "response_format": {"type": "json_object"},
                "stream": False,
            }
            url = self.config.base_url.rstrip("/") + "/chat/completions"
        body_bytes = canonical_json(body).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "authorization": f"Bearer {self.config.api_key}" if self.config.api_key else "",
        }
        if not headers["authorization"]:
            headers.pop("authorization")
        request = self._client.build_request("POST", url, content=body_bytes, headers=headers)
        request_hash = digest({
            "url": str(request.url),
            "body": body_bytes.decode("utf-8"),
            "headers": sorted(request.headers.items()),
        })
        try:
            response = self._client.send(request)
        except httpx.HTTPError as exc:
            raise ProviderError(f"provider transport failed: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise ProviderError(f"provider returned HTTP {response.status_code}")
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ProviderError("provider returned non-JSON data") from exc
        if not isinstance(data, dict):
            raise ProviderError("provider response root must be an object")
        if self.config.protocol == "ollama":
            message = data.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ProviderError("Ollama response has no final message content")
            content = message["content"]
            usage = {
                "input_tokens": data.get("prompt_eval_count"),
                "output_tokens": data.get("eval_count"),
                "estimated_cost": None,
            }
            if data.get("done_reason") == "length":
                raise ProviderError("Ollama output reached the token limit")
        else:
            content = _response_content(data)
            usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        try:
            raw_result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("provider content is not a JSON object") from exc
        try:
            result = InvestigationResult.model_validate(raw_result)
        except Exception as exc:
            raise ProviderError(f"provider result failed schema validation: {exc}") from exc
        if result.case_id != packet.case_id:
            raise ProviderError("provider result case_id does not match the packet")
        contract = validate_result_contract(result)
        if not contract.passed:
            details = "; ".join(item.detail for item in contract.errors)
            raise ProviderError(f"provider result violates abstention contract: {details}")
        return ProviderRun(
            case_id=result.case_id.value,
            result=result,
            request_hash=request_hash,
            response_hash=digest(raw_result),
            usage=usage,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


__all__ = [
    "DEFAULT_CONTEXT_LENGTH",
    "LiveExecutionGate",
    "MAX_CONTEXT_LENGTH",
    "MAX_TIMEOUT_SECONDS",
    "OpenAICompatibleProvider",
    "ProviderConfig",
    "ProviderError",
    "ProviderRun",
    "build_prompt",
    "provider_result_schema",
]
