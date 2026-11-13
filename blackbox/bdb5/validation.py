"""Deterministic packet, result, and leakage validation."""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from .models import (
    CaseManifest,
    CausalStatus,
    ClaimCategory,
    EvidencePacket,
    GroundTruth,
    InvestigationResult,
    TestOutcome,
    TestRole,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)
from .spec import KNOWN_DIMENSIONS

FORBIDDEN_KEYS = frozenset({
    "root_cause",
    "root_cause_service",
    "root_cause_file",
    "root_cause_line",
    "fault_description",
    "ground_truth",
    "gold_patch",
    "gold_patch_hunks",
    "fix_commit",
    "expected_answer",
    "scorer_notes",
    "label_vault",
    "target_service",
    "target_fault",
    "target_mapping",
    "is_target",
})
PRIVATE_PATH = re.compile(
    r"(?i)(?:[a-z]:\\|/tmp/|/home/|/users/|%temp%|label[_ -]?vault|staging/|\.\./|file://|\\\\)"
)
GOLD_PATCH = re.compile(r"(?m)^\s*(?:diff --git|\+\+\+ b/|--- a/)")
TARGET_MARKER = re.compile(
    r"(?i)\b(root[ _-]?cause(?:[ _-]?(?:service|file|line))?|faulty[ _-]?service|"
    r"target[ _-]?(?:service|fault|label)|is[ _-]?target|fault[ _-]?label)\b"
)


def issue(code: str, detail: str, severity: ValidationSeverity = ValidationSeverity.ERROR) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, detail=detail)


