from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from blackbox.bdb5.models import (
    Abstention,
    AbstentionScope,
    CaseId,
    CausalStatus,
    Claim,
    ClaimCategory,
    InvestigationResult,
    TestExecution,
    TestOutcome,
    TestRole,
)
from blackbox.bdb5.provider import (
    MAX_CONTEXT_LENGTH,
    LiveExecutionGate,
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderError,
    provider_result_schema,
)
from blackbox.bdb5.real_cases import R2, prepare_ci_case
from blackbox.bdb5.validation import validate_result_contract

ROOT = Path(__file__).resolve().parents[2]
R2_LOG = ROOT / "fixtures" / "bdb5" / "bugswarm" / "83523531.log"


def _visible():
    return prepare_ci_case(R2_LOG.read_text(encoding="utf-8"), R2).packet.model_visible_payload()


def _result_json():
    return InvestigationResult(
        case_id=CaseId.R2,
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.APPLICATION_SOURCE,
            reason="The supplied evidence does not establish an application-source cause.",
            missing_evidence=("application stack trace",),
            application_source_not_established=True,
        ),
    ).model_dump(mode="json")


def _bad_causal_result_json():
    return InvestigationResult(
        case_id=CaseId.R2,
        claims=(
            Claim(
                category=ClaimCategory.SERVICE_CAUSE,
                text="The service caused the failure.",
            ),
        ),
        l2_causal_status=CausalStatus.NOT_ASSESSED,
    ).model_dump(mode="json")


def _bad_not_established_result_json():
    return InvestigationResult(
        case_id=CaseId.R2,
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
    ).model_dump(mode="json")


def test_provider_refuses_when_gate_is_closed_before_transport():
    called = False

    def handler(_request):
        nonlocal called
        called = True
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        ProviderConfig(base_url="https://provider.test/v1", model="test-model"),
        client=client,
    )
    with pytest.raises(ProviderError, match="disabled"):
        provider.respond(_visible(), gate=LiveExecutionGate(enabled=True, approval_hash="a" * 64))
    assert called is False
    provider.close()


def test_provider_sends_only_visible_packet_and_validates_result(monkeypatch):
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        captured["url"] = str(request.url)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(_result_json())}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    monkeypatch.setattr("blackbox.bdb5.provider.LIVE_INFERENCE_ENABLED", True)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        ProviderConfig(base_url="https://provider.test/v1", model="test-model"),
        client=client,
    )
    visible = _visible()
    run = provider.respond(
        visible,
        gate=LiveExecutionGate(
            enabled=True,
            approval_hash="a" * 64,
            case_id="BDB5-R2",
        ),
    )
    provider.close()

    assert run.provider_calls == 1
    assert run.scored is False
    assert run.approved is False
    assert run.case_id == "BDB5-R2"
    assert captured["url"] == "https://provider.test/v1/chat/completions"
    user_text = captured["body"]["messages"][1]["content"]
    assert "MODEL-VISIBLE PACKET:" in user_text
    assert "ABSTENTION CONTRACT:" in user_text
    assert "REQUIRED ABSTENTION SHAPE" in user_text
    assert "top-level `abstention`" in user_text
    assert '"application_source_not_established": true' in user_text
    assert "REPRODUCTION_BEFORE or REPRODUCTION_AFTER" in user_text
    assert "omit that TestExecution entirely" in user_text
    assert "evaluator_only" not in user_text
    assert "ground_truth" not in user_text
    assert "expected_line" not in user_text


def test_provider_rejects_causal_claim_without_structured_abstention(monkeypatch):
    def handler(_request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(_bad_causal_result_json())}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })

    monkeypatch.setattr("blackbox.bdb5.provider.LIVE_INFERENCE_ENABLED", True)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        ProviderConfig(base_url="https://provider.test/v1", model="test-model"),
        client=client,
    )
    with pytest.raises(ProviderError, match="violates abstention contract"):
        provider.respond(
            _visible(),
            gate=LiveExecutionGate(
                enabled=True,
                approval_hash="a" * 64,
                case_id="BDB5-R2",
            ),
        )
    provider.close()


