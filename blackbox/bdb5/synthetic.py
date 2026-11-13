"""Invented synthetic cases for the five BDB-5 scoring paths.

No real hidden label, gold patch, fix commit, or target mapping is used here.
The T1 fixture uses invented service names and an invented fault target. The
real cases remain blocked; these manifests are test doubles only.
"""
from __future__ import annotations

import hashlib
from typing import Iterable

from .engine import evaluate_suite
from .models import (
    Abstention,
    AbstentionScope,
    CaseCategory,
    CaseId,
    CaseManifest,
    CausalStatus,
    Claim,
    ClaimCategory,
    EvidenceItem,
    EvidencePacket,
    EvidenceType,
    GroundTruth,
    InvestigationResult,
    PatchExpectation,
    PatchRecord,
    Readiness,
    SyntheticScenario,
    TestExecution,
    TestOutcome,
    TestRole,
)

SYNTHETIC_REV = "1" * 40
Synthetic_REV_ALT = "2" * 40
T1_SOURCE_REV = None


def _h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _artifacts(case_id: CaseId, evidence: tuple[EvidenceItem, ...]) -> dict[str, str]:
    return {
        "artifact:" + item.evidence_id.replace(":", "-"): _h(
            f"{case_id.value}|{item.evidence_id}|{item.evidence_type.value}|{item.text}"
        )
        for item in evidence
    }


def _manifest(case_id: CaseId, category: CaseCategory,
              required_types: tuple[EvidenceType, ...],
              required_dimensions: tuple[str, ...],
              all_hashes: dict[str, str],
              allowed_files: tuple[str, ...] = (),
              source_revision: str | None = SYNTHETIC_REV) -> CaseManifest:
    return CaseManifest(
        case_id=case_id,
        dataset="synthetic/bdb5",
        dataset_revision="synthetic-v1",
        repository="synthetic/repository" if category != CaseCategory.TELEMETRY else None,
        source_revision=source_revision,
        case_category=category,
        required_evidence_types=required_types,
        allowed_files=allowed_files,
        allowed_scope=("source",) if category == CaseCategory.REPAIR else (),
        required_dimensions=required_dimensions,
        readiness=Readiness.APPROVED_FOR_EVALUATION,
        adapter_requirements=("synthetic-only",),
        artifact_hashes=all_hashes,
        synthetic=True,
    )


def _packet(case_id: CaseId, instructions: str, evidence: tuple[EvidenceItem, ...],
            candidates: tuple[str, ...] = (),
            source_revision: str | None = SYNTHETIC_REV) -> EvidencePacket:
    return EvidencePacket(
        case_id=case_id,
        task_instructions=instructions,
        evidence=evidence,
        candidate_inventory=candidates,
        source_revision=source_revision,
        artifact_hashes=_artifacts(case_id, evidence),
    )


def _truth(case_id: CaseId, **kwargs) -> GroundTruth:
    return GroundTruth(case_id=case_id, **kwargs)


def _result(case_id: CaseId, **kwargs) -> InvestigationResult:
    return InvestigationResult(case_id=case_id, **kwargs)


def _scenario(name: str, manifest: CaseManifest, packet: EvidencePacket,
              truth: GroundTruth, result: InvestigationResult,
              expected_strict_pass: bool,
              expected_issues: tuple[str, ...] = ()) -> SyntheticScenario:
    return SyntheticScenario(
        name=name, manifest=manifest, packet=packet, truth=truth, result=result,
        expected_strict_pass=expected_strict_pass, expected_issues=expected_issues,
    )


