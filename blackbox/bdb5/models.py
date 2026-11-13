"""Validated data models for the BDB-5 offline evaluation harness.

The models deliberately keep three objects separate:

* ``CaseManifest``: frozen case definition and readiness state.
* ``EvidencePacket``: model-visible material only.
* ``GroundTruth``: evaluator-only labels.

There is no field on ``EvidencePacket`` that can hold a ground-truth object, and
``GroundTruth`` has no model-visible serializer.
"""
from __future__ import annotations

import re
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
FAULT = re.compile(r"^F[1-5]$")


def _relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or ":" in value
        or value.startswith("-")
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in value.split("/"))
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError("path must be a repository-relative POSIX path")
    return value


def _safe_id(value: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ValueError("identifier must match [A-Za-z][A-Za-z0-9_.:-]{0,127}")
    return value


def _unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")
    return values


class CaseId(str, Enum):
    T1 = "BDB5-T1"
    R1 = "BDB5-R1"
    R2 = "BDB5-R2"
    R3 = "BDB5-R3"
    P1 = "BDB5-P1"


class Readiness(str, Enum):
    SELECTED = "SELECTED"
    PREPARATION_BLOCKED = "PREPARATION_BLOCKED"
    PREPARED = "PREPARED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED_FOR_EVALUATION = "APPROVED_FOR_EVALUATION"


class CaseCategory(str, Enum):
    TELEMETRY = "TELEMETRY"
    CI_SOURCE = "CI_SOURCE"
    NEGATIVE_CONTROL = "NEGATIVE_CONTROL"
    ISSUE_SOURCE = "ISSUE_SOURCE"
    REPAIR = "REPAIR"


class EvidenceType(str, Enum):
    TELEMETRY_METRIC = "TELEMETRY_METRIC"
    TELEMETRY_LOG = "TELEMETRY_LOG"
    CI_LOG = "CI_LOG"
    SOURCE_EXCERPT = "SOURCE_EXCERPT"
    ISSUE_TEXT = "ISSUE_TEXT"
    TEST_RESULT = "TEST_RESULT"
    HARNESS_NOTE = "HARNESS_NOTE"
    PATCH_DIFF = "PATCH_DIFF"
    OTHER = "OTHER"


class ClaimCategory(str, Enum):
    OBSERVATION = "OBSERVATION"
    SERVICE_CAUSE = "SERVICE_CAUSE"
    SOURCE_CAUSE = "SOURCE_CAUSE"
    MECHANISM = "MECHANISM"
    APPLICATION_SOURCE_CAUSE = "APPLICATION_SOURCE_CAUSE"
    HARNESS_CAUSE = "HARNESS_CAUSE"
    PATCH = "PATCH"
    TEST_EXECUTION = "TEST_EXECUTION"
    ABSTENTION = "ABSTENTION"
    OTHER = "OTHER"


class CausalStatus(str, Enum):
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    SUPPORTED = "SUPPORTED"
    ESTABLISHED = "ESTABLISHED"
    NOT_ASSESSED = "NOT_ASSESSED"


class AbstentionScope(str, Enum):
    SOURCE = "SOURCE"
    APPLICATION_SOURCE = "APPLICATION_SOURCE"
    ALL = "ALL"


class TestOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    NOT_RUN = "NOT_RUN"


class TestRole(str, Enum):
    FAIL_TO_PASS = "FAIL_TO_PASS"
    PASS_TO_PASS = "PASS_TO_PASS"
    REPRODUCTION_BEFORE = "REPRODUCTION_BEFORE"
    REPRODUCTION_AFTER = "REPRODUCTION_AFTER"
    REGRESSION = "REGRESSION"
    OTHER = "OTHER"


class EvaluationMode(str, Enum):
    SYNTHETIC_DRY_RUN = "SYNTHETIC_DRY_RUN"
    REAL_CASE_EVALUATION = "REAL_CASE_EVALUATION"


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class EvidenceItem(BaseModel):
    """One content-addressed, public evidence item."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    evidence_type: EvidenceType
    text: str = Field(default="", max_length=20_000)
    structured: dict[str, Any] | None = None
    source_revision: str | None = None

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("source_revision")
    @classmethod
    def validate_source_revision(cls, value: str | None) -> str | None:
        if value is not None and not HEX40.fullmatch(value):
            raise ValueError("source_revision must be a 40-character lowercase Git SHA")
        return value

    @model_validator(mode="after")
    def has_content(self):
        if not self.text.strip() and self.structured is None:
            raise ValueError("evidence requires text or structured content")
        return self


class EvidencePacket(BaseModel):
    """The complete model-visible packet.

    Candidate names are intentionally allowed here. A bare candidate name that
    equals a hidden label is not leakage; target markers and target coupling are
    checked by ``validation.py``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: CaseId
    schema_version: Literal["bdb5-evidence-v1"] = "bdb5-evidence-v1"
    task_instructions: str = Field(min_length=1, max_length=20_000)
    evidence: tuple[EvidenceItem, ...] = Field(min_length=1)
    candidate_inventory: tuple[str, ...] = ()
    source_revision: str | None = None
    artifact_hashes: dict[str, str] = Field(default_factory=dict)

    @field_validator("source_revision")
    @classmethod
    def validate_source_revision(cls, value: str | None) -> str | None:
        if value is not None and not HEX40.fullmatch(value):
            raise ValueError("source_revision must be a 40-character lowercase Git SHA")
        return value

    @field_validator("candidate_inventory")
    @classmethod
    def validate_candidates(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "candidate_inventory")
        if value != tuple(sorted(value)):
            raise ValueError("candidate_inventory must be lexicographically sorted and unranked")
        for item in value:
            if not item.strip() or len(item) > 256:
                raise ValueError("candidate names must be short non-empty strings")
        return value

    @field_validator("artifact_hashes")
    @classmethod
    def validate_artifact_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        for key, digest in value.items():
            _safe_id(key)
            if not HEX64.fullmatch(digest):
                raise ValueError(f"artifact hash for {key} must be a 64-character SHA-256")
        return value

    @model_validator(mode="after")
    def unique_evidence_ids(self):
        ids = tuple(item.evidence_id for item in self.evidence)
        _unique(ids, "evidence identifiers")
        return self

    def model_visible_payload(self) -> dict[str, Any]:
        """Serialize exactly the fields permitted in a model-facing prompt."""
        return {
            "case_id": self.case_id.value,
            "schema_version": self.schema_version,
            "task_instructions": self.task_instructions,
            "evidence": [item.model_dump(mode="json") for item in self.evidence],
            "candidate_inventory": list(self.candidate_inventory),
            "source_revision": self.source_revision,
            "artifact_hashes": dict(sorted(self.artifact_hashes.items())),
        }


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: ClaimCategory
    text: str = Field(min_length=1, max_length=4_000)
    evidence_ids: tuple[str, ...] = ()
    material: bool = True
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    uncertainty: str | None = Field(default=None, max_length=2_000)
    asserts_execution: bool = False

    @field_validator("evidence_ids")
    @classmethod
    def unique_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "claim evidence_ids")
        for item in value:
            _safe_id(item)
        return value


