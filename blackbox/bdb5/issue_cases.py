"""Preparation-only issue/source adapter for BDB-5 R3.

R3 is a Django issue investigation, not an exception-event case. The packet
contains the original issue statement and a pinned source excerpt. The gold
patch, test patch, hidden tests and later fix comments are never included.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    CaseCategory,
    CaseId,
    CaseManifest,
    EvidenceItem,
    EvidencePacket,
    EvidenceType,
    Readiness,
)
from .scoring import canonical_json, digest
from .validation import validate_packet


DATASET_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"
BASE_REVISION = "879cc3da6249e920b8d54518a0ae06de835d7373"
SOURCE_PATH = "django/http/response.py"
SOURCE_LINE = 232
SOURCE_FUNCTION = "make_bytes"


@dataclass(frozen=True)
class IssueCaseConfig:
    case_id: CaseId
    dataset: str
    dataset_revision: str
    repository: str
    source_revision: str
    source_path: str
    source_line: int
    source_function: str
    allowed_files: tuple[str, ...]
    required_dimensions: tuple[str, ...]
    task_instructions: str
    adapter: str


R3 = IssueCaseConfig(
    case_id=CaseId.R3,
    dataset="SWE-bench Verified",
    dataset_revision=DATASET_REVISION,
    repository="https://github.com/django/django",
    source_revision=BASE_REVISION,
    source_path=SOURCE_PATH,
    source_line=SOURCE_LINE,
    source_function=SOURCE_FUNCTION,
    allowed_files=(SOURCE_PATH,),
    required_dimensions=(
        "file_exactness",
        "function_exactness",
        "mechanism",
        "causal_status",
        "citation_validity",
        "unsupported_claim_rate",
    ),
    task_instructions=(
        "Investigate the supplied issue report using the pinned source excerpt. "
        "Identify the most likely source file and method, explain the mechanism, "
        "and cite the supplied evidence. Do not claim that a test or patch was run."
    ),
    adapter="swebench-issue-source-v1",
)


class IssuePreparationError(ValueError):
    """R3 issue evidence cannot be prepared deterministically."""


@dataclass(frozen=True)
class PreparedIssueCase:
    config: IssueCaseConfig
    manifest: CaseManifest
    packet: EvidencePacket
    source_frame: dict[str, Any]
    packet_validation: dict[str, Any]
    diagnostics: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "mode": "REAL_CASE_PREPARATION_ONLY",
            "model_calls": 0,
            "case_id": self.config.case_id.value,
            "readiness": self.manifest.readiness.value,
            "model_visible_packet": self.packet.model_visible_payload(),
            "evaluator_only": {
                "manifest": self.manifest.model_dump(mode="json"),
                "source_status": "resolved",
                "source_frame": self.source_frame,
                "packet_validation": self.packet_validation,
                "diagnostics": self.diagnostics,
            },
            "payload_hash": digest({
                "case_id": self.config.case_id.value,
                "manifest": self.manifest.model_dump(mode="json"),
                "packet": self.packet.model_visible_payload(),
                "source_frame": self.source_frame,
            }),
        }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_excerpt(path: Path, line: int, context: int = 3) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if line < 1 or line > len(lines):
        raise IssuePreparationError("source line is outside the pinned file")
    start = max(1, line - context)
    end = min(len(lines), line + context)
    return {
        "path": SOURCE_PATH,
        "line": line,
        "function": SOURCE_FUNCTION,
        "status": "resolved",
        "source_line": lines[line - 1],
        "context": [
            {"line": number, "text": lines[number - 1]}
            for number in range(start, end + 1)
        ],
    }


def prepare_issue_case(
    issue_text: str,
    config: IssueCaseConfig,
    *,
    source_path: Path,
) -> PreparedIssueCase:
    if config.case_id != CaseId.R3:
        raise IssuePreparationError("this adapter prepares BDB5-R3 only")
    if not issue_text.strip():
        raise IssuePreparationError("issue text is empty")
    frame = _source_excerpt(source_path, config.source_line)
    source_text = "\n".join(
        f"{item['line']:>4}: {item['text']}" for item in frame["context"]
    )
    evidence = (
        EvidenceItem(
            evidence_id="issue:1",
            evidence_type=EvidenceType.ISSUE_TEXT,
            text=issue_text.strip(),
            structured={"source": "django-ticket-30294"},
        ),
        EvidenceItem(
            evidence_id="source:1",
            evidence_type=EvidenceType.SOURCE_EXCERPT,
            text=source_text,
            structured={
                "path": frame["path"],
                "line": frame["line"],
                "function": frame["function"],
                "status": frame["status"],
            },
            source_revision=config.source_revision,
        ),
    )
    packet = EvidencePacket(
        case_id=config.case_id,
        task_instructions=config.task_instructions,
        evidence=evidence,
        source_revision=config.source_revision,
    )
    hashes = {
        "issue_sha256": _sha(issue_text),
        "source_sha256": _sha(source_path.read_text(encoding="utf-8")),
    }
    packet = packet.model_copy(update={"artifact_hashes": hashes})
    manifest = CaseManifest(
        case_id=config.case_id,
        dataset=config.dataset,
        dataset_revision=config.dataset_revision,
        repository=config.repository,
        source_revision=config.source_revision,
        case_category=CaseCategory.ISSUE_SOURCE,
        required_evidence_types=(EvidenceType.ISSUE_TEXT, EvidenceType.SOURCE_EXCERPT),
        allowed_files=config.allowed_files,
        allowed_scope=("source",),
        required_dimensions=config.required_dimensions,
        readiness=Readiness.PREPARED,
        adapter_requirements=(config.adapter,),
        artifact_hashes=hashes,
        synthetic=False,
    )
    report = validate_packet(manifest, packet)
    if not report.passed:
        raise IssuePreparationError(
            "prepared packet failed validation: "
            + ", ".join(item.code for item in report.errors)
        )
    diagnostics = {
        "issue_chars": len(issue_text),
        "source_chars": len(source_path.read_text(encoding="utf-8")),
        "source_frame": frame,
        "model_facing_packet_bytes": len(canonical_json(packet.model_visible_payload()).encode("utf-8")),
        "note": "Preparation only. Hidden tests, gold patch and fix commit are excluded.",
    }
    return PreparedIssueCase(
        config=config,
        manifest=manifest,
        packet=packet,
        source_frame=frame,
        packet_validation=report.model_dump(mode="json"),
        diagnostics=diagnostics,
    )


__all__ = [
    "BASE_REVISION",
    "DATASET_REVISION",
    "IssueCaseConfig",
    "IssuePreparationError",
    "PreparedIssueCase",
    "R3",
    "SOURCE_FUNCTION",
    "SOURCE_LINE",
    "SOURCE_PATH",
    "prepare_issue_case",
]
