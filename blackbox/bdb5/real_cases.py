"""Preparation-only BugSwarm R1/R2 adapters.

This module turns a recorded Travis CI log into a deterministic BDB-5
``CaseManifest`` and ``EvidencePacket``. It deliberately does not:

* import the investigator, providers, repair pipeline, or M4B.3 ledger;
* call a model;
* approve a real case; or
* execute a repository, test, patch, or container.

The source resolver is injected by the caller. That keeps this package
independent of ``blackbox.source`` while still allowing the CLI to verify a
source revision through Git.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from .errors import BlockedCaseError
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


ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
HEADER = re.compile(
    r"^(ERROR|FAIL): ([A-Za-z_][A-Za-z0-9_.]*)(?: \(([^)]+)\))?\s*$"
)
FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+), in ([^\s]+)\s*$')
SUMMARY = re.compile(r"^Ran (\d+) tests? in .+$")
RESULT = re.compile(r"^(FAILED|OK)(?: \((.+)\))?\s*$")
EXIT = re.compile(r'The command ".*" exited with (\d+)\.')

SOURCE_READER = Callable[[Path | None, str, dict[str, Any]], dict[str, Any]]
SourceRole = Literal["application", "test"]


@dataclass(frozen=True)
class CiFailure:
    kind: str
    test: str
    class_name: str | None
    frames: tuple[dict[str, Any], ...]
    exception: str
    text: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class CiLog:
    text: str
    test_count: int | None
    summary: str | None
    exit_code: int | None
    failures: tuple[CiFailure, ...]

    def failure(self, test_name: str) -> CiFailure:
        for failure in self.failures:
            if failure.test == test_name:
                return failure
        raise ValueError(f"CI log does not contain failure {test_name!r}")


@dataclass(frozen=True)
class CiCaseConfig:
    case_id: CaseId
    dataset: str
    dataset_revision: str
    repository: str
    source_revision: str
    case_category: CaseCategory
    required_evidence_types: tuple[EvidenceType, ...]
    required_dimensions: tuple[str, ...]
    allowed_files: tuple[str, ...]
    allowed_scope: tuple[str, ...]
    primary_test: str
    source_role: SourceRole
    task_instructions: str
    adapter: str


R1 = CiCaseConfig(
    case_id=CaseId.R1,
    dataset="BugSwarm",
    dataset_revision="bwhmather-verktyg-109227527",
    repository="https://github.com/bwhmather/verktyg",
    source_revision="71dc420c22fadbae064c46b426e093bec7b86f32",
    case_category=CaseCategory.CI_SOURCE,
    required_evidence_types=(EvidenceType.CI_LOG, EvidenceType.SOURCE_EXCERPT),
    required_dimensions=(
        "file_exactness",
        "function_exactness",
        "line_exactness",
        "mechanism",
        "causal_status",
        "citation_validity",
        "reproduction_before",
        "unsupported_claim_rate",
    ),
    allowed_files=("verktyg/requests.py",),
    allowed_scope=("source",),
    primary_test="test_modified_url_encoding",
    source_role="application",
    task_instructions=(
        "Investigate the recorded CI failure. Identify the source mechanism and cite "
        "the supplied evidence. Distinguish a static mechanism from an established "
        "runtime cause; do not assume the client-reported frames executed."
    ),
    adapter="bugswarm-ci-log-v1",
)

R2 = CiCaseConfig(
    case_id=CaseId.R2,
    dataset="BugSwarm",
    dataset_revision="marshallward-f90nml-83523531",
    repository="https://github.com/marshallward/f90nml",
    source_revision="d8d88884dea251fc1d9e63b9afcf19b81a785066",
    case_category=CaseCategory.NEGATIVE_CONTROL,
    required_evidence_types=(EvidenceType.CI_LOG, EvidenceType.TEST_RESULT),
    required_dimensions=(
        "app_causal_status",
        "app_abstention",
        "app_source_claim",
        "citation_validity",
        "reproduction_before",
        "unsupported_claim_rate",
    ),
    allowed_files=(),
    allowed_scope=("test-harness",),
    primary_test="test_dict_write",
    source_role="test",
    task_instructions=(
        "Investigate the recorded CI failure. State whether an application-source "
        "cause is established and separately identify any test-harness or fixture "
        "cause supported by the evidence. Do not convert a harness failure into an "
        "application-source claim."
    ),
    adapter="bugswarm-ci-log-v1",
)

CASES: dict[CaseId, CiCaseConfig] = {CaseId.R1: R1, CaseId.R2: R2}


@dataclass(frozen=True)
class PreparedCiCase:
    config: CiCaseConfig
    manifest: CaseManifest
    packet: EvidencePacket
    primary_failure: CiFailure
    source_frame: dict[str, Any] | None
    source_status: str | None
    packet_validation: dict[str, Any]
    diagnostics: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        """Return preparation-only JSON. This contains no evaluator labels."""
        return {
            "mode": "REAL_CASE_PREPARATION_ONLY",
            "model_calls": 0,
            "case_id": self.config.case_id.value,
            "readiness": self.manifest.readiness.value,
            # Only this value is intended for a future model-facing prompt.
            "model_visible_packet": self.packet.model_visible_payload(),
            # Manifest, labels, source requirements and validation stay evaluator-only.
            "evaluator_only": {
                "manifest": self.manifest.model_dump(mode="json"),
                "primary_failure": {
                    "kind": self.primary_failure.kind,
                    "test": self.primary_failure.test,
                    "class_name": self.primary_failure.class_name,
                    "exception": self.primary_failure.exception,
                    "frame": self.source_frame,
                },
                "source_status": self.source_status,
                "packet_validation": self.packet_validation,
                "diagnostics": self.diagnostics,
            },
            "payload_hash": digest({
                "case_id": self.config.case_id.value,
                "manifest": self.manifest.model_dump(mode="json"),
                "packet": self.packet.model_visible_payload(),
                "primary_failure": self.primary_failure.text,
                "source_status": self.source_status,
            }),
        }


class PreparationError(ValueError):
    """A real case cannot be prepared safely or deterministically."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalise_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return ANSI.sub("", text)


