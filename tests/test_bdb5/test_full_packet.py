from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from blackbox.bdb5.approval import load_approval
from blackbox.bdb5.full_packet import FullPacketError, FullPacketRunner
from blackbox.bdb5.label_vault import load_label_vault
from blackbox.bdb5.models import (
    Abstention,
    AbstentionScope,
    CaseId,
    CausalStatus,
    InvestigationResult,
)
from blackbox.bdb5.provider import MAX_CONTEXT_LENGTH, ProviderConfig

ROOT = Path(__file__).resolve().parents[2]
PREPARED = ROOT / "data" / "bdb5_t1" / "bdb5_t1_prepared.json"
APPROVAL = ROOT / "data" / "bdb5_t1" / "approvals" / "BDB5-T1-approval.json"
VAULT = ROOT / "fixtures" / "bdb5" / "labels" / "t1_label_vault.json"


def _result_json() -> dict:
    return InvestigationResult(
        case_id=CaseId.T1,
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.SOURCE,
            reason="The supplied evidence does not establish a source-level cause.",
            missing_evidence=("runtime source map or stack trace",),
            source_not_established=True,
        ),
    ).model_dump(mode="json")


def _fixtures() -> tuple[dict, object, object]:
    return (
        json.loads(PREPARED.read_text(encoding="utf-8")),
        load_approval(APPROVAL),
        load_label_vault(VAULT),
    )


def test_full_packet_refuses_without_explicit_live_opt_in():
    called = False

    def handler(_request: httpx.Request):
        nonlocal called
        called = True
        return httpx.Response(500)

    payload, approval, vault = _fixtures()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    runner = FullPacketRunner(
        ProviderConfig(
            base_url="https://provider.test/v1",
            model="test-model",
            context_length=MAX_CONTEXT_LENGTH,
        ),
        client=client,
    )
    with pytest.raises(FullPacketError, match="allow_live"):
        runner.run(payload, approval=approval, vault=vault, allow_live=False)
    runner.close()
    assert called is False


def test_full_packet_sends_complete_packet_and_records_no_projection():
    captured: dict = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": json.dumps(_result_json())},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 612_000, "completion_tokens": 200},
        })

    payload, approval, vault = _fixtures()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with FullPacketRunner(
        ProviderConfig(
            base_url="https://provider.test/v1",
            model="test-model",
            context_length=MAX_CONTEXT_LENGTH,
        ),
        client=client,
    ) as runner:
        run = runner.run(
            payload,
            approval=approval,
            vault=vault,
            allow_live=True,
            prompt_tokens_preflight=620_000,
        )

    prompt = captured["body"]["messages"][1]["content"]
    assert "MODEL-VISIBLE PACKET:" in prompt
    assert "metric:1" in prompt
    assert "evaluator_only" not in prompt
    assert captured["body"]["max_tokens"] == 2_048
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert run.provider_calls == 1
    assert run.scored is False
    assert run.approved is False
    assert run.packet_sha256 == approval.packet_sha256
    assert run.prompt_chars > 1_000_000
    assert run.prompt_tokens_preflight == 620_000
    assert run.provider_input_tokens == 612_000
    assert run.fit_preflight == "PASSED_EXACT"
    assert run.fit_provider == "PASSED"
    assert run.token_count_source == "EXACT_PREFLIGHT_AND_PROVIDER_USAGE"
    record = run.payload()
    assert record["context_mode"] == "FULL_PACKET"
    assert record["projection_used"] is False
    assert record["truncated"] is False
    assert record["approval_hash"] == approval.approval_hash
    assert record["usage"]["prompt_tokens"] == 612_000
    assert "prompt_tokens_estimated" not in record


def test_full_packet_without_exact_count_does_not_claim_preflight_fit():
    def handler(_request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": json.dumps(_result_json())},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 612_000, "completion_tokens": 200},
        })

    payload, approval, vault = _fixtures()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with FullPacketRunner(
        ProviderConfig(
            base_url="https://provider.test/v1",
            model="test-model",
            context_length=MAX_CONTEXT_LENGTH,
        ),
        client=client,
    ) as runner:
        run = runner.run(payload, approval=approval, vault=vault, allow_live=True)

    assert run.prompt_tokens_preflight is None
    assert run.fit_preflight == "NOT_CHECKED"
    assert run.provider_input_tokens == 612_000
    assert run.fit_provider == "PASSED"
    assert run.token_count_source == "PROVIDER_USAGE"
    assert run.payload()["fit_preflight"] == "NOT_CHECKED"


def test_full_packet_without_provider_usage_marks_token_count_unavailable():
    def handler(_request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": json.dumps(_result_json())},
                "finish_reason": "stop",
            }],
        })

    payload, approval, vault = _fixtures()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with FullPacketRunner(
        ProviderConfig(
            base_url="https://provider.test/v1",
            model="test-model",
            context_length=MAX_CONTEXT_LENGTH,
        ),
        client=client,
    ) as runner:
        run = runner.run(payload, approval=approval, vault=vault, allow_live=True)

    assert run.provider_input_tokens is None
    assert run.fit_provider == "UNVERIFIED"
    assert run.token_count_source == "UNAVAILABLE"


def test_full_packet_openrouter_free_mode_omits_response_format_and_disables_reasoning():
    captured: dict = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": json.dumps(_result_json())},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 612_000, "completion_tokens": 200},
        })

    payload, approval, vault = _fixtures()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with FullPacketRunner(
        ProviderConfig(
            base_url="https://openrouter.ai/api/v1",
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            context_length=1_000_000,
        ),
        client=client,
        response_format=False,
        reasoning_effort="none",
    ) as runner:
        run = runner.run(payload, approval=approval, vault=vault, allow_live=True)

    assert "response_format" not in captured["body"]
    assert captured["body"]["reasoning"] == {"effort": "none"}
    assert run.fit_preflight == "NOT_CHECKED"
    assert run.fit_provider == "PASSED"


def test_full_packet_rejects_oversized_prompt_before_transport():
    called = False

    def handler(_request: httpx.Request):
        nonlocal called
        called = True
        return httpx.Response(500)

    payload, approval, vault = _fixtures()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with FullPacketRunner(
        ProviderConfig(
            base_url="https://provider.test/v1",
            model="test-model",
            context_length=MAX_CONTEXT_LENGTH,
        ),
        client=client,
    ) as runner:
        with pytest.raises(FullPacketError, match="does not fit"):
            runner.run(
                payload,
                approval=approval,
                vault=vault,
                allow_live=True,
                prompt_tokens_preflight=MAX_CONTEXT_LENGTH,
            )
    assert called is False
