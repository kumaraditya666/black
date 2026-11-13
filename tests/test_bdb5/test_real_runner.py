from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from blackbox.bdb5.models import (
    Abstention,
    AbstentionScope,
    CaseId,
    CausalStatus,
    Claim,
    ClaimCategory,
    InvestigationResult,
)
from blackbox.bdb5.real_cases import R1, R2, prepare_ci_case
from blackbox.bdb5.runner import RunnerError, accept_prepared_result, run_prepared_case

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "fixtures" / "bdb5" / "bugswarm"
R1_LOG = LOGS / "109227527.log"
R2_LOG = LOGS / "83523531.log"
REGISTRY = LOGS / "registry.json"


def _fake_source(_repo, _commit, frame):
    return {
        "path": frame["path"],
        "line": frame["line"],
        "function": frame["function"],
        "status": "resolved",
        "source_line": "encoding=self.url_charset, errors=self.encoding_errors,",
        "context": [
            {"line": 356, "text": "    encoding=self.url_charset, errors=self.encoding_errors,"},
        ],
    }


def _payload(case):
    if case == CaseId.R1:
        return prepare_ci_case(
            R1_LOG.read_text(encoding="utf-8"), R1, source_reader=_fake_source
        ).payload()
    return prepare_ci_case(R2_LOG.read_text(encoding="utf-8"), R2).payload()


def _r1_result():
    return InvestigationResult(
        case_id=CaseId.R1,
        claims=(
            Claim(
                category=ClaimCategory.MECHANISM,
                text="The query bytes are decoded as ASCII before parsing.",
                evidence_ids=("source:1", "ci:1"),
            ),
        ),
        predicted_files=("verktyg/requests.py",),
        predicted_function="args",
        predicted_line=356,
        predicted_mechanism="ASCII decoding of query bytes fails.",
        mechanism_evidence_ids=("source:1",),
        l2_causal_status=CausalStatus.SUPPORTED,
        claimed_source_revision="71dc420c22fadbae064c46b426e093bec7b86f32",
    )


def _r2_result():
    return InvestigationResult(
        case_id=CaseId.R2,
        claims=(
            Claim(
                category=ClaimCategory.HARNESS_CAUSE,
                text="The test fixture types_dict.nml is missing.",
                evidence_ids=("test:1",),
            ),
        ),
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.APPLICATION_SOURCE,
            reason="The CI log establishes a missing test fixture, not an application-source cause.",
            missing_evidence=("application source traceback",),
            application_source_not_established=True,
        ),
    )


def test_runner_passes_only_the_visible_packet_to_responder():
    seen = {}
    payload = _payload(CaseId.R1)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def responder(visible):
        seen.update(visible)
        return _r1_result()

    run = run_prepared_case(payload, responder, registry=registry)
    assert run.status == "RUN_READY_FOR_REVIEW"
    assert run.approved is False
    assert run.scored is False
    assert run.payload()["provider_calls"] == 0
    assert "manifest" not in seen
    assert "evaluator_only" not in seen
    assert set(seen) == {
        "case_id", "schema_version", "task_instructions", "evidence",
        "candidate_inventory", "source_revision", "artifact_hashes",
    }


def test_runner_accepts_r2_abstention_without_approving_it():
    payload = _payload(CaseId.R2)
    run = accept_prepared_result(payload, _r2_result())
    assert run.status == "RUN_READY_FOR_REVIEW"
    assert run.approved is False
    assert run.scored is False
    assert run.validation_issues == ()


def test_runner_rejects_a_tampered_payload_before_calling_responder():
    payload = _payload(CaseId.R2)
    payload["manifest"] = payload["evaluator_only"]["manifest"]
    called = False

    def responder(_visible):
        nonlocal called
        called = True
        return _r2_result()

    with pytest.raises(RunnerError, match="failed review"):
        run_prepared_case(payload, responder)
    assert called is False


def test_runner_cli_outputs_ready_for_review(tmp_path):
    payload = _payload(CaseId.R2)
    prepared = tmp_path / "r2.json"
    result = tmp_path / "result.json"
    prepared.write_text(json.dumps(payload), encoding="utf-8")
    result.write_text(json.dumps(_r2_result().model_dump(mode="json")), encoding="utf-8")
    command = [
        sys.executable,
        str(ROOT / "scripts" / "bdb5_run_prepared.py"),
        "--prepared", str(prepared),
        "--result", str(result),
        "--registry", str(REGISTRY),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8"
    )
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["status"] == "RUN_READY_FOR_REVIEW"
    assert output["approved"] is False
    assert output["scored"] is False
    assert output["provider_calls"] == 0