class Abstention(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: AbstentionScope
    reason: str = Field(min_length=1, max_length=4_000)
    missing_evidence: tuple[str, ...] = ()
    source_not_established: bool = False
    application_source_not_established: bool = False

    @field_validator("missing_evidence")
    @classmethod
    def unique_missing_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "missing_evidence")
        return value

    @model_validator(mode="after")
    def explicit_scope(self):
        if self.scope in (AbstentionScope.SOURCE, AbstentionScope.ALL) and not self.source_not_established:
            raise ValueError("SOURCE abstention must explicitly state source cause is not established")
        if self.scope in (AbstentionScope.APPLICATION_SOURCE, AbstentionScope.ALL) and not self.application_source_not_established:
            raise ValueError("APPLICATION_SOURCE abstention must explicitly state application source is not established")
        return self


class TestExecution(BaseModel):
    """A recorded test observation.

    ``artifact_sha256`` is the only evidence that makes an execution count as
    recorded. A PASS without it is deliberately representable so scoring can
    flag it as an execution overclaim instead of silently accepting it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: TestRole = TestRole.OTHER
    name: str = Field(min_length=1, max_length=512)
    outcome: TestOutcome
    artifact_sha256: str | None = None
    command: str | None = Field(default=None, max_length=2_000)
    failure_signature_matched: bool | None = None

    @field_validator("artifact_sha256")
    @classmethod
    def validate_artifact(cls, value: str | None) -> str | None:
        if value is not None and not HEX64.fullmatch(value):
            raise ValueError("artifact_sha256 must be a 64-character SHA-256")
        return value

    @property
    def recorded(self) -> bool:
        return self.artifact_sha256 is not None


class PatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    applied: bool = False
    changed_files: tuple[str, ...] = ()
    tests_modified: bool = False
    diff_sha256: str | None = None

    @field_validator("changed_files")
    @classmethod
    def validate_changed_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "changed_files")
        for item in value:
            _relative_path(item)
        return value

    @field_validator("diff_sha256")
    @classmethod
    def validate_diff_hash(cls, value: str | None) -> str | None:
        if value is not None and not HEX64.fullmatch(value):
            raise ValueError("diff_sha256 must be a 64-character SHA-256")
        return value


class InvestigationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: CaseId
    claims: tuple[Claim, ...] = ()
    service_ranked: tuple[str, ...] = ()
    fault_class: str | None = None
    predicted_files: tuple[str, ...] = ()
    predicted_function: str | None = Field(default=None, max_length=512)
    predicted_line: int | None = Field(default=None, ge=1, le=10_000_000)
    predicted_mechanism: str | None = Field(default=None, max_length=8_000)
    mechanism_evidence_ids: tuple[str, ...] = ()
    l1_causal_status: CausalStatus = CausalStatus.NOT_ASSESSED
    l2_causal_status: CausalStatus = CausalStatus.NOT_ASSESSED
    abstention: Abstention | None = None
    patch: PatchRecord | None = None
    test_executions: tuple[TestExecution, ...] = ()
    claimed_source_revision: str | None = None

    @field_validator("service_ranked")
    @classmethod
    def unique_ranked_services(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "service_ranked")
        return value

    @field_validator("fault_class")
    @classmethod
    def validate_fault_class(cls, value: str | None) -> str | None:
        if value is not None and not FAULT.fullmatch(value):
            raise ValueError("fault_class must be one of F1..F5")
        return value

    @field_validator("predicted_files")
    @classmethod
    def validate_predicted_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "predicted_files")
        for item in value:
            _relative_path(item)
        return value

    @field_validator("mechanism_evidence_ids")
    @classmethod
    def unique_mechanism_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "mechanism_evidence_ids")
        for item in value:
            _safe_id(item)
        return value

    @field_validator("claimed_source_revision")
    @classmethod
    def validate_claimed_revision(cls, value: str | None) -> str | None:
        if value is not None and not HEX40.fullmatch(value):
            raise ValueError("claimed_source_revision must be a 40-character lowercase Git SHA")
        return value

    @model_validator(mode="after")
    def unique_test_records(self):
        keys = [(item.role.value, item.name) for item in self.test_executions]
        if len(keys) != len(set(keys)):
            raise ValueError("test_executions must be unique by role and name")
        return self


class PatchExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed_files: tuple[str, ...] = Field(min_length=1)
    fail_to_pass: tuple[str, ...] = ()
    pass_to_pass: tuple[str, ...] = ()
    require_reproduction_before: bool = True
    require_reproduction_after: bool = True
    require_regression: bool = True

    @field_validator("allowed_files", "fail_to_pass", "pass_to_pass")
    @classmethod
    def unique_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "patch expectation values")
        return value


class GroundTruth(BaseModel):
    """Evaluator-only truth. Never serialize this into a model-visible packet."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: CaseId
    expected_service: str | None = None
    expected_fault_class: str | None = None
    expected_files: tuple[str, ...] = ()
    expected_function: str | None = Field(default=None, max_length=512)
    expected_line: int | None = Field(default=None, ge=1, le=10_000_000)
    expected_mechanism: str | None = Field(default=None, max_length=8_000)
    mechanism_term_groups: tuple[tuple[str, ...], ...] = ()
    expected_harness_terms: tuple[str, ...] = ()
    causal_level: Literal["L0", "L1", "L2", "L3", "L4", "NA"] = "NA"
    expected_l1_status: CausalStatus = CausalStatus.NOT_ASSESSED
    expected_l2_status: CausalStatus = CausalStatus.NOT_ASSESSED
    expected_abstention: bool = False
    expected_abstention_scope: AbstentionScope | None = None
    expected_abstention_evidence: tuple[str, ...] = ()
    require_reproduction_before: bool = False
    require_reproduction_after: bool = False
    require_regression: bool = False
    expected_patch: PatchExpectation | None = None
    forbidden_public_literals: tuple[str, ...] = ()

    @field_validator("expected_fault_class")
    @classmethod
    def validate_fault(cls, value: str | None) -> str | None:
        if value is not None and not FAULT.fullmatch(value):
            raise ValueError("expected_fault_class must be one of F1..F5")
        return value

    @field_validator("expected_files")
    @classmethod
    def validate_expected_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "expected_files")
        for item in value:
            _relative_path(item)
        return value

    @field_validator("mechanism_term_groups")
    @classmethod
    def validate_groups(cls, value: tuple[tuple[str, ...], ...]) -> tuple[tuple[str, ...], ...]:
        for group in value:
            if not group or any(not term.strip() for term in group):
                raise ValueError("each mechanism group must contain non-empty terms")
        return value

    @model_validator(mode="after")
    def consistent_abstention(self):
        if self.expected_abstention and self.expected_abstention_scope is None:
            raise ValueError("expected_abstention requires an expected_abstention_scope")
        return self

    def model_visible(self) -> None:
        raise TypeError("ground truth is evaluator-only and has no model-visible serialization")