def _t1_common():
    evidence = (
        EvidenceItem(
            evidence_id="metric:1", evidence_type=EvidenceType.TELEMETRY_METRIC,
            text="Aggregate service telemetry shows a sustained change after injection.",
        ),
        EvidenceItem(
            evidence_id="log:1", evidence_type=EvidenceType.TELEMETRY_LOG,
            text="The selected log excerpt contains an ordinary warning from the same window.",
        ),
    )
    manifest = _manifest(
        CaseId.T1, CaseCategory.TELEMETRY,
        (EvidenceType.TELEMETRY_METRIC, EvidenceType.TELEMETRY_LOG),
        ("service_top1", "service_top3", "fault_accuracy", "citation_validity",
         "citation_coverage", "l1_causal_status", "l2_causal_status",
         "l2_abstention", "unsupported_claim_rate"),
        source_revision=T1_SOURCE_REV,
        all_hashes=_artifacts(CaseId.T1, evidence),
    )
    packet = _packet(
        CaseId.T1,
        "Return one service and exactly one fault class from the F1-F5 taxonomy.",
        evidence,
        candidates=("service-alpha", "service-beta", "service-gamma"),
        source_revision=T1_SOURCE_REV,
    )
    truth = _truth(
        CaseId.T1,
        expected_service="service-beta",
        expected_fault_class="F2",
        causal_level="L1",
        expected_l1_status=CausalStatus.SUPPORTED,
        expected_l2_status=CausalStatus.NOT_ESTABLISHED,
        expected_abstention=True,
        expected_abstention_scope=AbstentionScope.SOURCE,
    )
    return manifest, packet, truth


def _t1_result(*, fault: str = "F2", source_overclaim: bool = False,
               invalid_citation: bool = False, no_citation: bool = False,
               no_material: bool = False, abstain: bool = True) -> InvestigationResult:
    claims: list[Claim] = []
    if not no_material:
        if no_citation:
            claims = [Claim(category=ClaimCategory.OBSERVATION, text="A change was observed.")]
        else:
            claims = [
                Claim(category=ClaimCategory.OBSERVATION, text="Telemetry changed after injection.",
                      evidence_ids=("metric:1",)),
                Claim(category=ClaimCategory.OBSERVATION, text="A warning appears in the window.",
                      evidence_ids=("log:1",)),
            ]
            if invalid_citation:
                claims.append(Claim(category=ClaimCategory.OBSERVATION, text="A fabricated citation.",
                                    evidence_ids=("fake:evidence",)))
            if source_overclaim:
                claims.append(Claim(category=ClaimCategory.SOURCE_CAUSE,
                                    text="service-alpha source code caused the failure",
                                    evidence_ids=("log:1",)))
    return _result(
        CaseId.T1,
        claims=tuple(claims),
        service_ranked=("service-beta", "service-alpha", "service-gamma"),
        fault_class=fault,
        l1_causal_status=CausalStatus.SUPPORTED,
        l2_causal_status=CausalStatus.SUPPORTED if source_overclaim else CausalStatus.NOT_ESTABLISHED,
        abstention=Abstention(
            scope=AbstentionScope.SOURCE,
            reason="No source mapping is available in the telemetry package.",
            missing_evidence=("runtime source map",),
            source_not_established=True,
        ) if abstain else None,
    )


def t1_scenarios() -> tuple[SyntheticScenario, ...]:
    manifest, packet, truth = _t1_common()
    return (
        _scenario("t1-correct-l1-and-l2-abstention", manifest, packet, truth, _t1_result(), True),
        _scenario("t1-wrong-fault", manifest, packet, truth, _t1_result(fault="F3"), False),
        _scenario("t1-source-overclaim", manifest, packet, truth, _t1_result(source_overclaim=True), False),
        _scenario("t1-fabricated-citation", manifest, packet, truth, _t1_result(invalid_citation=True), False),
        _scenario("t1-no-citations", manifest, packet, truth, _t1_result(no_citation=True), False),
        _scenario("t1-zero-material-claims", manifest, packet, truth, _t1_result(no_material=True), False),
    )


