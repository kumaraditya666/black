from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from blackbox.bdb5.approval import (
    ApprovalError,
    ReviewerSignoff,
    build_approval,
    validate_approval,
)
from blackbox.bdb5.label_vault import LabelVaultError, load_label_vault
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
from blackbox.bdb5.real_cases import R1, R2, prepare_ci_case
from blackbox.bdb5.real_score import RealScoreError, score_approved_case

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "fixtures" / "bdb5" / "bugswarm"
R1_LOG = LOGS / "109227527.log"
R2_LOG = LOGS / "83523531.log"
VAULT = ROOT / "fixtures" / "bdb5" / "labels" / "label_vault.json"
ARTIFACT = "a" * 64


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


def _reviewers():
    now = datetime.now(timezone.utc)
    return (
        ReviewerSignoff(
            reviewer_id="reviewer-a",
            role="PRIMARY",
            independent=True,
            conflict_free=True,
            attestation="I reproduced the evidence and reviewed the label.",
            reviewed_at=now,
        ),
        ReviewerSignoff(
            reviewer_id="reviewer-b",
            role="SECONDARY",
            independent=True,
            conflict_free=True,
            attestation="I independently checked the packet and label boundary.",
            reviewed_at=now,
        ),
    )


def _approval(payload, vault):
    return build_approval(payload, vault, _reviewers())


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
        test_executions=(
            TestExecution(
                role=TestRole.REPRODUCTION_BEFORE,
                name="test_modified_url_encoding",
                outcome=TestOutcome.FAIL,
                artifact_sha256=ARTIFACT,
                failure_signature_matched=True,
            ),
        ),
    )


def _r2_result():
    return InvestigationResult(
        case_id=CaseId.R2,
        claims=(
            Claim(
                category=ClaimCategory.HARNESS_CAUSE,
                text="The missing fixture types_dict.nml is opened at test_f90nml.py:211.",
                evidence_ids=("test:1",),
            ),
        ),
        l2_causal_status=CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.APPLICATION_SOURCE,
            reason="The log establishes only a missing test fixture.",
            missing_evidence=("application source traceback",),
            application_source_not_established=True,
        ),
        test_executions=(
            TestExecution(
                role=TestRole.REPRODUCTION_BEFORE,
                name="test_dict_write",
                outcome=TestOutcome.FAIL,
                artifact_sha256=ARTIFACT,
                failure_signature_matched=True,
            ),
        ),
    )


def test_label_vault_is_separate_and_has_hashes():
    vault = load_label_vault(VAULT)
    assert vault.truth(CaseId.R1).expected_line == 356
    assert vault.truth(CaseId.R2).expected_l2_status == CausalStatus.NOT_ESTABLISHED
    assert vault.truth(CaseId.R3).expected_line == 232
    assert len(vault.vault_hash) == 64
    with pytest.raises(LabelVaultError):
        vault.truth(CaseId.T1)


def test_approval_requires_two_independent_reviewers_and_is_content_bound():
    payload = _payload(CaseId.R2)
    vault = load_label_vault(VAULT)
    approval = _approval(payload, vault)
    validate_approval(approval, payload, vault)
    assert approval.payload()["approved"] is True

    with pytest.raises(ApprovalError, match="different label vault"):
        validate_approval(approval, payload, dataclasses.replace(vault, vault_hash="b" * 64))
    tampered = json.loads(json.dumps(payload))
    tampered["model_visible_packet"]["task_instructions"] += " changed"
    with pytest.raises(ApprovalError, match="packet hash"):
        validate_approval(approval, tampered, vault)

    with pytest.raises(ValueError, match="at least 2"):
        build_approval(payload, vault, _reviewers()[:1])
    primary_only = tuple(
        item.model_copy(update={"role": "PRIMARY"}) for item in _reviewers()
    )
    with pytest.raises(ValueError, match="PRIMARY and one SECONDARY"):
        build_approval(payload, vault, primary_only)


def test_approved_r1_scores_real_case_without_approving_model_output():
    payload = _payload(CaseId.R1)
    vault = load_label_vault(VAULT)
    approval = _approval(payload, vault)
    run = score_approved_case(payload, _r1_result(), vault, approval)
    assert run.status == "REAL_CASE_SCORED"
    assert run.approved is True
    assert run.scored is True
    assert run.provider_calls == 0
    assert run.payload()["benchmark_result"] is False
    assert run.score.synthetic is False
    assert run.score.mode.value == "REAL_CASE_EVALUATION"
    assert run.score.result_class == "REAL_CASE_SCORE_NOT_BENCHMARK_RESULT"
    assert run.score.strict_pass is True


def test_approved_r2_separates_fixture_claim_from_app_source_abstention():
    payload = _payload(CaseId.R2)
    vault = load_label_vault(VAULT)
    approval = _approval(payload, vault)
    run = score_approved_case(payload, _r2_result(), vault, approval)
    assert run.score.strict_pass is True
    assert run.score.dimensions["app_source_claim"] == 0.0
    assert run.score.dimensions["app_abstention"] == 1.0
    assert run.score.dimensions["harness_identification"] == 1.0


def test_unapproved_or_stale_approval_cannot_score():
    payload = _payload(CaseId.R2)
    vault = load_label_vault(VAULT)
    approval = _approval(payload, vault)
    with pytest.raises(RealScoreError, match="approval"):
        score_approved_case(payload, _r2_result(), vault, approval.model_copy(update={"approval_hash": "b" * 64}))
