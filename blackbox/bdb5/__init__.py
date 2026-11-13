"""BDB-5 synthetic offline evaluation harness.

This namespace is independent of the M4B.3 experiment ledger and the restricted
repair pipeline. It contains no live provider or execution path.
"""
from .approval import ApprovalRecord, ReviewerSignoff, build_approval, validate_approval
from .engine import evaluate_case, evaluate_suite
from .errors import BlockedCaseError, ManifestValidationError, PacketValidationError, UnsupportedModeError
from .models import (
    Abstention,
    AbstentionScope,
    CaseCategory,
    CaseId,
    CaseManifest,
    CaseScore,
    CausalStatus,
    Claim,
    ClaimCategory,
    EvaluationMode,
    EvidenceItem,
    EvidencePacket,
    EvidenceType,
    GroundTruth,
    InvestigationResult,
    PatchExpectation,
    PatchRecord,
    Readiness,
    SuiteResult,
    SyntheticScenario,
    TestExecution,
    TestOutcome,
    TestRole,
)
from .label_vault import LabelVault, load_label_vault
from .provider import LiveExecutionGate, OpenAICompatibleProvider, ProviderConfig
from .real_cases import (
    CASES as REAL_CASES,
    PreparationError,
    PreparedCiCase,
    parse_ci_log,
    prepare_ci_case,
)
from .real_score import RealCaseRun, score_approved_case
from .review import PacketReview, review_file, review_payload
from .runner import (
    PreparedCaseRun,
    RunnerError,
    accept_prepared_result,
    run_prepared_case,
)
from .spec import FAULT_TAXONOMY, LIVE_INFERENCE_ENABLED

__all__ = [
    "Abstention", "AbstentionScope", "ApprovalRecord", "BlockedCaseError", "CaseCategory", "CaseId",
    "CaseManifest", "CaseScore", "CausalStatus", "Claim", "ClaimCategory",
    "EvaluationMode", "EvidenceItem", "EvidencePacket", "EvidenceType", "FAULT_TAXONOMY",
    "GroundTruth", "InvestigationResult", "LIVE_INFERENCE_ENABLED", "ManifestValidationError",
    "PacketValidationError", "PatchExpectation", "PatchRecord", "Readiness", "SuiteResult",
    "SyntheticScenario", "TestExecution", "TestOutcome", "TestRole", "UnsupportedModeError",
    "REAL_CASES", "PreparationError", "PreparedCiCase", "parse_ci_log", "prepare_ci_case",
    "LabelVault", "load_label_vault", "LiveExecutionGate", "OpenAICompatibleProvider",
    "ProviderConfig", "ReviewerSignoff", "build_approval", "validate_approval",
    "RealCaseRun", "score_approved_case",
    "PacketReview", "review_file", "review_payload",
    "PreparedCaseRun", "RunnerError", "accept_prepared_result", "run_prepared_case",
    "evaluate_case", "evaluate_suite",
]
