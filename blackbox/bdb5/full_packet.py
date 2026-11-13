"""Explicit full-packet BDB-5 provider run.

This path is separate from the closed live gate used by the default provider
adapter. It requires ``allow_live=True`` from the caller, validates the same
approved packet, and refuses to use a bounded projection. No label vault data is
added to the prompt.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from .approval import ApprovalRecord, validate_approval
from .errors import BDB5Error
from .label_vault import LabelVault
from .models import (
    CaseManifest,
    EvidencePacket,
    InvestigationResult,
)
from .provider import (
    ProviderConfig,
    build_prompt,
    provider_result_schema,
)
from .review import review_payload
from .scoring import canonical_json, digest
from .validation import validate_result_contract


class FullPacketError(BDB5Error):
    """The full-packet request is unauthorised, too large, or invalid."""


@dataclass(frozen=True)
class FullPacketRun:
    case_id: str
    result: InvestigationResult
    request_hash: str
    response_hash: str
    usage: dict[str, Any]
    prompt_chars: int
    prompt_tokens_preflight: int | None
    provider_input_tokens: int | None
    fit_preflight: str
    fit_provider: str
    token_count_source: str
    context_length: int
    max_output_tokens: int
    packet_sha256: str
    approval_hash: str
    provider_calls: int = 1
    scored: bool = False
    approved: bool = False

    def payload(self) -> dict[str, Any]:
        return {
            "mode": "REAL_CASE_FULL_PACKET_PROVIDER_RUN",
            "case_id": self.case_id,
            "status": "FULL_PACKET_RESULT_READY_FOR_REVIEW",
            "context_mode": "FULL_PACKET",
            "projection_used": False,
            "truncated": False,
            "provider_calls": self.provider_calls,
            "scored": self.scored,
            "approved": self.approved,
            "approval_hash": self.approval_hash,
            "packet_sha256": self.packet_sha256,
            "prompt_chars": self.prompt_chars,
            "prompt_tokens_preflight": self.prompt_tokens_preflight,
            "provider_input_tokens": self.provider_input_tokens,
            "fit_preflight": self.fit_preflight,
            "fit_provider": self.fit_provider,
            "token_count_source": self.token_count_source,
            "context_length": self.context_length,
            "max_output_tokens": self.max_output_tokens,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash,
            "usage": self.usage,
            "result_hash": digest(self.result.model_dump(mode="json")),
            "model_visible_only": True,
        }


def _content(data: dict[str, Any], protocol: str) -> str:
    if protocol == "ollama":
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise FullPacketError("Ollama response has no final message content")
        text = message["content"]
    else:
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise FullPacketError("provider response has no choices[0].message.content") from exc
        if isinstance(content, list):
            text = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        else:
            text = content
    if not isinstance(text, str) or not text.strip():
        raise FullPacketError("provider returned empty content")
    return text


def _usage(data: dict[str, Any], protocol: str) -> dict[str, Any]:
    if protocol == "ollama":
        return {
            "input_tokens": data.get("prompt_eval_count"),
            "output_tokens": data.get("eval_count"),
            "estimated_cost": None,
        }
    return data.get("usage") if isinstance(data.get("usage"), dict) else {}


def _provider_input_tokens(data: dict[str, Any], protocol: str) -> int | None:
    usage = _usage(data, protocol)
    for key in ("input_tokens", "prompt_tokens"):
        value = usage.get(key)
        if isinstance(value, int) and value >= 0:
            return value
    return None


def _finish_reason(data: dict[str, Any], protocol: str) -> str | None:
    if protocol == "ollama":
        return data.get("done_reason")
    try:
        return data["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError):
        return None


class FullPacketRunner:
    """Send the complete model-visible packet in one request.

    The caller must explicitly pass ``allow_live=True``. The repository-wide
    ``LIVE_INFERENCE_ENABLED`` switch is intentionally not changed by this class.
    """

    def __init__(
        self,
        config: ProviderConfig,
        *,
        transport: httpx.BaseTransport | None = None,
        client: httpx.Client | None = None,
        response_format: bool = True,
        reasoning_effort: str | None = None,
    ):
        config.validate()
        self.config = config
        self.response_format = response_format
        self.reasoning_effort = reasoning_effort
        self._client = client or httpx.Client(
            transport=transport or httpx.HTTPTransport(retries=0),
            timeout=config.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )

    def close(self) -> None:
        self._client.close()

    def run(
        self,
        payload: dict[str, Any],
        *,
        approval: ApprovalRecord,
        vault: LabelVault,
        allow_live: bool = False,
        max_output_tokens: int | None = None,
        prompt_tokens_preflight: int | None = None,
        registry: dict[str, Any] | None = None,
    ) -> FullPacketRun:
        if not allow_live:
            raise FullPacketError(
                "full-packet live call requires allow_live=True; no request was sent"
            )

        review = review_payload(payload, registry)
        if not review.passed:
            raise FullPacketError(
                "prepared payload failed review: " + "; ".join(review.issues)
            )
        validate_approval(approval, payload, vault)

        manifest = CaseManifest.model_validate(payload["evaluator_only"]["manifest"])
        packet = EvidencePacket.model_validate(payload["model_visible_packet"])
        visible = packet.model_visible_payload()
        packet_hash = digest(visible)
        if packet_hash != approval.packet_sha256:
            raise FullPacketError("approval packet hash does not match the full packet")

        prompt = build_prompt(visible)
        output_tokens = max_output_tokens or self.config.max_output_tokens
        if prompt_tokens_preflight is not None:
            if prompt_tokens_preflight <= 0:
                raise FullPacketError("exact preflight token count must be positive")
            if prompt_tokens_preflight + output_tokens + 4_096 > self.config.context_length:
                raise FullPacketError(
                    "full packet does not fit the configured context: "
                    f"exact_prompt={prompt_tokens_preflight}, output={output_tokens}, "
                    f"context={self.config.context_length}"
                )
            fit_preflight = "PASSED_EXACT"
            token_count_source = "EXACT_PREFLIGHT"
        else:
            fit_preflight = "NOT_CHECKED"
            token_count_source = "PROVIDER_USAGE_PENDING"

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
                    "num_predict": output_tokens,
                },
            }
            url = self.config.base_url.rstrip("/") + "/api/chat"
        else:
            body = {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": output_tokens,
                "stream": False,
            }
            if self.response_format:
                body["response_format"] = {"type": "json_object"}
            if self.reasoning_effort:
                body["reasoning"] = {"effort": self.reasoning_effort}
            url = self.config.base_url.rstrip("/") + "/chat/completions"

        body_bytes = canonical_json(body).encode("utf-8")
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
        if self.config.api_key:
            headers["authorization"] = f"Bearer {self.config.api_key}"
        request = self._client.build_request("POST", url, content=body_bytes, headers=headers)
        request_hash = digest(
            {
                "url": str(request.url),
                "body": body_bytes.decode("utf-8"),
                "headers": sorted(request.headers.items()),
            }
        )
        try:
            response = self._client.send(request)
        except httpx.HTTPError as exc:
            raise FullPacketError(
                f"full-packet provider transport failed: {type(exc).__name__}"
            ) from exc
        if response.status_code >= 400:
            raise FullPacketError(f"provider returned HTTP {response.status_code}")
        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise FullPacketError("provider returned non-JSON data") from exc
        if not isinstance(data, dict):
            raise FullPacketError("provider response root must be an object")

        finish = _finish_reason(data, self.config.protocol)
        if finish == "length":
            raise FullPacketError("provider output reached the token limit")
        provider_input_tokens = _provider_input_tokens(data, self.config.protocol)
        if provider_input_tokens is not None:
            fit_provider = (
                "PASSED"
                if provider_input_tokens + output_tokens <= self.config.context_length
                else "FAILED"
            )
            if fit_provider == "FAILED":
                raise FullPacketError(
                    "provider-reported prompt tokens exceed the configured context: "
                    f"provider_input={provider_input_tokens}, output={output_tokens}, "
                    f"context={self.config.context_length}"
                )
            token_count_source = (
                "EXACT_PREFLIGHT_AND_PROVIDER_USAGE"
                if prompt_tokens_preflight is not None
                else "PROVIDER_USAGE"
            )
        else:
            fit_provider = "UNVERIFIED"
            if prompt_tokens_preflight is None:
                token_count_source = "UNAVAILABLE"
        content = _content(data, self.config.protocol)
        try:
            raw_result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise FullPacketError("provider content is not a JSON object") from exc
        try:
            result = InvestigationResult.model_validate(raw_result)
        except Exception as exc:
            raise FullPacketError(f"provider result failed schema validation: {exc}") from exc
        if result.case_id != manifest.case_id:
            raise FullPacketError("provider result case_id does not match the packet")
        contract = validate_result_contract(result)
        if not contract.passed:
            details = "; ".join(item.detail for item in contract.errors)
            raise FullPacketError(f"provider result violates abstention contract: {details}")

        return FullPacketRun(
            case_id=result.case_id.value,
            result=result,
            request_hash=request_hash,
            response_hash=digest(raw_result),
            usage=_usage(data, self.config.protocol),
            prompt_chars=len(prompt),
            prompt_tokens_preflight=prompt_tokens_preflight,
            provider_input_tokens=provider_input_tokens,
            fit_preflight=fit_preflight,
            fit_provider=fit_provider,
            token_count_source=token_count_source,
            context_length=self.config.context_length,
            max_output_tokens=output_tokens,
            packet_sha256=packet_hash,
            approval_hash=approval.approval_hash,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


__all__ = [
    "FullPacketError",
    "FullPacketRun",
    "FullPacketRunner",
]