def test_provider_config_reads_large_context_from_env(monkeypatch):
    monkeypatch.setenv("BLACKBOX_BDB5_PROVIDER_URL", "https://provider.test/v1")
    monkeypatch.setenv("BLACKBOX_BDB5_MODEL", "test-model")
    monkeypatch.setenv("BLACKBOX_BDB5_CONTEXT_LENGTH", str(MAX_CONTEXT_LENGTH))
    monkeypatch.setenv("BLACKBOX_BDB5_TIMEOUT_SECONDS", "1200")
    config = ProviderConfig.from_env()
    assert config.context_length == MAX_CONTEXT_LENGTH
    assert config.timeout_seconds == 1200
    config.validate()


def test_provider_config_rejects_context_above_max(monkeypatch):
    monkeypatch.setenv("BLACKBOX_BDB5_PROVIDER_URL", "https://provider.test/v1")
    monkeypatch.setenv("BLACKBOX_BDB5_MODEL", "test-model")
    monkeypatch.setenv("BLACKBOX_BDB5_CONTEXT_LENGTH", str(MAX_CONTEXT_LENGTH + 1))
    config = ProviderConfig.from_env()
    with pytest.raises(ProviderError, match="context length"):
        config.validate()


def test_provider_schema_requires_abstention():
    schema = provider_result_schema()
    assert "abstention" in schema["required"]
    assert "structured object" in schema["properties"]["abstention"]["description"]
    abstention_required = set(schema["$defs"]["Abstention"]["required"])
    assert {
        "scope",
        "reason",
        "missing_evidence",
        "source_not_established",
        "application_source_not_established",
    } <= abstention_required


def test_result_contract_rejects_not_established_without_abstention():
    result = InvestigationResult.model_validate(_bad_not_established_result_json())
    report = validate_result_contract(result)
    assert report.codes() == ("missing_structured_abstention",)


def test_result_contract_rejects_unrecorded_reproduction():
    result = InvestigationResult(
        case_id=CaseId.R2,
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.APPLICATION_SOURCE,
            reason="The evidence does not establish an application-source cause.",
            missing_evidence=("application stack trace",),
            application_source_not_established=True,
        ),
        test_executions=(
            TestExecution(
                role=TestRole.REPRODUCTION_BEFORE,
                name="reproduce_fixture_error",
                outcome=TestOutcome.FAIL,
            ),
        ),
    )
    report = validate_result_contract(result)
    assert report.codes() == ("missing_execution_artifact",)


def test_result_contract_rejects_unrecorded_pass():
    result = InvestigationResult(
        case_id=CaseId.R2,
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.APPLICATION_SOURCE,
            reason="The evidence does not establish an application-source cause.",
            missing_evidence=("application stack trace",),
            application_source_not_established=True,
        ),
        test_executions=(
            TestExecution(
                role=TestRole.OTHER,
                name="claimed_pass",
                outcome=TestOutcome.PASS,
            ),
        ),
    )
    report = validate_result_contract(result)
    assert report.codes() == ("missing_execution_artifact",)


def test_provider_native_ollama_uses_final_content(monkeypatch):
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        captured["url"] = str(request.url)
        return httpx.Response(200, json={
            "message": {"content": json.dumps(_result_json())},
            "done_reason": "stop",
            "prompt_eval_count": 12,
            "eval_count": 8,
        })

    monkeypatch.setattr("blackbox.bdb5.provider.LIVE_INFERENCE_ENABLED", True)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            base_url="http://127.0.0.1:11434",
            model="local-model",
            protocol="ollama",
            context_length=8192,
        ),
        client=client,
    )
    run = provider.respond(
        _visible(),
        gate=LiveExecutionGate(
            enabled=True,
            approval_hash="a" * 64,
            case_id="BDB5-R2",
        ),
    )
    provider.close()

    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["body"]["think"] is False
    assert captured["body"]["options"]["num_ctx"] == 8192
    assert "abstention" in captured["body"]["format"]["required"]
    assert "application_source_not_established" in captured["body"]["format"]["$defs"]["Abstention"]["required"]
    assert run.usage["input_tokens"] == 12
    assert run.result.case_id == CaseId.R2
