from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from blackbox.bdb5.approval import ReviewerSignoff, build_approval
from blackbox.bdb5.issue_cases import R3, prepare_issue_case
from blackbox.bdb5.label_vault import load_label_vault
from blackbox.bdb5.models import (
    CaseId,
    CausalStatus,
    Claim,
    ClaimCategory,
    InvestigationResult,
)
from blackbox.bdb5.real_score import score_approved_case
from blackbox.bdb5.review import review_payload

ROOT = Path(__file__).resolve().parents[2]
R3_DIR = ROOT / "fixtures" / "bdb5" / "r3"
VAULT = ROOT / "fixtures" / "bdb5" / "labels" / "label_vault.json"


def _prepared():
    return prepare_issue_case(
        (R3_DIR / "issue.txt").read_text(encoding="utf-8"),
        R3,
        source_path=R3_DIR / "response.py",
    )


def _reviewers():
    now = datetime.now(timezone.utc)
    return (
        ReviewerSignoff(
            reviewer_id="r3-reviewer-a",
            role="PRIMARY",
            independent=True,
            conflict_free=True,
            attestation="I checked the pinned source and original issue report.",
            reviewed_at=now,
        ),
        ReviewerSignoff(
            reviewer_id="r3-reviewer-b",
            role="SECONDARY",
            independent=True,
            conflict_free=True,
            attestation="I independently checked the evidence and label boundary.",
            reviewed_at=now,
        ),
    )


def _result():
    return InvestigationResult(
        case_id=CaseId.R3,
        claims=(
            Claim(
                category=ClaimCategory.SOURCE_CAUSE,
                text="A memoryview is not bytes or str, so make_bytes converts it with str(value).encode and returns a representation string.",
                evidence_ids=("source:1", "issue:1"),
            ),
        ),
        predicted_files=("django/http/response.py",),
        predicted_function="make_bytes",
        predicted_line=232,
        predicted_mechanism="memoryview falls through bytes and str handling into str(value).encode.",
        mechanism_evidence_ids=("source:1",),
        l2_causal_status=CausalStatus.SUPPORTED,
        claimed_source_revision=R3.source_revision,
    )


def test_r3_preparation_has_issue_and_pinned_source_but_no_gold_patch():
    prepared = _prepared()
    payload = prepared.payload()
    assert payload["readiness"] == "PREPARED"
    assert prepared.manifest.case_id == CaseId.R3
    assert prepared.source_frame["line"] == 232
    visible = json.dumps(payload["model_visible_packet"])
    assert "memoryview" in visible
    assert "test_memoryview_content" not in visible
    assert "gold" not in visible.lower()
    assert "9aa56cb0d5dede7fc176a46c745dfd3dacdad773" not in visible
    assert review_payload(payload).passed


def test_r3_approval_and_real_scoring_require_no_model():
    prepared = _prepared()
    payload = prepared.payload()
    vault = load_label_vault(VAULT)
    approval = build_approval(payload, vault, _reviewers())
    run = score_approved_case(payload, _result(), vault, approval)
    assert run.status == "REAL_CASE_SCORED"
    assert run.provider_calls == 0
    assert run.score.strict_pass is True
    assert run.score.dimensions["file_exactness"] == 1.0
    assert run.score.dimensions["function_exactness"] == 1.0
    assert run.score.dimensions["mechanism"] == 1.0
    assert run.score.dimensions["causal_status"] == 1.0