def _walk(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _strings(value: Any) -> Iterator[str]:
    for _, item in _walk(value):
        if isinstance(item, str):
            yield item


def _scan_public_payload(payload: dict[str, Any], truth: GroundTruth | None) -> list[ValidationIssue]:
    found: list[ValidationIssue] = []
    for path, value in _walk(payload):
        if isinstance(value, dict):
            for key in value:
                if str(key).lower() in FORBIDDEN_KEYS:
                    found.append(issue("forbidden_label_field", f"{path} contains forbidden key {key!r}"))
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    for text in _strings(payload):
        if PRIVATE_PATH.search(text):
            found.append(issue("private_path", "model-visible text contains a private or staging path"))
            break
        if GOLD_PATCH.search(text):
            found.append(issue("gold_patch_content", "model-visible text contains a patch/diff marker"))
            break
    if GOLD_PATCH.search(serialized):
        found.append(issue("gold_patch_content", "model-visible text contains a patch/diff marker"))
    if truth is not None:
        for literal in truth.forbidden_public_literals:
            if literal and literal in serialized:
                found.append(issue("forbidden_public_literal", "model-visible packet contains an evaluator-only literal"))
                break
        # A bare candidate name is allowed. Leakage requires a target marker
        # coupled to that name, so the hidden target may remain in the ordinary
        # unranked inventory.
        for text in _strings(payload):
            lines = text.splitlines() or [text]
            if truth.expected_service and any(
                truth.expected_service.lower() in line.lower() and TARGET_MARKER.search(line)
                for line in lines
            ):
                found.append(issue("target_mapping", "candidate name is coupled to a target marker"))
                break
            if truth.expected_fault_class:
                # The taxonomy range (for example F1-F5) is not a target label.
                fault_literal = re.compile(
                    rf"(?<![A-Za-z0-9]){re.escape(truth.expected_fault_class)}(?![A-Za-z0-9])(?!-F5\b)",
                    re.IGNORECASE,
                )
                if any(fault_literal.search(line) and TARGET_MARKER.search(line) for line in lines):
                    found.append(issue("target_mapping", "fault class is coupled to a target marker"))
                    break
    return found


def validate_manifest(manifest: CaseManifest) -> ValidationReport:
    found: list[ValidationIssue] = []
    unknown = sorted(set(manifest.required_dimensions) - KNOWN_DIMENSIONS)
    if unknown:
        found.append(issue("unknown_dimension", "unknown required dimensions: " + ", ".join(unknown)))
    if manifest.readiness.value == "APPROVED_FOR_EVALUATION" and not manifest.synthetic:
        found.append(issue(
            "real_evaluation_not_enabled",
            "this harness only evaluates synthetic manifests; real approvals remain blocked",
        ))
    return ValidationReport(issues=tuple(found))


def validate_packet(manifest: CaseManifest, packet: EvidencePacket,
                    truth: GroundTruth | None = None) -> ValidationReport:
    found: list[ValidationIssue] = []
    if manifest.case_id != packet.case_id:
        found.append(issue("case_id_mismatch", "packet case_id does not match manifest"))
    if manifest.source_revision != packet.source_revision:
        found.append(issue("source_revision_mismatch", "packet source revision does not match manifest"))
    for item in packet.evidence:
        if manifest.source_revision is not None and item.source_revision is not None and item.source_revision != manifest.source_revision:
            found.append(issue(
                "evidence_revision_mismatch",
                f"evidence {item.evidence_id} has a source revision different from the manifest",
            ))
    present_types = {item.evidence_type for item in packet.evidence}
    missing_types = [item.value for item in manifest.required_evidence_types if item not in present_types]
    if missing_types:
        found.append(issue("missing_required_evidence", "packet lacks required evidence types: " + ", ".join(missing_types)))
    for artifact_id, digest in packet.artifact_hashes.items():
        expected = manifest.artifact_hashes.get(artifact_id)
        if expected is None:
            found.append(issue("unregistered_artifact", f"artifact {artifact_id} is not in the manifest"))
        elif expected != digest:
            found.append(issue("artifact_hash_mismatch", f"artifact {artifact_id} hash differs from the manifest"))
    found.extend(_scan_public_payload(packet.model_visible_payload(), truth))
    return ValidationReport(issues=tuple(found))


def validate_result(manifest: CaseManifest, packet: EvidencePacket,
                    result: InvestigationResult) -> ValidationReport:
    found: list[ValidationIssue] = []
    if result.case_id != manifest.case_id:
        found.append(issue("result_case_mismatch", "result case_id does not match manifest"))
    known = {item.evidence_id for item in packet.evidence}
    cited: list[str] = []
    for claim in result.claims:
        cited.extend(claim.evidence_ids)
    cited.extend(result.mechanism_evidence_ids)
    unknown = sorted(set(cited) - known)
    if unknown:
        found.append(issue("unknown_citation", "unknown evidence IDs: " + ", ".join(unknown),
                           ValidationSeverity.WARNING))
    if (
        result.claimed_source_revision is not None
        and manifest.source_revision is not None
        and result.claimed_source_revision != manifest.source_revision
    ):
        found.append(issue("wrong_source_revision", "result claims a source revision different from the manifest"))
    for execution in result.test_executions:
        if execution.outcome.value == "PASS" and not execution.recorded:
            found.append(issue(
                "unrecorded_test_pass",
                f"test {execution.name!r} is claimed as PASS without an execution artifact",
                ValidationSeverity.WARNING,
            ))
    if any(claim.asserts_execution for claim in result.claims) and not any(t.recorded for t in result.test_executions):
        found.append(issue(
            "unrecorded_execution_claim",
            "a claim asserts execution but no recorded execution artifact exists",
            ValidationSeverity.WARNING,
        ))
    return ValidationReport(issues=tuple(found))


CAUSAL_CLAIM_CATEGORIES = frozenset({
    ClaimCategory.SERVICE_CAUSE,
    ClaimCategory.SOURCE_CAUSE,
    ClaimCategory.APPLICATION_SOURCE_CAUSE,
})
REPRODUCTION_ROLES = frozenset({
    TestRole.REPRODUCTION_BEFORE,
    TestRole.REPRODUCTION_AFTER,
})


def validate_result_contract(result: InvestigationResult) -> ValidationReport:
    """Reject internally inconsistent causal claims and abstentions.

    This is a provider-output contract, not a score. It does not know the
    evaluator truth. It requires a result that says causation is not
    established to carry a structured abstention, a result that carries an
    abstention not to claim an established cause, and reproduction or PASS
    executions to carry an artifact hash.
    """
    found: list[ValidationIssue] = []
    if result.abstention is None:
        if result.l2_causal_status == CausalStatus.NOT_ESTABLISHED:
            found.append(issue(
                "missing_structured_abstention",
                "l2_causal_status NOT_ESTABLISHED requires a structured abstention",
            ))
        for claim in result.claims:
            if claim.category in CAUSAL_CLAIM_CATEGORIES or claim.category == ClaimCategory.ABSTENTION:
                found.append(issue(
                    "missing_structured_abstention",
                    f"claim category {claim.category.value} requires a structured abstention",
                ))
                break
    elif result.l2_causal_status != CausalStatus.NOT_ESTABLISHED:
        found.append(issue(
            "abstention_causal_status_mismatch",
            "a structured abstention requires l2_causal_status NOT_ESTABLISHED",
        ))
    for execution in result.test_executions:
        if execution.recorded:
            continue
        if execution.role in REPRODUCTION_ROLES:
            found.append(issue(
                "missing_execution_artifact",
                f"test execution {execution.role.value} {execution.name!r} requires artifact_sha256",
            ))
        elif execution.outcome == TestOutcome.PASS:
            found.append(issue(
                "missing_execution_artifact",
                f"PASS test execution {execution.name!r} requires artifact_sha256",
            ))
    return ValidationReport(issues=tuple(found))
