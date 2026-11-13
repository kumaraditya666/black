"""Independent review and packet-approval records for real BDB-5 cases.

The module can record a sign-off, but it cannot make a reviewer independent.
It requires two distinct reviewers, explicit independence/conflict attestations,
and a content hash over the packet, manifest and evaluator-only label vault.
No approval record is shipped in this checkout; the R1/R2 cases remain PREPARED.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .label_vault import LabelVault
from .models import CaseId, CaseManifest, EvidencePacket
from .review import review_payload
from .scoring import digest

APPROVAL_SCHEMA = "bdb5-independent-approval-v1"


class ApprovalError(ValueError):
    """The approval record is incomplete, stale or not independent."""


class ReviewerSignoff(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str = Field(min_length=3, max_length=128)
    role: Literal["PRIMARY", "SECONDARY", "ADJUDICATOR"]
    independent: bool
    conflict_free: bool
    attestation: str = Field(min_length=20, max_length=2_000)
    reviewed_at: datetime

    @field_validator("reviewed_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        return value


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["bdb5-independent-approval-v1"] = APPROVAL_SCHEMA
    case_id: CaseId
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    label_vault_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewers: tuple[ReviewerSignoff, ...] = Field(min_length=2)
    approved_at: datetime
    approval_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("approved_at")
    @classmethod
    def aware_approval_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("approved_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def independent_pair(self):
        ids = [item.reviewer_id for item in self.reviewers]
        if len(ids) != len(set(ids)):
            raise ValueError("reviewers must be distinct")
        if any(not item.independent or not item.conflict_free for item in self.reviewers):
            raise ValueError("every reviewer must be independent and conflict-free")
        roles = {item.role for item in self.reviewers}
        if "PRIMARY" not in roles or "SECONDARY" not in roles:
            raise ValueError("approval requires one PRIMARY and one SECONDARY reviewer")
        return self

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id.value,
            "packet_sha256": self.packet_sha256,
            "manifest_sha256": self.manifest_sha256,
            "label_vault_sha256": self.label_vault_sha256,
            "reviewers": [
                item.model_dump(mode="json") for item in self.reviewers
            ],
            "approved_at": self.approved_at.isoformat(),
            "approval_hash": self.approval_hash,
            "approved": True,
            "model_calls": 0,
        }


def _approval_base(
    *,
    case_id: CaseId,
    packet_sha256: str,
    manifest_sha256: str,
    label_vault_sha256: str,
    reviewers: tuple[ReviewerSignoff, ...],
    approved_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": APPROVAL_SCHEMA,
        "case_id": case_id.value,
        "packet_sha256": packet_sha256,
        "manifest_sha256": manifest_sha256,
        "label_vault_sha256": label_vault_sha256,
        "reviewers": [item.model_dump(mode="json") for item in reviewers],
        "approved_at": approved_at.isoformat(),
    }


def _manifest_and_packet(payload: dict[str, Any]) -> tuple[CaseManifest, EvidencePacket]:
    try:
        manifest = CaseManifest.model_validate(payload["evaluator_only"]["manifest"])
        packet = EvidencePacket.model_validate(payload["model_visible_packet"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ApprovalError("prepared payload is missing a valid manifest or packet") from exc
    return manifest, packet


def build_approval(
    payload: dict[str, Any],
    vault: LabelVault,
    reviewers: tuple[ReviewerSignoff, ...],
    *,
    approved_at: datetime | None = None,
    registry: dict[str, Any] | None = None,
) -> ApprovalRecord:
    """Create a deterministic approval record after an external review.

    The caller supplies reviewer identities and attestations. This function does
    not verify that those people exist or performed the review; it only enforces
    the structural independence contract and binds the record to content.
    """
    review = review_payload(payload, registry)
    if not review.passed:
        raise ApprovalError("approval requires a passing packet review: " + "; ".join(review.issues))
    manifest, packet = _manifest_and_packet(payload)
    truth = vault.truth(manifest.case_id)
    if truth.case_id != manifest.case_id:
        raise ApprovalError("label vault case does not match the prepared case")
    timestamp = approved_at or datetime.now(timezone.utc)
    packet_hash = digest(packet.model_visible_payload())
    manifest_hash = digest(manifest.model_dump(mode="json"))
    base = _approval_base(
        case_id=manifest.case_id,
        packet_sha256=packet_hash,
        manifest_sha256=manifest_hash,
        label_vault_sha256=vault.vault_hash,
        reviewers=reviewers,
        approved_at=timestamp,
    )
    return ApprovalRecord(
        **base,
        approval_hash=digest(base),
    )


def validate_approval(
    approval: ApprovalRecord,
    payload: dict[str, Any],
    vault: LabelVault,
) -> None:
    """Reject stale, cross-case or malformed approval records."""
    manifest, packet = _manifest_and_packet(payload)
    if approval.case_id != manifest.case_id:
        raise ApprovalError("approval belongs to a different case")
    if approval.label_vault_sha256 != vault.vault_hash:
        raise ApprovalError("approval was bound to a different label vault")
    if approval.packet_sha256 != digest(packet.model_visible_payload()):
        raise ApprovalError("approval packet hash does not match the packet")
    if approval.manifest_sha256 != digest(manifest.model_dump(mode="json")):
        raise ApprovalError("approval manifest hash does not match the manifest")
    base = _approval_base(
        case_id=approval.case_id,
        packet_sha256=approval.packet_sha256,
        manifest_sha256=approval.manifest_sha256,
        label_vault_sha256=approval.label_vault_sha256,
        reviewers=approval.reviewers,
        approved_at=approval.approved_at,
    )
    if approval.approval_hash != digest(base):
        raise ApprovalError("approval hash does not match the record")
    if approval.approved_at < max(item.reviewed_at for item in approval.reviewers):
        raise ApprovalError("approval predates at least one reviewer sign-off")


def load_approval(path: Path) -> ApprovalRecord:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApprovalError(f"cannot read approval record {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ApprovalError("approval record must be an object")
    return ApprovalRecord.model_validate(data)


__all__ = [
    "APPROVAL_SCHEMA",
    "ApprovalError",
    "ApprovalRecord",
    "ReviewerSignoff",
    "build_approval",
    "load_approval",
    "validate_approval",
]
