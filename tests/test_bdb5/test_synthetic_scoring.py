from __future__ import annotations

from blackbox.bdb5.engine import evaluate_suite
from blackbox.bdb5.synthetic import synthetic_suite


def scenario(name: str):
    return next(item for item in synthetic_suite() if item.name == name)


def score(name: str):
    return evaluate_suite([scenario(name)]).cases[0]


def test_every_synthetic_scenario_matches_its_expected_classification():
    scenarios = synthetic_suite()
    suite = evaluate_suite(scenarios)
    assert {item.manifest.case_id.value for item in scenarios} == {
        "BDB5-T1", "BDB5-R1", "BDB5-R2", "BDB5-R3", "BDB5-P1"
    }
    assert suite.result_class == "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT"
    for item, result in zip(scenarios, suite.cases):
        assert result.strict_pass is item.expected_strict_pass, item.name
        assert "accuracy" not in result.dimensions


def test_t1_service_identification_and_l2_abstention_are_separate():
    correct = score("t1-correct-l1-and-l2-abstention")
    assert correct.strict_pass
    assert correct.dimensions["service_top1"] == 1.0
    assert correct.dimensions["l1_causal_status"] == 1.0
    assert correct.dimensions["l2_causal_status"] == 1.0
    assert correct.dimensions["l2_abstention"] == 1.0
    assert correct.dimensions["false_abstention"] == 0.0

    wrong_fault = score("t1-wrong-fault")
    assert wrong_fault.dimensions["service_top1"] == 1.0
    assert wrong_fault.dimensions["l1_causal_status"] == 0.0
    assert wrong_fault.dimensions["l2_abstention"] == 1.0


def test_t1_source_overclaim_fails_the_abstention_dimension():
    result = score("t1-source-overclaim")
    assert result.dimensions["l2_causal_status"] == 0.0
    assert result.dimensions["l2_abstention"] == 0.0
    assert not result.strict_pass


def test_t1_fabricated_citation_and_unsupported_rate():
    result = score("t1-fabricated-citation")
    assert result.dimensions["fabricated_citations"] is not None
    assert result.dimensions["fabricated_citations"] > 0
    assert result.dimensions["citation_validity"] < 1.0
    assert result.dimensions["unsupported_claim_rate"] > 0
    assert not result.strict_pass


def test_t1_zero_citations_makes_fabricated_rate_not_applicable():
    result = score("t1-no-citations")
    assert result.dimensions["citation_validity"] == 0.0
    assert result.dimensions["fabricated_citations"] is None
    assert result.dimensions["citation_coverage"] == 0.0
    assert result.dimensions["unsupported_claim_rate"] == 1.0
    assert not result.strict_pass


def test_t1_zero_material_claims_makes_unsupported_rate_not_applicable():
    result = score("t1-zero-material-claims")
    assert result.dimensions["unsupported_claim_rate"] is None
    assert not result.strict_pass


def test_r1_patch_free_source_scoring_dimensions():
    correct = score("r1-correct")
    assert correct.strict_pass
    assert correct.dimensions["file_exactness"] == 1.0
    assert correct.dimensions["function_exactness"] == 1.0
    assert correct.dimensions["line_exactness"] == 1.0
    assert correct.dimensions["mechanism"] == 1.0
    assert correct.dimensions["causal_status"] == 1.0
    assert correct.dimensions["reproduction_before"] == 1.0

    wrong_file = score("r1-wrong-file")
    assert wrong_file.dimensions["file_exactness"] == 0.0
    assert not wrong_file.strict_pass

    wrong_causal = score("r1-wrong-causal-status")
    assert wrong_causal.dimensions["causal_status"] == 0.0


def test_r1_wrong_revision_is_a_traceable_validation_failure():
    result = score("r1-wrong-revision")
    codes = {item.code for item in result.validation_issues}
    assert "wrong_source_revision" in codes
    assert not result.strict_pass


def test_r1_unexecuted_pass_is_an_execution_overclaim():
    result = score("r1-unexecuted-pass")
    assert result.dimensions["execution_overclaims"] >= 1
    assert result.dimensions["reproduction_before"] == 0.0
    assert not result.strict_pass


def test_r1_missing_reproduction_and_citation():
    no_repro = score("r1-no-reproduction")
    assert no_repro.dimensions["reproduction_before"] == 0.0
    assert not no_repro.strict_pass

    missing = score("r1-missing-citation")
    assert missing.dimensions["unsupported_claim_rate"] > 0
    assert not missing.strict_pass


def test_r2_missing_fixture_does_not_blame_application_source():
    result = score("r2-correct-harness-and-abstention")
    assert result.strict_pass
    assert result.dimensions["app_source_claim"] == 0.0
    assert result.dimensions["app_causal_status"] == 1.0
    assert result.dimensions["app_abstention"] == 1.0
    assert result.dimensions["harness_claim"] == 1.0
    assert result.dimensions["harness_identification"] == 1.0


def test_r2_false_source_blame_fails_negative_control():
    result = score("r2-false-source-blame")
    assert result.dimensions["app_source_claim"] == 1.0
    assert result.dimensions["app_causal_status"] == 0.0
    assert result.dimensions["app_abstention"] == 0.0
    assert not result.strict_pass


def test_r2_missing_abstention_and_reproduction_fail():
    missing_abstention = score("r2-missing-abstention")
    assert missing_abstention.dimensions["app_abstention"] == 0.0
    no_repro = score("r2-no-reproduction")
    assert no_repro.dimensions["reproduction_before"] == 0.0
    assert not no_repro.strict_pass


def test_r3_source_scoring_and_wrong_mechanism():
    correct = score("r3-correct")
    assert correct.strict_pass
    assert correct.dimensions["file_exactness"] == 1.0
    assert correct.dimensions["function_exactness"] == 1.0
    assert correct.dimensions["mechanism"] == 1.0

    wrong_mechanism = score("r3-wrong-mechanism")
    assert wrong_mechanism.dimensions["mechanism"] == 0.0
    assert not wrong_mechanism.strict_pass


def test_p1_patch_test_and_regression_dimensions():
    correct = score("p1-correct")
    assert correct.strict_pass
    assert correct.dimensions["patch_applies"] == 1.0
    assert correct.dimensions["patch_scope"] == 1.0
    assert correct.dimensions["fail_to_pass"] == 1.0
    assert correct.dimensions["pass_to_pass"] == 1.0
    assert correct.dimensions["reproduction_before"] == 1.0
    assert correct.dimensions["reproduction_after"] == 1.0
    assert correct.dimensions["regression_safety"] == 1.0


def test_p1_invalid_scope_and_test_modification_are_rejected():
    invalid_scope = score("p1-invalid-scope")
    assert invalid_scope.dimensions["patch_scope"] == 0.0
    assert not invalid_scope.strict_pass

    modified = score("p1-test-file-modification")
    assert modified.dimensions["patch_scope"] == 0.0
    assert modified.dimensions["regression_safety"] == 0.0
    assert not modified.strict_pass


def test_p1_incomplete_f2p_unexecuted_pass_and_regression_failure():
    incomplete = score("p1-incomplete-fail-to-pass")
    assert incomplete.dimensions["fail_to_pass"] == 0.5
    assert not incomplete.strict_pass

    unexecuted = score("p1-unexecuted-pass")
    assert unexecuted.dimensions["execution_overclaims"] >= 1
    assert unexecuted.dimensions["fail_to_pass"] == 0.5
    assert not unexecuted.strict_pass

    regression = score("p1-regression-failure")
    assert regression.dimensions["regression_safety"] == 0.0
    assert not regression.strict_pass
