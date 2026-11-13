"""Static BDB-5 specification facts used by the offline harness.

This module contains no real labels. It records the task-visible fault taxonomy,
the five case identifiers, and the readiness blockers that the harness must not
pretend to resolve.
"""
from __future__ import annotations

from .models import CaseId, Readiness


FAULT_TAXONOMY: dict[str, str] = {
    "F1": "incorrect parameter values",
    "F2": "missing parameters",
    "F3": "missing function call",
    "F4": "incorrect return values",
    "F5": "missing exception handlers",
}

CASE_IDS: tuple[CaseId, ...] = (
    CaseId.T1,
    CaseId.R1,
    CaseId.R2,
    CaseId.R3,
    CaseId.P1,
)

REAL_CASE_READINESS: dict[CaseId, Readiness] = {
    CaseId.T1: Readiness.PREPARED,
    CaseId.R1: Readiness.PREPARED,
    CaseId.R2: Readiness.PREPARED,
    CaseId.R3: Readiness.PREPARED,
    CaseId.P1: Readiness.PREPARED,
}

T1_BLOCKERS: tuple[str, ...] = (
    "the full packet is 1,615,146 provider-counted tokens and needs at least a 1.62M-token context",
)

P1_BLOCKERS: tuple[str, ...] = ()

LIVE_INFERENCE_ENABLED = False

KNOWN_DIMENSIONS: frozenset[str] = frozenset({
    "citation_validity",
    "citation_coverage",
    "fabricated_citations",
    "service_top1",
    "service_top3",
    "fault_accuracy",
    "file_exactness",
    "function_exactness",
    "line_exactness",
    "mechanism",
    "causal_status",
    "l1_causal_status",
    "l2_causal_status",
    "l2_abstention",
    "false_abstention",
    "app_source_claim",
    "harness_claim",
    "app_causal_status",
    "app_abstention",
    "harness_identification",
    "unsupported_claim_rate",
    "execution_overclaims",
    "patch_applies",
    "patch_scope",
    "fail_to_pass",
    "pass_to_pass",
    "reproduction_before",
    "reproduction_after",
    "regression_safety",
})

# The expected value direction for a strict pass. A ``None`` value always
# fails a required dimension. These rules are intentionally explicit rather
# than an aggregate score.
STRICT_RULES: dict[str, tuple[str, float]] = {
    "citation_validity": ("min", 0.9),
    "citation_coverage": ("equals", 1.0),
    "service_top1": ("equals", 1.0),
    "service_top3": ("equals", 1.0),
    "fault_accuracy": ("equals", 1.0),
    "file_exactness": ("equals", 1.0),
    "function_exactness": ("equals", 1.0),
    "line_exactness": ("equals", 1.0),
    "mechanism": ("equals", 1.0),
    "causal_status": ("equals", 1.0),
    "l1_causal_status": ("equals", 1.0),
    "l2_causal_status": ("equals", 1.0),
    "l2_abstention": ("equals", 1.0),
    "false_abstention": ("equals", 0.0),
    "app_source_claim": ("equals", 0.0),
    "app_causal_status": ("equals", 1.0),
    "app_abstention": ("equals", 1.0),
    "harness_identification": ("equals", 1.0),
    "unsupported_claim_rate": ("equals", 0.0),
    "execution_overclaims": ("equals", 0.0),
    "patch_applies": ("equals", 1.0),
    "patch_scope": ("equals", 1.0),
    "fail_to_pass": ("equals", 1.0),
    "pass_to_pass": ("equals", 1.0),
    "reproduction_before": ("equals", 1.0),
    "reproduction_after": ("equals", 1.0),
    "regression_safety": ("equals", 1.0),
}


def run_spec_checks() -> dict:
    """Validate the static specification without reading any dataset label."""
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    check("five_case_ids", len(CASE_IDS) == 5 and len(set(CASE_IDS)) == 5,
          "exactly five unique BDB-5 case IDs")
    check("fault_taxonomy", set(FAULT_TAXONOMY) == {"F1", "F2", "F3", "F4", "F5"},
          "F1-F5 are present")
    check("fault_definitions", tuple(FAULT_TAXONOMY.values()) == (
        "incorrect parameter values", "missing parameters", "missing function call",
        "incorrect return values", "missing exception handlers",
    ), "F1-F5 definitions match the governing taxonomy")
    check("t1_not_approved", REAL_CASE_READINESS[CaseId.T1] != Readiness.APPROVED_FOR_EVALUATION,
          "T1 is not approved for evaluation")
    check("p1_not_approved", REAL_CASE_READINESS[CaseId.P1] != Readiness.APPROVED_FOR_EVALUATION,
          "P1 is not approved for evaluation")
    check("live_disabled", not LIVE_INFERENCE_ENABLED, "live inference remains disabled")
    check("no_real_manifest", True, "this module creates no real case manifest")
    return {
        "status": "PASS" if all(item["ok"] for item in checks) else "FAIL",
        "checks": checks,
        "t1_blockers": list(T1_BLOCKERS),
        "p1_blockers": list(P1_BLOCKERS),
        "live_inference_enabled": LIVE_INFERENCE_ENABLED,
    }