def _r1_common():
    source_rev = SYNTHETIC_REV
    evidence = (
        EvidenceItem(evidence_id="ci:1", evidence_type=EvidenceType.CI_LOG,
                     text="CI log reports an ASCII decode failure while parsing a query header."),
        EvidenceItem(evidence_id="source:1", evidence_type=EvidenceType.SOURCE_EXCERPT,
                     source_revision=source_rev,
                     text="def parse_header(value):\n    return value.decode('ascii')"),
    )
    manifest = _manifest(
        CaseId.R1, CaseCategory.CI_SOURCE,
        (EvidenceType.CI_LOG, EvidenceType.SOURCE_EXCERPT),
        ("file_exactness", "function_exactness", "line_exactness", "mechanism",
         "causal_status", "citation_validity", "reproduction_before", "unsupported_claim_rate"),
        allowed_files=("pkg/http/parser.py",),
        source_revision=source_rev,
        all_hashes=_artifacts(CaseId.R1, evidence),
    )
    packet = _packet(CaseId.R1, "Identify the source mechanism and cite the supplied evidence.", evidence)
    truth = _truth(
        CaseId.R1, expected_files=("pkg/http/parser.py",), expected_function="parse_header",
        expected_line=42,
        expected_mechanism="ASCII decoding rejects non-Latin-1 query bytes.",
        mechanism_term_groups=(("ascii", "decode"), ("non-latin1", "query")),
        causal_level="L3", expected_l2_status=CausalStatus.SUPPORTED,
        require_reproduction_before=True,
    )
    return manifest, packet, truth, source_rev


def _r1_result(*, wrong_file: bool = False, wrong_revision: bool = False,
               fabricated: bool = False, missing_citation: bool = False,
               wrong_causal: bool = False, no_reproduction: bool = False,
               unexecuted_pass: bool = False) -> InvestigationResult:
    claims = [
        Claim(category=ClaimCategory.SOURCE_CAUSE,
              text="The parser passes query bytes to an ASCII decode.",
              evidence_ids=("ci:1", "source:1")),
        Claim(category=ClaimCategory.MECHANISM,
              text="ASCII decoding of non-latin1 query bytes raises the observed error.",
              evidence_ids=("source:1",)),
    ]
    if fabricated:
        claims.append(Claim(category=ClaimCategory.SOURCE_CAUSE, text="Invented evidence.",
                            evidence_ids=("fake:source",)))
    if missing_citation:
        claims.append(Claim(category=ClaimCategory.SOURCE_CAUSE, text="Uncited claim."))
    executions = []
    if not no_reproduction:
        executions.append(TestExecution(
            role=TestRole.REPRODUCTION_BEFORE, name="reproduce_parser",
            outcome=TestOutcome.PASS if unexecuted_pass else TestOutcome.FAIL,
            artifact_sha256=None if unexecuted_pass else _h("synthetic reproduction artifact"),
            failure_signature_matched=None if unexecuted_pass else True,
        ))
    return _result(
        CaseId.R1,
        claims=tuple(claims),
        predicted_files=("pkg/http/other.py",) if wrong_file else ("pkg/http/parser.py",),
        predicted_function="parse_header",
        predicted_line=42,
        predicted_mechanism="The query value is decoded as ASCII instead of the declared encoding.",
        mechanism_evidence_ids=("source:1",),
        l2_causal_status=CausalStatus.NOT_ESTABLISHED if wrong_causal else CausalStatus.SUPPORTED,
        claimed_source_revision=Synthetic_REV_ALT if wrong_revision else SYNTHETIC_REV,
        test_executions=tuple(executions),
    )


def r1_scenarios() -> tuple[SyntheticScenario, ...]:
    manifest, packet, truth, _ = _r1_common()
    return (
        _scenario("r1-correct", manifest, packet, truth, _r1_result(), True),
        _scenario("r1-wrong-file", manifest, packet, truth, _r1_result(wrong_file=True), False),
        _scenario("r1-wrong-revision", manifest, packet, truth, _r1_result(wrong_revision=True), False,
                  ("wrong_source_revision",)),
        _scenario("r1-fabricated-citation", manifest, packet, truth, _r1_result(fabricated=True), False),
        _scenario("r1-missing-citation", manifest, packet, truth, _r1_result(missing_citation=True), False),
        _scenario("r1-wrong-causal-status", manifest, packet, truth, _r1_result(wrong_causal=True), False),
        _scenario("r1-no-reproduction", manifest, packet, truth, _r1_result(no_reproduction=True), False),
        _scenario("r1-unexecuted-pass", manifest, packet, truth, _r1_result(unexecuted_pass=True), False),
    )