class CaseManifest(BaseModel):
    """Frozen case definition.

    The model is immutable. There is intentionally no method that moves a case
    to ``APPROVED_FOR_EVALUATION``; approval must be constructed explicitly by
    the caller and is checked by the engine.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["bdb5-case-v1"] = "bdb5-case-v1"
    evaluation_schema_version: Literal["bdb5-eval-v1"] = "bdb5-eval-v1"
    case_id: CaseId
    dataset: str = Field(min_length=1, max_length=256)
    dataset_revision: str = Field(min_length=1, max_length=128)
    repository: str | None = Field(default=None, max_length=512)
    source_revision: str | None = None
    case_category: CaseCategory
    required_evidence_types: tuple[EvidenceType, ...] = Field(min_length=1)
    allowed_files: tuple[str, ...] = ()
    allowed_scope: tuple[str, ...] = ()
    required_dimensions: tuple[str, ...] = Field(min_length=1)
    readiness: Readiness = Readiness.SELECTED
    adapter_requirements: tuple[str, ...] = ()
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    synthetic: bool = False

    @field_validator("source_revision")
    @classmethod
    def validate_source_revision(cls, value: str | None) -> str | None:
        if value is not None and not HEX40.fullmatch(value):
            raise ValueError("source_revision must be a 40-character lowercase Git SHA")
        return value

    @field_validator("required_evidence_types")
    @classmethod
    def unique_evidence_types(cls, value: tuple[EvidenceType, ...]) -> tuple[EvidenceType, ...]:
        if len(value) != len(set(value)):
            raise ValueError("required_evidence_types must not contain duplicates")
        return value

    @field_validator("allowed_files")
    @classmethod
    def validate_allowed_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "allowed_files")
        for item in value:
            _relative_path(item)
        return value

    @field_validator("allowed_scope", "required_dimensions", "adapter_requirements")
    @classmethod
    def unique_manifest_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "manifest values")
        for item in value:
            if not item.strip():
                raise ValueError("manifest values must be non-empty")
        return value

    @field_validator("artifact_hashes")
    @classmethod
    def validate_artifact_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        for key, digest in value.items():
            _safe_id(key)
            if not HEX64.fullmatch(digest):
                raise ValueError(f"artifact hash for {key} must be a 64-character SHA-256")
        return value

    @model_validator(mode="after")
    def approved_has_artifacts(self):
        if self.readiness == Readiness.APPROVED_FOR_EVALUATION and not self.artifact_hashes:
            raise ValueError("an approved case requires at least one artifact hash")
        return self

    @property
    def runnable(self) -> bool:
        return self.readiness == Readiness.APPROVED_FOR_EVALUATION


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=128)
    severity: ValidationSeverity
    detail: str = Field(min_length=1, max_length=8_000)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR)

    @property
    def passed(self) -> bool:
        return not self.errors

    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)


class CaseScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: str | None = None
    case_id: CaseId
    synthetic: bool
    mode: EvaluationMode = EvaluationMode.SYNTHETIC_DRY_RUN
    result_class: Literal[
        "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT",
        "REAL_CASE_SCORE_NOT_BENCHMARK_RESULT",
    ] = "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT"
    dimensions: dict[str, bool | int | float | str | None]
    dimension_explanations: dict[str, str]
    required_dimensions: tuple[str, ...]
    strict_pass: bool
    failures: tuple[str, ...]
    citations: dict[str, Any]
    validation_issues: tuple[ValidationIssue, ...] = ()
    result_hash: str

    @field_validator("result_hash")
    @classmethod
    def validate_result_hash(cls, value: str) -> str:
        if not HEX64.fullmatch(value):
            raise ValueError("result_hash must be a 64-character SHA-256")
        return value


class SuiteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: EvaluationMode = EvaluationMode.SYNTHETIC_DRY_RUN
    result_class: Literal[
        "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT",
        "REAL_CASE_SCORE_NOT_BENCHMARK_RESULT",
    ] = "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT"
    cases: tuple[CaseScore, ...]
    dimension_summary: dict[str, dict[str, int]]
    strict_pass_count: int = Field(ge=0)
    case_count: int = Field(ge=0)
    suite_hash: str

    @field_validator("suite_hash")
    @classmethod
    def validate_suite_hash(cls, value: str) -> str:
        if not HEX64.fullmatch(value):
            raise ValueError("suite_hash must be a 64-character SHA-256")
        return value


class SyntheticScenario(BaseModel):
    """A fully synthetic, in-memory case used only for offline dry-run tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    manifest: CaseManifest
    packet: EvidencePacket
    truth: GroundTruth
    result: InvestigationResult
    expected_strict_pass: bool
    expected_issues: tuple[str, ...] = ()