def _sanitise_ci_text(text: str) -> str:
    """Remove host/container paths from model-visible CI text.

    The raw log remains an artifact outside the packet. The model sees only
    repository-relative paths and generic CI-home/stdlib markers.
    """
    text = _normalise_text(text)
    text = re.sub(r"/home/travis/build/[^/\s]+/[^/\s]+/", "", text)
    text = re.sub(r"/home/travis/", "ci-home/", text)
    text = re.sub(r"/opt/python/[^/\s]+/lib/python[^/\s]+/", "stdlib/", text)
    text = re.sub(r"/tmp/", "ci-tmp/", text)
    text = re.sub(r"[A-Za-z]:\\[^\s\"']*", "ci-home/", text)
    return text


def _normalise_path(raw: str) -> str:
    path = raw.replace("\\", "/")
    if "/bwhmather/verktyg/" in path:
        path = path.split("/bwhmather/verktyg/", 1)[1]
    elif "/marshallward/f90nml/" in path:
        path = path.split("/marshallward/f90nml/", 1)[1]
    path = path.lstrip("./")
    return path


def _is_test_path(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return (
        "testsuite" in parts
        or "tests" in parts
        or "test" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def parse_ci_log(text: str) -> CiLog:
    """Parse a Travis build log into failure records without guessing labels."""
    normal = _normalise_text(text)
    lines = normal.splitlines()
    test_count: int | None = None
    summary: str | None = None
    exit_code: int | None = None
    headers: list[tuple[int, re.Match[str]]] = []

    for index, line in enumerate(lines):
        match = SUMMARY.match(line)
        if match:
            test_count = int(match.group(1))
        result = RESULT.match(line)
        if result:
            summary = result.group(1) + (f" ({result.group(2)})" if result.group(2) else "")
        exit_match = EXIT.search(line)
        if exit_match:
            exit_code = int(exit_match.group(1))
        header = HEADER.match(line)
        if header:
            headers.append((index, header))

    failures: list[CiFailure] = []
    for position, (start, header) in enumerate(headers):
        end = len(lines)
        for later_start, _ in headers[position + 1:]:
            end = later_start
            break
        for index in range(start + 1, end):
            if SUMMARY.match(lines[index]) or RESULT.match(lines[index]):
                end = index
                break
        block = lines[start:end]
        frames: list[dict[str, Any]] = []
        for index, line in enumerate(block):
            frame_match = FRAME.match(line)
            if not frame_match:
                continue
            source_line = None
            if index + 1 < len(block):
                candidate = block[index + 1]
                if candidate.startswith("    ") and not FRAME.match(candidate):
                    source_line = candidate.strip()
            raw_path = frame_match.group(1)
            path = _normalise_path(raw_path)
            frames.append({
                "path": path,
                "line": int(frame_match.group(2)),
                "function": frame_match.group(3),
                "source_line": source_line,
                "stdlib": raw_path.startswith("/opt/python/") or path.startswith("stdlib/"),
                "test_file": _is_test_path(path),
            })

        exception = ""
        for line in reversed(block):
            stripped = line.strip()
            if not stripped or stripped.startswith("=") or stripped.startswith("-"):
                continue
            if line[:1].isspace() or HEADER.match(line) or FRAME.match(line):
                continue
            if stripped == "Traceback (most recent call last):":
                continue
            exception = stripped
            break
        if not exception:
            raise PreparationError(f"could not identify exception for {header.group(2)}")

        failures.append(CiFailure(
            kind=header.group(1),
            test=header.group(2),
            class_name=header.group(3),
            frames=tuple(frames),
            exception=exception,
            text="\n".join(block).strip(),
            start_line=start + 1,
            end_line=end,
        ))

    return CiLog(
        text=normal,
        test_count=test_count,
        summary=summary,
        exit_code=exit_code,
        failures=tuple(failures),
    )


def _primary_source_frame(failure: CiFailure, role: SourceRole) -> dict[str, Any]:
    candidates = [frame for frame in failure.frames if not frame["stdlib"]]
    if role == "application":
        candidates = [frame for frame in candidates if not frame["test_file"]]
    else:
        candidates = [frame for frame in candidates if frame["test_file"]]
    if not candidates:
        raise PreparationError(
            f"{failure.test!r} has no {role} source frame; refusing to invent one"
        )
    # The recorded order is innermost first. For a test-harness case, the last
    # test frame is the assertion that opens the missing fixture.
    return candidates[-1]


def _bounded_excerpt(log: CiLog, failure: CiFailure, limit: int = 12_000) -> str:
    lines = log.text.splitlines()
    before = max(0, failure.start_line - 1 - 4)
    after = min(len(lines), failure.end_line + 2)
    excerpt = "\n".join(lines[before:after])
    sanitised = _sanitise_ci_text(excerpt)
    if len(sanitised) > limit:
        sanitised = sanitised[:limit] + "\n... [CI excerpt truncated] ..."
    return sanitised


def _source_text(frame: dict[str, Any], source: dict[str, Any]) -> str:
    if source.get("status") != "resolved":
        raise PreparationError(
            f"source frame {frame['path']}:{frame['line']} did not resolve: "
            f"{source.get('reason', 'unknown reason')}"
        )
    context = source.get("context") or []
    body = "\n".join(
        f"{item.get('line')}: {item.get('text')}" for item in context
        if isinstance(item, dict) and item.get("text") is not None
    )
    if not body:
        body = f"{source.get('line')}: {source.get('source_line', '')}"
    return _sanitise_ci_text(
        f"{source.get('path')}:{source.get('line')} in {source.get('function')}\n{body}"
    )[:20_000]


def _test_text(log: CiLog, failure: CiFailure) -> str:
    return _sanitise_ci_text(
        f"Recorded CI result: {log.test_count or 'unknown'} tests; "
        f"{log.summary or 'unknown result'}; primary failure {failure.test} "
        f"({failure.kind}).\n{failure.exception}"
    )[:20_000]


def _artifacts(log_text: str, packet: EvidencePacket) -> dict[str, str]:
    hashes = {"artifact:full-log": _sha(log_text)}
    for item in packet.evidence:
        key = "artifact:" + item.evidence_id.replace(":", "-")
        hashes[key] = _sha(
            f"{packet.case_id.value}|{item.evidence_id}|"
            f"{item.evidence_type.value}|{item.text}|{canonical_json(item.structured)}"
        )
    return hashes


def prepare_ci_case(
    log_text: str,
    config: CiCaseConfig,
    *,
    repo: Path | None = None,
    source_reader: SOURCE_READER | None = None,
) -> PreparedCiCase:
    """Build a deterministic preparation package for one BugSwarm case.

    The result is ``PREPARED``, never approved. The synthetic-only engine will
    still refuse it. A source reader is required for R1 because the manifest
    requires a resolved source excerpt.
    """
    log = parse_ci_log(log_text)
    failure = log.failure(config.primary_test)
    frame = _primary_source_frame(failure, config.source_role)

    if config.case_id == CaseId.R1:
        if source_reader is None:
            raise PreparationError("R1 preparation requires an injected source reader")
        source = source_reader(repo, config.source_revision, frame)
        source_status = str(source.get("status"))
        source_text = _source_text(frame, source)
        source_item = EvidenceItem(
            evidence_id="source:1",
            evidence_type=EvidenceType.SOURCE_EXCERPT,
            text=source_text,
            structured={
                "path": source.get("path", frame["path"]),
                "line": source.get("line", frame["line"]),
                "function": source.get("function", frame["function"]),
                "status": source.get("status"),
            },
            source_revision=config.source_revision,
        )
    else:
        source = None
        source_status = None
        source_item = None

    evidence: list[EvidenceItem] = [
        EvidenceItem(
            evidence_id="ci:1",
            evidence_type=EvidenceType.CI_LOG,
            text=_bounded_excerpt(log, failure),
            structured={
                "job": config.dataset_revision,
                "test_count": log.test_count,
                "summary": log.summary,
                "primary_test": failure.test,
                "failure_kind": failure.kind,
                "source_path_normalised": True,
            },
        ),
        EvidenceItem(
            evidence_id="test:1",
            evidence_type=EvidenceType.TEST_RESULT,
            text=_test_text(log, failure),
            structured={
                "job": config.dataset_revision,
                "test_count": log.test_count,
                "summary": log.summary,
                "exit_code": log.exit_code,
                "primary_test": failure.test,
            },
        ),
    ]
    if source_item is not None:
        evidence.append(source_item)

    packet = EvidencePacket(
        case_id=config.case_id,
        task_instructions=config.task_instructions,
        evidence=tuple(evidence),
        source_revision=config.source_revision,
    )
    hashes = _artifacts(log.text, packet)
    packet = packet.model_copy(update={"artifact_hashes": hashes})

    manifest = CaseManifest(
        case_id=config.case_id,
        dataset=config.dataset,
        dataset_revision=config.dataset_revision,
        repository=config.repository,
        source_revision=config.source_revision,
        case_category=config.case_category,
        required_evidence_types=config.required_evidence_types,
        allowed_files=config.allowed_files,
        allowed_scope=config.allowed_scope,
        required_dimensions=config.required_dimensions,
        readiness=Readiness.PREPARED,
        adapter_requirements=(config.adapter,),
        artifact_hashes=hashes,
        synthetic=False,
    )

    report = validate_packet(manifest, packet)
    if not report.passed:
        raise PreparationError(
            "prepared packet failed validation: "
            + ", ".join(item.code for item in report.errors)
        )

    diagnostics = {
        "log_lines": len(log.text.splitlines()),
        "failure_count": len(log.failures),
        "primary_frame": frame,
        "host_paths_removed": True,
        "model_facing_packet_bytes": len(canonical_json(packet.model_visible_payload()).encode("utf-8")),
        "note": "Preparation only. This case is not approved and cannot enter the synthetic engine.",
    }
    return PreparedCiCase(
        config=config,
        manifest=manifest,
        packet=packet,
        primary_failure=failure,
        source_frame=frame,
        source_status=source_status,
        packet_validation=report.model_dump(mode="json"),
        diagnostics=diagnostics,
    )


def ensure_not_approved(prepared: PreparedCiCase) -> None:
    """Guard used by tests and callers that must not promote a case silently."""
    if prepared.manifest.readiness == Readiness.APPROVED_FOR_EVALUATION:
        raise BlockedCaseError("real preparation must never approve a case")