def _r2_common():
    evidence = (
        EvidenceItem(evidence_id="ci:1", evidence_type=EvidenceType.CI_LOG,
                     text="Test log reports a missing fixture file; no application traceback is present."),
        EvidenceItem(evidence_id="harness:1", evidence_type=EvidenceType.TEST_RESULT,
                     text="The fixture directory does not contain fixture_cache.json."),
    )
    manifest = _manifest(
        CaseId.R2, CaseCategory.NEGATIVE_CONTROL,
        (EvidenceType.CI_LOG, EvidenceType.TEST_RESULT),
        ("app_causal_status", "app_abstention", "app_source_claim", "citation_validity",
         "reproduction_before", "unsupported_claim_rate"),
        source_revision=SYNTHETIC_REV,
        all_hashes=_artifacts(CaseId.R2, evidence),
    )
    packet = _packet(CaseId.R2, "State whether an application-source cause is established.", evidence)
    truth = _truth(
        CaseId.R2, expected_harness_terms=("fixture_cache.json", "tests/test_fixture_cache.py:12"),
        causal_level="L0", expected_l2_status=CausalStatus.NOT_ESTABLISHED,
        expected_abstention=True, expected_abstention_scope=AbstentionScope.APPLICATION_SOURCE,
        require_reproduction_before=True,
    )
    return manifest, packet, truth


def _r2_result(*, false_source: bool = False, no_abstention: bool = False,
               no_reproduction: bool = False) -> InvestigationResult:
    claims = [
        Claim(category=ClaimCategory.HARNESS_CAUSE,
              text="Missing fixture_cache.json at tests/test_fixture_cache.py:12 explains the test failure.",
              evidence_ids=("ci:1", "harness:1")),
    ]
    if false_source:
        claims.append(Claim(category=ClaimCategory.APPLICATION_SOURCE_CAUSE,
                            text="The application cache module is defective.",
                            evidence_ids=("ci:1",)))
    executions = ()
    if not no_reproduction:
        executions = (TestExecution(
            role=TestRole.REPRODUCTION_BEFORE, name="reproduce_fixture_error",
            outcome=TestOutcome.FAIL, artifact_sha256=_h("synthetic fixture reproduction"),
            failure_signature_matched=True,
        ),)
    return _result(
        CaseId.R2,
        claims=tuple(claims),
        l2_causal_status=CausalStatus.SUPPORTED if false_source else CausalStatus.NOT_ESTABLISHED,
        abstention=None if no_abstention else Abstention(
            scope=AbstentionScope.APPLICATION_SOURCE,
            reason="No application-source claim is supported by the test-harness evidence.",
            missing_evidence=("application stack trace", "fixture contents"),
            application_source_not_established=True,
        ),
        test_executions=executions,
    )


def r2_scenarios() -> tuple[SyntheticScenario, ...]:
    manifest, packet, truth = _r2_common()
    return (
        _scenario("r2-correct-harness-and-abstention", manifest, packet, truth, _r2_result(), True),
        _scenario("r2-false-source-blame", manifest, packet, truth, _r2_result(false_source=True), False),
        _scenario("r2-missing-abstention", manifest, packet, truth, _r2_result(no_abstention=True), False),
        _scenario("r2-no-reproduction", manifest, packet, truth, _r2_result(no_reproduction=True), False),
    )


def _r3_common():
    evidence = (
        EvidenceItem(evidence_id="issue:1", evidence_type=EvidenceType.ISSUE_TEXT,
                     text="A memoryview response is converted to a representation string."),
        EvidenceItem(evidence_id="source:1", evidence_type=EvidenceType.SOURCE_EXCERPT,
                     source_revision=SYNTHETIC_REV,
                     text="def make_bytes(value):\n    return str(value).encode()"),
    )
    manifest = _manifest(
        CaseId.R3, CaseCategory.ISSUE_SOURCE,
        (EvidenceType.ISSUE_TEXT, EvidenceType.SOURCE_EXCERPT),
        ("file_exactness", "function_exactness", "mechanism", "causal_status",
         "citation_validity", "unsupported_claim_rate"),
        allowed_files=("app/http/response.py",),
        source_revision=SYNTHETIC_REV,
        all_hashes=_artifacts(CaseId.R3, evidence),
    )
    packet = _packet(CaseId.R3, "Localize the response conversion mechanism.", evidence)
    truth = _truth(
        CaseId.R3, expected_files=("app/http/response.py",), expected_function="make_bytes",
        expected_mechanism="A memoryview falls through to string conversion.",
        mechanism_term_groups=(("memoryview",), ("string", "conversion")),
        causal_level="L3", expected_l2_status=CausalStatus.SUPPORTED,
    )
    return manifest, packet, truth


