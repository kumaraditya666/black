"""Score an approved real BDB-5 case without calling a model.

The packet review and independent approval are both required. The label vault is
loaded only here, never added to the packet. A real score is still not a BDB-5
benchmark result: it is one case-level evaluation with its own result class.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .approval import ApprovalError, ApprovalRecord, validate_approval
from .label_vault import LabelVault
from .models import (
    CaseManifest,
    CaseScore,
    EvaluationMode,
    EvidencePacket,
    InvestigationResult,
    Readiness,
)
from .review import review_payload
from .scoring import score_case
from .validation import validate_packet, validate_result


class RealScoreError(ValueError):
    """The real score request is missing approval or valid evidence."""


@dataclass(frozen=True)
class RealCaseRun:
    case_id: str
    status: str
    score: CaseScore
    approval_hash: str
    approved: bool = True
    scored: bool = True
    provider_calls: int = 0

    def payload(self) -> dict[str, Any]:
        return {
            "mode": "REAL_CASE_EVALUATION",
            "case_id": self.case_id,
            "status": self.status,
            "approved": self.approved,
            "scored": self.scored,
            "provider_calls": self.provider_calls,
            "benchmark_result": False,
            "approval_hash": self.approval_hash,
            "score": self.score.model_dump(mode="json"),
        }


def score_approved_case(
    payload: dict[str, Any],
    result: InvestigationResult | dict[str, Any],
    vault: LabelVault,
    approval: ApprovalRecord,
    *,
    registry: dict[str, Any] | None = None,
) -> RealCaseRun:
    review = review_payload(payload, registry)
    if not review.passed:
        raise RealScoreError("prepared payload failed review: " + "; ".join(review.issues))
    try:
        validate_approval(approval, payload, vault)
    except ApprovalError as exc:
        raise RealScoreError(f"approval rejected: {exc}") from exc

    manifest = CaseManifest.model_validate(payload["evaluator_only"]["manifest"])
    packet = EvidencePacket.model_validate(payload["model_visible_packet"])
    if result.case_id != manifest.case_id:
        raise RealScoreError("result case_id does not match the prepared case")
    truth = vault.truth(manifest.case_id)

    packet_report = validate_packet(manifest, packet, truth)
    if not packet_report.passed:
        raise RealScoreError(
            "packet failed validation: " + ", ".join(item.code for item in packet_report.errors)
        )
    result_report = validate_result(manifest, packet, result)

    # Approval is a packet/label decision. The score records the approved state
    # explicitly instead of mutating the prepared manifest on disk.
    evaluated_manifest = manifest.model_copy(
        update={"readiness": Readiness.APPROVED_FOR_EVALUATION}
    )
    score = score_case(
        evaluated_manifest,
        packet,
        truth,
        result,
        result_report,
        mode=EvaluationMode.REAL_CASE_EVALUATION,
        result_class="REAL_CASE_SCORE_NOT_BENCHMARK_RESULT",
    )
    return RealCaseRun(
        case_id=manifest.case_id.value,
        status="REAL_CASE_SCORED",
        score=score,
        approval_hash=approval.approval_hash,
    )


__all__ = ["RealCaseRun", "RealScoreError", "score_approved_case"]
