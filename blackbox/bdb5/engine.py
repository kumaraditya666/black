"""Offline BDB-5 evaluation orchestration.

Only synthetic, explicitly approved manifests can be evaluated. Real cases
remain blocked even if a scorer exists for their category.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from .errors import (
    BlockedCaseError,
    ManifestValidationError,
    PacketValidationError,
    UnsupportedModeError,
)
from .models import (
    CaseManifest,
    CaseScore,
    EvaluationMode,
    EvidencePacket,
    GroundTruth,
    InvestigationResult,
    Readiness,
    SuiteResult,
    SyntheticScenario,
)
from .scoring import digest, score_case
from .spec import STRICT_RULES
from .validation import validate_manifest, validate_packet, validate_result


def _ensure_evaluable(manifest: CaseManifest, mode: EvaluationMode) -> None:
    if mode != EvaluationMode.SYNTHETIC_DRY_RUN:
        raise UnsupportedModeError("only SYNTHETIC_DRY_RUN is implemented")
    if not manifest.synthetic:
        raise BlockedCaseError("real cases are not enabled in this offline harness")
    if manifest.readiness != Readiness.APPROVED_FOR_EVALUATION:
        raise BlockedCaseError(
            f"case {manifest.case_id.value} is {manifest.readiness.value}, not APPROVED_FOR_EVALUATION"
        )


def evaluate_case(manifest: CaseManifest, packet: EvidencePacket, truth: GroundTruth,
                  result: InvestigationResult, *, scenario: str | None = None,
                  mode: EvaluationMode = EvaluationMode.SYNTHETIC_DRY_RUN) -> CaseScore:
    """Validate and score one synthetic case.

    A blocked or non-synthetic case raises before any scoring. Hard packet
    leakage raises instead of being converted into a score.
    """
    _ensure_evaluable(manifest, mode)
    manifest_report = validate_manifest(manifest)
    if not manifest_report.passed:
        raise ManifestValidationError("; ".join(item.code for item in manifest_report.errors))
    packet_report = validate_packet(manifest, packet, truth)
    if not packet_report.passed:
        raise PacketValidationError("; ".join(item.code for item in packet_report.errors))
    result_report = validate_result(manifest, packet, result)
    return score_case(manifest, packet, truth, result, result_report, scenario=scenario)


def evaluate_suite(scenarios: Iterable[SyntheticScenario], *,
                   mode: EvaluationMode = EvaluationMode.SYNTHETIC_DRY_RUN) -> SuiteResult:
    cases: list[CaseScore] = []
    for scenario in scenarios:
        cases.append(evaluate_case(
            scenario.manifest, scenario.packet, scenario.truth, scenario.result,
            scenario=scenario.name, mode=mode,
        ))
    dimension_summary: dict[str, dict[str, int]] = {}
    names = sorted({name for case in cases for name in case.dimensions})
    for name in names:
        counts: Counter[str] = Counter()
        for case in cases:
            value = case.dimensions.get(name)
            if value is None:
                counts["N/A"] += 1
            elif name in STRICT_RULES:
                from .scoring import _strict_ok
                counts["PASS" if _strict_ok(name, value) else "FAIL"] += 1
            else:
                counts["OBSERVED"] += 1
        dimension_summary[name] = {key: counts[key] for key in ("PASS", "FAIL", "N/A", "OBSERVED") if counts[key]}
    payload = {
        "mode": mode.value,
        "result_class": "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT",
        "cases": [case.model_dump(mode="json") for case in cases],
        "dimension_summary": dimension_summary,
        "strict_pass_count": sum(1 for case in cases if case.strict_pass),
        "case_count": len(cases),
    }
    return SuiteResult(**payload, suite_hash=digest(payload))