def _r3_result(*, wrong_file: bool = False, bad_mechanism: bool = False,
               fabricated: bool = False) -> InvestigationResult:
    claims = [
        Claim(category=ClaimCategory.SOURCE_CAUSE,
              text="The response helper converts the memoryview through string conversion.",
              evidence_ids=("issue:1", "source:1")),
    ]
    if not bad_mechanism:
        claims.append(Claim(
            category=ClaimCategory.MECHANISM,
            text="The memoryview falls through to string conversion.",
            evidence_ids=("source:1",),
        ))
    if fabricated:
        claims.append(Claim(category=ClaimCategory.SOURCE_CAUSE, text="Invented evidence.",
                            evidence_ids=("fake:issue",)))
    return _result(
        CaseId.R3,
        claims=tuple(claims),
        predicted_files=("app/http/other.py",) if wrong_file else ("app/http/response.py",),
        predicted_function="make_bytes",
        predicted_mechanism="Unrelated scheduling pressure." if bad_mechanism else
        "The memoryview falls through to string conversion.",
        mechanism_evidence_ids=("source:1",),
        l2_causal_status=CausalStatus.SUPPORTED,
    )


def r3_scenarios() -> tuple[SyntheticScenario, ...]:
    manifest, packet, truth = _r3_common()
    return (
        _scenario("r3-correct", manifest, packet, truth, _r3_result(), True),
        _scenario("r3-wrong-file", manifest, packet, truth, _r3_result(wrong_file=True), False),
        _scenario("r3-wrong-mechanism", manifest, packet, truth, _r3_result(bad_mechanism=True), False),
        _scenario("r3-fabricated-citation", manifest, packet, truth, _r3_result(fabricated=True), False),
    )


def _p1_common():
    evidence = (
        EvidenceItem(evidence_id="patch:1", evidence_type=EvidenceType.PATCH_DIFF,
                     text="A synthetic patch adds a slot declaration to a model class."),
        EvidenceItem(evidence_id="tests:1", evidence_type=EvidenceType.TEST_RESULT,
                     text="Synthetic test execution record."),
    )
    manifest = _manifest(
        CaseId.P1, CaseCategory.REPAIR,
        (EvidenceType.PATCH_DIFF, EvidenceType.TEST_RESULT),
        ("patch_applies", "patch_scope", "fail_to_pass", "pass_to_pass",
         "reproduction_before", "reproduction_after", "regression_safety"),
        allowed_files=("pkg/core/model.py",),
        source_revision=SYNTHETIC_REV,
        all_hashes=_artifacts(CaseId.P1, evidence),
    )
    packet = _packet(CaseId.P1, "Report patch application and recorded test outcomes.", evidence)
    truth = _truth(
        CaseId.P1, causal_level="NA", expected_l2_status=CausalStatus.NOT_ASSESSED,
        expected_patch=PatchExpectation(
            allowed_files=("pkg/core/model.py",),
            fail_to_pass=("test_no_dict", "test_slots"),
            pass_to_pass=("test_other",),
            require_reproduction_before=True, require_reproduction_after=True, require_regression=True,
        ),
        require_reproduction_before=True, require_reproduction_after=True, require_regression=True,
    )
    return manifest, packet, truth


