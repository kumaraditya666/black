"""Read-only review of prepared BDB-5 payloads.

A prepared payload is not approved evidence. This module checks that the
model-visible packet contains no evaluator material, that the manifest and
packet agree, and that the case-specific evidence shape is intact. It never
promotes a case or modifies a payload.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import (
    CaseId,
    CaseManifest,
    EvidencePacket,
    EvidenceType,
    Readiness,
)
from .external_repair import P1_ALLOWED_FILES, P1_BASE_COMMIT
from .telemetry import T1_N_MAX, T1_WINDOW_END, T1_WINDOW_START
from .validation import FORBIDDEN_KEYS, PRIVATE_PATH, validate_manifest, validate_packet

VISIBLE_KEYS = frozenset({
    "case_id",
    "schema_version",
    "task_instructions",
    "evidence",
    "candidate_inventory",
    "source_revision",
    "artifact_hashes",
})
FORBIDDEN_VISIBLE_KEYS = frozenset({
    "manifest",
    "allowed_files",
    "readiness",
    "evaluator_only",
    "ground_truth",
    "gold_patch",
    "fix_commit",
    "root_cause",
    "target_mapping",
})
PAYLOAD_HASH = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PacketReview:
    case_id: str | None
    status: str
    issues: tuple[str, ...]
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return not self.issues

    def payload(self) -> dict[str, Any]:
        return {
            "mode": "REAL_CASE_PACKET_REVIEW_ONLY",
            "case_id": self.case_id,
            "status": self.status,
            "approved": False,
            "model_calls": 0,
            "checks": dict(sorted(self.checks.items())),
            "issues": list(self.issues),
        }


def _keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found.update(_keys(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.update(_keys(child))
    return found


def _strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            found.extend(_strings(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.extend(_strings(child))
    return found


def _registry_entry(registry: dict[str, Any] | None, case_id: str) -> dict[str, Any] | None:
    if not registry:
        return None
    cases = registry.get("cases")
    if not isinstance(cases, dict):
        return None
    entry = cases.get(case_id)
    return entry if isinstance(entry, dict) else None


def review_payload(payload: dict[str, Any],
                   registry: dict[str, Any] | None = None) -> PacketReview:
    """Review one prepared JSON payload without changing it or approving it."""
    issues: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool, detail: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            issues.append(f"{name}: {detail}")

    check("mode", payload.get("mode") == "REAL_CASE_PREPARATION_ONLY",
          "payload must be REAL_CASE_PREPARATION_ONLY")
    check("no_model_calls", payload.get("model_calls") == 0,
          "preparation must record zero model calls")
    check("no_top_level_manifest", "manifest" not in payload,
          "manifest must not be at the top level")
    check("prepared_not_approved", payload.get("readiness") == Readiness.PREPARED.value,
          "review accepts PREPARED payloads only; do not promote the case")

    case_id = payload.get("case_id")
    check("known_case", case_id in (CaseId.T1.value, CaseId.R1.value, CaseId.R2.value,
                                   CaseId.R3.value, CaseId.P1.value),
          "review supports BDB5-T1, BDB5-R1, BDB5-R2, BDB5-R3 and BDB5-P1")
    check("payload_hash", isinstance(payload.get("payload_hash"), str)
          and bool(PAYLOAD_HASH.fullmatch(payload["payload_hash"])),
          "payload_hash must be a 64-character lowercase SHA-256")

    visible = payload.get("model_visible_packet")
    evaluator = payload.get("evaluator_only")
    check("visible_packet_object", isinstance(visible, dict),
          "model_visible_packet must be an object")
    check("evaluator_object", isinstance(evaluator, dict),
          "evaluator_only must be an object")
    if not isinstance(visible, dict) or not isinstance(evaluator, dict):
        return PacketReview(
            case_id=case_id if isinstance(case_id, str) else None,
            status="REVIEW_FAILED",
            issues=tuple(issues),
            checks=checks,
        )

    check("visible_keys", set(visible) == VISIBLE_KEYS,
          "model-visible keys must be exactly the packet serializer keys")
    check("no_manifest_in_visible", "manifest" not in visible,
          "manifest leaked into the model-visible packet")
    forbidden = _keys(visible) & (set(FORBIDDEN_KEYS) | FORBIDDEN_VISIBLE_KEYS)
    check("no_forbidden_keys", not forbidden,
          "forbidden keys in model-visible packet: " + ", ".join(sorted(forbidden)))
    # Scan the strings themselves, not canonical JSON. JSON escaping turns
    # ordinary newlines into ``\\n`` and would falsely match the UNC-path rule.
    visible_strings = _strings(visible)
    check("no_private_paths", all(PRIVATE_PATH.search(text) is None for text in visible_strings),
          "model-visible packet contains a private or host path")

    manifest_raw = evaluator.get("manifest")
    check("manifest_present", isinstance(manifest_raw, dict),
          "evaluator_only.manifest is missing")
    packet_validation = evaluator.get("packet_validation")
    check("packet_validation_present", isinstance(packet_validation, dict),
          "evaluator_only.packet_validation is missing")

    manifest: CaseManifest | None = None
    packet: EvidencePacket | None = None
    if isinstance(manifest_raw, dict):
        try:
            manifest = CaseManifest.model_validate(manifest_raw)
        except ValidationError as exc:
            check("manifest_valid", False, f"invalid manifest: {exc}")
    if manifest is not None:
        check("manifest_case_matches", manifest.case_id.value == case_id,
              "manifest case_id does not match payload")
        check("manifest_readiness", manifest.readiness == Readiness.PREPARED,
              "manifest must remain PREPARED")
        check("manifest_not_synthetic", manifest.synthetic is False,
              "prepared real cases must not be synthetic")
    else:
        check("manifest_valid", False, "manifest could not be validated")

    try:
        packet = EvidencePacket.model_validate(visible)
    except ValidationError as exc:
        check("packet_valid", False, f"invalid model-visible packet: {exc}")
    if packet is not None:
        check("packet_case_matches", packet.case_id.value == case_id,
              "packet case_id does not match payload")
        check("packet_schema", packet.schema_version == "bdb5-evidence-v1",
              "unexpected packet schema version")
        if manifest is not None:
            check("packet_revision_matches", packet.source_revision == manifest.source_revision,
                  "packet source revision does not match manifest")
            report = validate_packet(manifest, packet)
            check("packet_validation_clean", report.passed,
                  "packet validation failed: " + ", ".join(item.code for item in report.errors))
            manifest_report = validate_manifest(manifest)
            check("manifest_validation_clean", manifest_report.passed,
                  "manifest validation failed: " + ", ".join(item.code for item in manifest_report.errors))
        if isinstance(packet_validation, dict):
            check("preparation_validation_empty", packet_validation.get("issues") == [],
                  "preparation recorded packet-validation issues")
        else:
            check("preparation_validation_empty", False, "missing packet_validation.issues")

        evidence_types = {item.evidence_type for item in packet.evidence}
        evidence_ids = {item.evidence_id for item in packet.evidence}
        if case_id == CaseId.R1.value:
            check("r1_ci_evidence", EvidenceType.CI_LOG in evidence_types,
                  "R1 lacks CI_LOG evidence")
            check("r1_source_evidence", EvidenceType.SOURCE_EXCERPT in evidence_types,
                  "R1 lacks SOURCE_EXCERPT evidence")
            check("r1_source_id", "source:1" in evidence_ids,
                  "R1 lacks source:1 evidence")
        elif case_id == CaseId.R2.value:
            check("r2_ci_evidence", EvidenceType.CI_LOG in evidence_types,
                  "R2 lacks CI_LOG evidence")
            check("r2_test_evidence", EvidenceType.TEST_RESULT in evidence_types,
                  "R2 lacks TEST_RESULT evidence")
            check("r2_no_source_evidence", EvidenceType.SOURCE_EXCERPT not in evidence_types,
                  "R2 must not claim an application-source excerpt")
        elif case_id == CaseId.R3.value:
            check("r3_issue_evidence", EvidenceType.ISSUE_TEXT in evidence_types,
                  "R3 lacks ISSUE_TEXT evidence")
            check("r3_source_evidence", EvidenceType.SOURCE_EXCERPT in evidence_types,
                  "R3 lacks SOURCE_EXCERPT evidence")
            check("r3_source_id", "source:1" in evidence_ids,
                  "R3 lacks source:1 evidence")
        elif case_id == CaseId.T1.value:
            check("t1_metric_evidence", EvidenceType.TELEMETRY_METRIC in evidence_types,
                  "T1 lacks TELEMETRY_METRIC evidence")
            check("t1_log_evidence", EvidenceType.TELEMETRY_LOG in evidence_types,
                  "T1 lacks TELEMETRY_LOG evidence")
            check("t1_no_source_revision", packet.source_revision is None,
                  "T1 must not claim a source revision")
        elif case_id == CaseId.P1.value:
            check("p1_issue_evidence", EvidenceType.ISSUE_TEXT in evidence_types,
                  "P1 lacks ISSUE_TEXT evidence")
            check("p1_source_evidence", EvidenceType.SOURCE_EXCERPT in evidence_types,
                  "P1 lacks SOURCE_EXCERPT evidence")
            check("p1_source_id", "source:1" in evidence_ids,
                  "P1 lacks source:1 evidence")
            check("p1_no_test_material", not any(
                key in _keys(visible) for key in
                ("test_patch", "gold_patch", "fail_to_pass", "pass_to_pass", "fix_commit")
            ), "P1 model-visible packet contains hidden test or fix material")

    primary = evaluator.get("primary_failure")
    if case_id == CaseId.T1.value:
        telemetry = evaluator.get("telemetry")
        check("t1_telemetry_present", isinstance(telemetry, dict),
              "evaluator_only.telemetry is missing")
        if isinstance(telemetry, dict):
            check("t1_window", telemetry.get("window_start") == T1_WINDOW_START
                  and telemetry.get("window_end") == T1_WINDOW_END,
                  "T1 window does not match the frozen window")
            check("t1_n_max", telemetry.get("n_max") == T1_N_MAX,
                  "T1 N_max does not match the frozen cap")
            check("t1_metric_rows", telemetry.get("metric_rows") == 1_441,
                  "T1 metrics table is not complete")
            check("t1_selected_logs", 0 < telemetry.get("selected_log_rows", 0) <= T1_N_MAX,
                  "T1 selected log count is outside the frozen bound")
            check("t1_inventory", isinstance(telemetry.get("inventory"), list)
                  and telemetry.get("inventory") == visible.get("candidate_inventory"),
                  "T1 inventory metadata does not match the packet")
            check("t1_inventory_status", isinstance(telemetry.get("inventory_status"), str)
                  and bool(telemetry.get("inventory_status")),
                  "T1 inventory status is missing")
    elif case_id == CaseId.P1.value:
        frame = evaluator.get("source_frame")
        check("p1_source_frame", isinstance(frame, dict)
              and frame.get("path") == "sympy/core/_print_helpers.py",
              "P1 source frame does not match the allowed file")
        external = evaluator.get("external_repair")
        check("p1_external_present", isinstance(external, dict),
              "evaluator_only.external_repair is missing")
        if isinstance(external, dict):
            check("p1_external_base", external.get("base_commit") == manifest.source_revision
                  if manifest is not None else False,
                  "P1 external base commit does not match the manifest")
            check("p1_external_allowed", external.get("allowed_files") == list(P1_ALLOWED_FILES),
                  "P1 external allowed files do not match the frozen scope")
            check("p1_external_hidden", external.get("hidden_test_location") == "evaluator_only",
                  "P1 hidden tests must remain evaluator-only")
    elif isinstance(primary, dict):
        frame = primary.get("frame")
        if case_id == CaseId.R1.value:
            check("r1_primary_frame", isinstance(frame, dict)
                  and frame.get("path") == "verktyg/requests.py"
                  and frame.get("line") == 356
                  and frame.get("function") == "args",
                  "R1 primary frame does not match the prepared source frame")
        elif case_id == CaseId.R2.value:
            check("r2_primary_frame", isinstance(frame, dict)
                  and frame.get("test_file") is True,
                  "R2 primary frame must be a test frame")
    elif case_id == CaseId.R3.value:
        frame = evaluator.get("source_frame")
        check("r3_source_frame", isinstance(frame, dict)
              and frame.get("path") == "django/http/response.py"
              and frame.get("line") == 232
              and frame.get("function") == "make_bytes",
              "R3 source frame does not match the pinned issue source")
    else:
        check("primary_failure_present", False, "evaluator_only.primary_failure is missing")

    if case_id == CaseId.R1.value:
        check("r1_source_status", evaluator.get("source_status") == "resolved",
              "R1 source status must be resolved")
    elif case_id == CaseId.R2.value:
        check("r2_source_status", evaluator.get("source_status") is None,
              "R2 must not have an application-source status")
    elif case_id == CaseId.R3.value:
        check("r3_source_status", evaluator.get("source_status") == "resolved",
              "R3 source status must be resolved")
    elif case_id == CaseId.T1.value:
        check("t1_manifest_no_source_revision", manifest is not None
              and manifest.source_revision is None,
              "T1 manifest must not claim a source revision")
    elif case_id == CaseId.P1.value:
        check("p1_source_revision", manifest is not None
              and manifest.source_revision == P1_BASE_COMMIT,
              "P1 manifest must pin the SymPy base commit")

    entry = _registry_entry(registry, case_id) if isinstance(case_id, str) else None
    if entry is not None and manifest is not None:
        check("registry_revision", manifest.source_revision == entry.get("source_revision"),
              "manifest source revision does not match the fixture registry")

    status = "REVIEW_PASSED" if not issues else "REVIEW_FAILED"
    return PacketReview(
        case_id=case_id if isinstance(case_id, str) else None,
        status=status,
        issues=tuple(issues),
        checks=checks,
    )


def review_file(path: Path, registry_path: Path | None = None) -> PacketReview:
    payload = json.loads(path.read_text(encoding="utf-8"))
    registry = None
    if registry_path is not None:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    return review_payload(payload, registry)
