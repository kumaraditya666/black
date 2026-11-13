"""Dimension-based scoring for BDB-5.

There is deliberately no aggregate accuracy value. Every dimension is emitted
with an explanation, missing values stay ``None`` (JSON null), and a strict
case pass is a conjunction of the manifest's required dimensions.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import (
    AbstentionScope,
    CaseId,
    CaseManifest,
    CaseScore,
    CausalStatus,
    ClaimCategory,
    EvaluationMode,
    EvidencePacket,
    GroundTruth,
    InvestigationResult,
    TestOutcome,
    TestRole,
    ValidationReport,
)
from .spec import STRICT_RULES


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _is_test_path(path: str) -> bool:
    parts = path.split("/")
    if "tests" in parts or "test" in parts:
        return True
    name = parts[-1]
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def _citation_audit(manifest: CaseManifest, packet: EvidencePacket,
                    result: InvestigationResult) -> dict[str, Any]:
    cited: list[str] = []
    for claim in result.claims:
        cited.extend(claim.evidence_ids)
    cited.extend(result.mechanism_evidence_ids)
    # Preserve first-seen order for audit output; metrics use sets.
    unique_cited = tuple(dict.fromkeys(cited))
    by_id = {item.evidence_id: item for item in packet.evidence}
    valid = tuple(item for item in unique_cited if item in by_id)
    invalid = tuple(item for item in unique_cited if item not in by_id)
    valid_types = {by_id[item].evidence_type for item in valid}
    required = set(manifest.required_evidence_types)
    validity = len(valid) / len(unique_cited) if unique_cited else 0.0
    fabricated = len(invalid) / len(unique_cited) if unique_cited else None
    coverage = (len(valid_types & required) / len(required)) if required else None
    return {
        "cited": list(unique_cited),
        "valid": list(valid),
        "invalid": list(invalid),
        "validity": round(validity, 12),
        "fabricated_rate": None if fabricated is None else round(fabricated, 12),
        "coverage": None if coverage is None else round(coverage, 12),
        "required_evidence_types": sorted(item.value for item in required),
        "valid_evidence_types": sorted(item.value for item in valid_types),
    }


def _mechanism_score(truth: GroundTruth, packet: EvidencePacket,
                     result: InvestigationResult) -> float | None:
    if not truth.mechanism_term_groups:
        return None
    text_parts = [result.predicted_mechanism or ""]
    text_parts.extend(claim.text for claim in result.claims if claim.category == ClaimCategory.MECHANISM)
    text = " ".join(text_parts).lower()
    matched = 0
    for group in truth.mechanism_term_groups:
        if all(term.lower() in text for term in group):
            matched += 1
    evidence_ids = set(result.mechanism_evidence_ids)
    evidence_ids.update(
        evidence_id
        for claim in result.claims
        if claim.category == ClaimCategory.MECHANISM
        for evidence_id in claim.evidence_ids
    )
    known = {item.evidence_id for item in packet.evidence}
    supported = any(evidence_id in known for evidence_id in evidence_ids)
    if matched == len(truth.mechanism_term_groups) and supported:
        return 1.0
    if matched:
        return 0.5
    return 0.0


def _has_source_claim(result: InvestigationResult) -> bool:
    return any(
        claim.category in (ClaimCategory.SOURCE_CAUSE, ClaimCategory.MECHANISM,
                           ClaimCategory.APPLICATION_SOURCE_CAUSE)
        for claim in result.claims
    )


def _has_app_claim(result: InvestigationResult) -> bool:
    return (
        any(claim.category == ClaimCategory.APPLICATION_SOURCE_CAUSE for claim in result.claims)
        or result.l2_causal_status in (CausalStatus.SUPPORTED, CausalStatus.ESTABLISHED)
    )


def _has_harness_claim(result: InvestigationResult) -> bool:
    return any(claim.category == ClaimCategory.HARNESS_CAUSE for claim in result.claims)


def _has_valid_evidence(claim, known: set[str]) -> bool:
    return bool(claim.evidence_ids) and all(item in known for item in claim.evidence_ids)


def _recorded_execution(result: InvestigationResult, role: TestRole, name: str,
                        outcome: TestOutcome, require_signature: bool = False) -> bool:
    for execution in result.test_executions:
        if execution.role != role or execution.name != name:
            continue
        if execution.outcome != outcome or not execution.recorded:
            continue
        if require_signature and execution.failure_signature_matched is not True:
            continue
        return True
    return False


def _ratio(passed: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(passed / total, 12)


def _strict_ok(name: str, value: Any) -> bool:
    if value is None:
        return False
    if name not in STRICT_RULES:
        return False
    if isinstance(value, bool):
        numeric = 1.0 if value else 0.0
    elif isinstance(value, (int, float)):
        numeric = float(value)
    else:
        return False
    mode, threshold = STRICT_RULES[name]
    if mode == "min":
        return numeric >= threshold
    return numeric == threshold


def _explanations(dimensions: dict[str, Any], truths: GroundTruth) -> dict[str, str]:
    expected = {
        "service_top1": truths.expected_service,
        "fault_accuracy": truths.expected_fault_class,
        "file_exactness": truths.expected_files,
        "function_exactness": truths.expected_function,
        "line_exactness": truths.expected_line,
        "causal_status": truths.expected_l2_status.value,
        "l1_causal_status": truths.expected_l1_status.value,
        "l2_causal_status": truths.expected_l2_status.value,
    }
    output = {}
    for name, value in dimensions.items():
        target = expected.get(name)
        output[name] = f"value={value!r}" + (f"; expected={target!r}" if name in expected else "")
    return output


def score_case(manifest: CaseManifest, packet: EvidencePacket, truth: GroundTruth,
               result: InvestigationResult, validation: ValidationReport,
               scenario: str | None = None, *,
               mode: EvaluationMode = EvaluationMode.SYNTHETIC_DRY_RUN,
               result_class: str = "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT") -> CaseScore:
    """Score one result without averaging dimensions into a single number."""
    known = {item.evidence_id for item in packet.evidence}
    citations = _citation_audit(manifest, packet, result)
    source_claim = _has_source_claim(result)
    app_claim = _has_app_claim(result)
    harness_claim = _has_harness_claim(result)

    expected_service = truth.expected_service
    if expected_service is None:
        service_top1 = None
        service_top3 = None
    else:
        service_top1 = 1.0 if result.service_ranked[:1] == (expected_service,) else 0.0
        service_top3 = 1.0 if expected_service in result.service_ranked[:3] else 0.0

    fault_accuracy = None
    if truth.expected_fault_class is not None:
        fault_accuracy = 1.0 if result.fault_class == truth.expected_fault_class else 0.0

    file_exactness = None
    if truth.expected_files:
        file_exactness = 1.0 if set(result.predicted_files) == set(truth.expected_files) else 0.0
    function_exactness = None
    if truth.expected_function is not None:
        function_exactness = 1.0 if result.predicted_function == truth.expected_function else 0.0
    line_exactness = None
    if truth.expected_line is not None:
        line_exactness = 1.0 if result.predicted_line == truth.expected_line else 0.0

    mechanism = _mechanism_score(truth, packet, result)

    l2_causal_status = None
    causal_status = None
    if truth.expected_l2_status != CausalStatus.NOT_ASSESSED:
        contradicts_abstention = (
            truth.expected_l2_status == CausalStatus.NOT_ESTABLISHED
            and (source_claim or app_claim)
        )
        status_match = result.l2_causal_status == truth.expected_l2_status and not contradicts_abstention
        l2_causal_status = 1.0 if status_match else 0.0
        causal_status = l2_causal_status

    l1_causal_status = None
    if truth.expected_l1_status != CausalStatus.NOT_ASSESSED:
        l1_causal_status = 1.0 if (
            service_top1 == 1.0
            and fault_accuracy == 1.0
            and result.l1_causal_status == truth.expected_l1_status
        ) else 0.0

    abstention = result.abstention
    l2_abstention = None
    if truth.expected_abstention:
        if truth.expected_abstention_scope not in (AbstentionScope.SOURCE, AbstentionScope.ALL):
            l2_abstention = None
        elif (
            abstention is not None
            and abstention.scope in (AbstentionScope.SOURCE, AbstentionScope.ALL)
            and abstention.source_not_established
            and bool(abstention.missing_evidence)
            and not source_claim
            and result.l2_causal_status == CausalStatus.NOT_ESTABLISHED
        ):
            l2_abstention = 1.0
        else:
            l2_abstention = 0.0

    app_abstention = None
    if truth.expected_abstention and truth.expected_abstention_scope in (
        AbstentionScope.APPLICATION_SOURCE, AbstentionScope.ALL
    ):
        app_abstention = 1.0 if (
            abstention is not None
            and abstention.scope in (AbstentionScope.APPLICATION_SOURCE, AbstentionScope.ALL)
            and abstention.application_source_not_established
            and bool(abstention.missing_evidence)
            and not app_claim
            and result.l2_causal_status == CausalStatus.NOT_ESTABLISHED
        ) else 0.0
    elif truth.expected_abstention and truth.expected_abstention_scope == AbstentionScope.SOURCE:
        app_abstention = None

    app_causal_status = None
    if truth.expected_abstention_scope in (AbstentionScope.APPLICATION_SOURCE, AbstentionScope.ALL):
        app_causal_status = 1.0 if (
            result.l2_causal_status == CausalStatus.NOT_ESTABLISHED and not app_claim
        ) else 0.0

    harness_identification = None
    if truth.expected_harness_terms:
        harness_text = " ".join(
            claim.text for claim in result.claims if claim.category == ClaimCategory.HARNESS_CAUSE
        ).lower()
        terms_found = all(term.lower() in harness_text for term in truth.expected_harness_terms)
        harness_evidence = any(
            _has_valid_evidence(claim, known)
            for claim in result.claims
            if claim.category == ClaimCategory.HARNESS_CAUSE
        )
        harness_identification = 1.0 if terms_found and harness_evidence else 0.0

    material = [claim for claim in result.claims if claim.material]
    unsupported_claims = [
        claim for claim in material
        if not _has_valid_evidence(claim, known)
        or (claim.asserts_execution and not any(item.recorded for item in result.test_executions))
    ]
    unsupported_rate = _ratio(len(unsupported_claims), len(material))

    execution_overclaims = sum(
        1 for item in result.test_executions
        if item.outcome == TestOutcome.PASS and not item.recorded
    )
    execution_overclaims += sum(
        1 for claim in result.claims
        if claim.asserts_execution and not any(item.recorded for item in result.test_executions)
    )

    if manifest.case_id == CaseId.T1:
        false_abstention = 0.0 if service_top1 == 1.0 and fault_accuracy == 1.0 else 1.0
    elif manifest.case_id in (CaseId.R1, CaseId.R3):
        false_abstention = 1.0 if result.abstention is not None else 0.0
    else:
        false_abstention = None

    patch_applies = None
    patch_scope = None
    fail_to_pass = None
    pass_to_pass = None
    reproduction_before = None
    reproduction_after = None
    regression_safety = None

    if truth.expected_patch is not None:
        patch = result.patch
        allowed = set(truth.expected_patch.allowed_files)
        changed = set(patch.changed_files) if patch else set()
        test_paths = any(_is_test_path(item) for item in changed)
        patch_applies = 1.0 if patch is not None and patch.applied else 0.0
        patch_scope = 1.0 if (
            patch is not None
            and patch.applied
            and bool(changed)
            and changed <= allowed
            and not patch.tests_modified
            and not test_paths
        ) else 0.0

        if truth.expected_patch.fail_to_pass:
            passed = sum(
                1 for name in truth.expected_patch.fail_to_pass
                if _recorded_execution(result, TestRole.FAIL_TO_PASS, name, TestOutcome.PASS)
            )
            fail_to_pass = _ratio(passed, len(truth.expected_patch.fail_to_pass))
        if truth.expected_patch.pass_to_pass:
            passed = sum(
                1 for name in truth.expected_patch.pass_to_pass
                if _recorded_execution(result, TestRole.PASS_TO_PASS, name, TestOutcome.PASS)
            )
            pass_to_pass = _ratio(passed, len(truth.expected_patch.pass_to_pass))
        if truth.expected_patch.require_reproduction_before:
            reproduction_before = 1.0 if any(
                item.role == TestRole.REPRODUCTION_BEFORE
                and item.outcome == TestOutcome.FAIL
                and item.failure_signature_matched is True
                and item.recorded
                for item in result.test_executions
            ) else 0.0
        if truth.expected_patch.require_reproduction_after:
            reproduction_after = 1.0 if any(
                item.role == TestRole.REPRODUCTION_AFTER
                and item.outcome == TestOutcome.PASS
                and item.recorded
                for item in result.test_executions
            ) else 0.0
        if truth.expected_patch.require_regression:
            regression_safety = 1.0 if (
                patch is not None
                and not patch.tests_modified
                and any(
                    item.role == TestRole.REGRESSION
                    and item.outcome == TestOutcome.PASS
                    and item.recorded
                    for item in result.test_executions
                )
            ) else 0.0
    elif truth.require_reproduction_before:
        reproduction_before = 1.0 if any(
            item.role == TestRole.REPRODUCTION_BEFORE
            and item.outcome == TestOutcome.FAIL
            and item.failure_signature_matched is True
            and item.recorded
            for item in result.test_executions
        ) else 0.0
    if truth.require_reproduction_after and reproduction_after is None:
        reproduction_after = 1.0 if any(
            item.role == TestRole.REPRODUCTION_AFTER
            and item.outcome == TestOutcome.PASS
            and item.recorded
            for item in result.test_executions
        ) else 0.0
    if truth.require_regression and regression_safety is None:
        regression_safety = 1.0 if (
            not result.patch or not result.patch.tests_modified
        ) and any(
            item.role == TestRole.REGRESSION
            and item.outcome == TestOutcome.PASS
            and item.recorded
            for item in result.test_executions
        ) else 0.0

    dimensions: dict[str, bool | int | float | str | None] = {
        "citation_validity": citations["validity"],
        "citation_coverage": citations["coverage"],
        "fabricated_citations": citations["fabricated_rate"],
        "service_top1": service_top1,
        "service_top3": service_top3,
        "fault_accuracy": fault_accuracy,
        "file_exactness": file_exactness,
        "function_exactness": function_exactness,
        "line_exactness": line_exactness,
        "mechanism": mechanism,
        "causal_status": causal_status,
        "l1_causal_status": l1_causal_status,
        "l2_causal_status": l2_causal_status,
        "l2_abstention": l2_abstention,
        "false_abstention": false_abstention,
        "app_source_claim": 1.0 if app_claim else 0.0,
        "harness_claim": 1.0 if harness_claim else 0.0,
        "app_causal_status": app_causal_status,
        "app_abstention": app_abstention,
        "harness_identification": harness_identification,
        "unsupported_claim_rate": unsupported_rate,
        "execution_overclaims": execution_overclaims,
        "patch_applies": patch_applies,
        "patch_scope": patch_scope,
        "fail_to_pass": fail_to_pass,
        "pass_to_pass": pass_to_pass,
        "reproduction_before": reproduction_before,
        "reproduction_after": reproduction_after,
        "regression_safety": regression_safety,
    }

    failures: list[str] = []
    for name in manifest.required_dimensions:
        if name not in dimensions:
            failures.append(f"{name}: missing dimension")
        elif not _strict_ok(name, dimensions[name]):
            failures.append(f"{name}: value {dimensions[name]!r} does not satisfy the strict rule")
    for item in validation.errors:
        failures.append(f"validation:{item.code}")

    strict_pass = not failures
    explanations = _explanations(dimensions, truth)
    for item in validation.issues:
        explanations[f"validation:{item.code}"] = item.detail

    payload = {
        "scenario": scenario,
        "case_id": manifest.case_id.value,
        "synthetic": manifest.synthetic,
        "mode": mode.value,
        "result_class": result_class,
        "dimensions": dimensions,
        "dimension_explanations": explanations,
        "required_dimensions": manifest.required_dimensions,
        "strict_pass": strict_pass,
        "failures": failures,
        "citations": citations,
        "validation_issues": [item.model_dump(mode="json") for item in validation.issues],
    }
    result_hash = digest(payload)
    return CaseScore(**payload, result_hash=result_hash)