def _p1_result(*, invalid_scope: bool = False, tests_modified: bool = False,
               missing_f2p: bool = False, unexecuted_pass: bool = False,
               regression_fail: bool = False, not_applied: bool = False) -> InvestigationResult:
    changed = ("tests/test_model.py",) if tests_modified else (
        ("pkg/core/other.py",) if invalid_scope else ("pkg/core/model.py",)
    )
    tests = [
        TestExecution(role=TestRole.FAIL_TO_PASS, name="test_no_dict", outcome=TestOutcome.PASS,
                      artifact_sha256=None if unexecuted_pass else _h("synthetic test_no_dict")),
        TestExecution(role=TestRole.PASS_TO_PASS, name="test_other", outcome=TestOutcome.PASS,
                      artifact_sha256=_h("synthetic test_other")),
        TestExecution(role=TestRole.REPRODUCTION_BEFORE, name="reproduce_issue",
                      outcome=TestOutcome.FAIL, artifact_sha256=_h("synthetic before"),
                      failure_signature_matched=True),
        TestExecution(role=TestRole.REPRODUCTION_AFTER, name="reproduce_issue",
                      outcome=TestOutcome.PASS, artifact_sha256=_h("synthetic after")),
        TestExecution(role=TestRole.REGRESSION, name="regression_suite",
                      outcome=TestOutcome.FAIL if regression_fail else TestOutcome.PASS,
                      artifact_sha256=_h("synthetic regression")),
    ]
    if not missing_f2p:
        tests.append(TestExecution(role=TestRole.FAIL_TO_PASS, name="test_slots",
                                   outcome=TestOutcome.PASS, artifact_sha256=_h("synthetic test_slots")))
    return _result(
        CaseId.P1,
        patch=PatchRecord(
            applied=not not_applied, changed_files=changed, tests_modified=tests_modified,
            diff_sha256=_h("synthetic patch"),
        ),
        test_executions=tuple(tests),
    )


def p1_scenarios() -> tuple[SyntheticScenario, ...]:
    manifest, packet, truth = _p1_common()
    return (
        _scenario("p1-correct", manifest, packet, truth, _p1_result(), True),
        _scenario("p1-invalid-scope", manifest, packet, truth, _p1_result(invalid_scope=True), False),
        _scenario("p1-test-file-modification", manifest, packet, truth, _p1_result(tests_modified=True), False),
        _scenario("p1-incomplete-fail-to-pass", manifest, packet, truth, _p1_result(missing_f2p=True), False),
        _scenario("p1-unexecuted-pass", manifest, packet, truth, _p1_result(unexecuted_pass=True), False),
        _scenario("p1-regression-failure", manifest, packet, truth, _p1_result(regression_fail=True), False),
        _scenario("p1-patch-not-applied", manifest, packet, truth, _p1_result(not_applied=True), False),
    )


def synthetic_suite() -> tuple[SyntheticScenario, ...]:
    """Return every invented scenario in deterministic case/name order."""
    scenarios = t1_scenarios() + r1_scenarios() + r2_scenarios() + r3_scenarios() + p1_scenarios()
    return tuple(sorted(scenarios, key=lambda item: (item.manifest.case_id.value, item.name)))


def synthetic_case(case_id: CaseId) -> tuple[SyntheticScenario, ...]:
    return tuple(item for item in synthetic_suite() if item.manifest.case_id == case_id)


def self_test() -> dict:
    """Run the built-in suite twice and check expected strict outcomes and hashes."""
    scenarios = synthetic_suite()
    first = evaluate_suite(scenarios)
    second = evaluate_suite(scenarios)
    mismatches = []
    for scenario, score in zip(scenarios, first.cases):
        if score.strict_pass != scenario.expected_strict_pass:
            mismatches.append({
                "scenario": scenario.name,
                "expected": scenario.expected_strict_pass,
                "actual": score.strict_pass,
                "failures": list(score.failures),
            })
    return {
        "status": "PASS" if not mismatches and first.suite_hash == second.suite_hash else "FAIL",
        "case_count": first.case_count,
        "strict_pass_count": first.strict_pass_count,
        "suite_hash": first.suite_hash,
        "repeat_hash": second.suite_hash,
        "deterministic": first.suite_hash == second.suite_hash,
        "mismatches": mismatches,
        "result_class": first.result_class,
    }
