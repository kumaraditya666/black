"""Real-case run envelope with no provider, approval or scoring.

The caller supplies the responder. This module deliberately imports no model
provider. It hands the responder only the model-visible packet, validates the
returned ``InvestigationResult``, and stops at ``RUN_READY_FOR_REVIEW``.

A runner result is not a benchmark result: ``approved`` and ``scored`` remain
false, and the prepared case stays ``PREPARED``.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import ValidationError

from .models import (
    CaseManifest,
    EvidencePacket,
    InvestigationResult,
    ValidationSeverity,
)
from .review import PacketReview, review_payload
from .scoring import digest
from .validation import validate_result

Responder = Callable[[dict[str, Any]], InvestigationResult | dict[str, Any]]


class RunnerError(ValueError):
    """The prepared payload or the responder result cannot be run safely."""


@dataclass(frozen=True)
class PreparedCaseRun:
    case_id: str | None
    status: str
    review: PacketReview
    validation_issues: tuple[dict[str, Any], ...]
    result_hash: str | None
    responder_keys: tuple[str, ...]
    approved: bool = False
    scored: bool = False

    def payload(self) -> dict[str, Any]:
        return {
            "mode": "REAL_CASE_RUN_ENVELOPE",
            "case_id": self.case_id,
            "status": self.status,
            "approved": self.approved,
            "scored": self.scored,
            "provider_calls": 0,
            "responder_invocations": 1 if self.responder_keys else 0,
            "model_visible_keys": list(self.responder_keys),
            "packet_review": self.review.payload(),
            "validation_issues": list(self.validation_issues),
            "result_hash": self.result_hash,
        }


def _case_objects(payload: dict[str, Any],
                  registry: dict[str, Any] | None) -> tuple[PacketReview, CaseManifest, EvidencePacket]:
    review = review_payload(payload, registry)
    if not review.passed:
        raise RunnerError("prepared payload failed review: " + "; ".join(review.issues))
    manifest = CaseManifest.model_validate(payload["evaluator_only"]["manifest"])
    packet = EvidencePacket.model_validate(payload["model_visible_packet"])
    return review, manifest, packet


def accept_prepared_result(payload: dict[str, Any],
                           raw_result: InvestigationResult | dict[str, Any],
                           *,
                           registry: dict[str, Any] | None = None,
                           responder_keys: tuple[str, ...] = ()) -> PreparedCaseRun:
    """Validate an already-produced result without scoring or approving it."""
    review, manifest, packet = _case_objects(payload, registry)
    try:
        result = (
            raw_result
            if isinstance(raw_result, InvestigationResult)
            else InvestigationResult.model_validate(raw_result)
        )
    except ValidationError as exc:
        raise RunnerError(f"responder result is not a valid InvestigationResult: {exc}") from exc

    validation = validate_result(manifest, packet, result)
    issues = tuple(item.model_dump(mode="json") for item in validation.issues)
    errors = [item for item in validation.issues
              if item.severity == ValidationSeverity.ERROR]
    status = "RUN_REJECTED" if errors else "RUN_READY_FOR_REVIEW"
    return PreparedCaseRun(
        case_id=manifest.case_id.value,
        status=status,
        review=review,
        validation_issues=issues,
        result_hash=digest(result.model_dump(mode="json")),
        responder_keys=responder_keys,
        approved=False,
        scored=False,
    )


def run_prepared_case(payload: dict[str, Any],
                      responder: Responder,
                      *,
                      registry: dict[str, Any] | None = None) -> PreparedCaseRun:
    """Call an injected responder with only the model-visible packet.

    The responder receives a copy. It never receives the manifest, primary
    frame, source status or any evaluator-only field.
    """
    review, _manifest, packet = _case_objects(payload, registry)
    visible = copy.deepcopy(packet.model_visible_payload())
    raw_result = responder(visible)
    return accept_prepared_result(
        payload,
        raw_result,
        registry=registry,
        responder_keys=tuple(visible.keys()),
    )
