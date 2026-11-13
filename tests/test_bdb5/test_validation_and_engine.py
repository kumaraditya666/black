from __future__ import annotations

import pytest
from pydantic import ValidationError

from blackbox.bdb5.engine import evaluate_case, evaluate_suite
from blackbox.bdb5.errors import BlockedCaseError, PacketValidationError
from blackbox.bdb5.models import Claim, EvidencePacket, Readiness, ValidationSeverity
from blackbox.bdb5.synthetic import SYNTHETIC_REV, synthetic_suite
from blackbox.bdb5.validation import validate_packet, validate_result


def scenario(name: str):
    return next(item for item in synthetic_suite() if item.name == name)


def test_candidate_name_matching_hidden_target_is_not_leakage_by_itself():
    item = scenario("t1-correct-l1-and-l2-abstention")
    assert "service-beta" in item.packet.candidate_inventory
    assert validate_packet(item.manifest, item.packet, item.truth).passed


def test_target_mapping_marker_is_rejected():
    item = scenario("t1-correct-l1-and-l2-abstention")
    packet = item.packet.model_copy(update={"task_instructions": "The root_cause_service is service-beta."})
    with pytest.raises(PacketValidationError):
        evaluate_case(item.manifest, packet, item.truth, item.result)


def test_target_marker_on_a_different_line_is_not_leakage():
    item = scenario("t1-correct-l1-and-l2-abstention")
    packet = item.packet.model_copy(update={
        "task_instructions": "The root cause is under investigation.\nservice-beta appears in the ordinary inventory."
    })
    assert validate_packet(item.manifest, packet, item.truth).passed


def test_generic_fault_taxonomy_range_is_not_leakage():
    item = scenario("t1-correct-l1-and-l2-abstention")
    packet = item.packet.model_copy(update={
        "task_instructions": "Identify the faulty service and one fault class from F1-F5."
    })
    assert validate_packet(item.manifest, packet, item.truth).passed


def test_gold_patch_and_private_path_are_rejected():
    item = scenario("r1-correct")
    patch = item.packet.model_copy(update={"task_instructions": "diff --git a/x b/x\n+++ b/x"})
    with pytest.raises(PacketValidationError):
        evaluate_case(item.manifest, patch, item.truth, item.result)

    private = item.packet.model_copy(update={"task_instructions": "Read C:\\label-vault\\target.txt"})
    with pytest.raises(PacketValidationError):
        evaluate_case(item.manifest, private, item.truth, item.result)


def test_hidden_label_key_is_rejected_by_packet_schema():
    item = scenario("r1-correct")
    raw = item.packet.model_dump(mode="json")
    raw["ground_truth"] = {"expected_service": "hidden"}
    with pytest.raises(ValidationError):
        type(item.packet)(**raw)


def test_duplicate_evidence_ids_are_rejected_by_schema():
    item = scenario("r1-correct")
    with pytest.raises(ValidationError):
        EvidencePacket.model_validate({
            **item.packet.model_dump(),
            "evidence": item.packet.evidence + (item.packet.evidence[0],),
        })


def test_wrong_artifact_hash_and_source_revision_are_rejected():
    item = scenario("r1-correct")
    bad_hash = item.packet.model_copy(update={
        "artifact_hashes": {**item.packet.artifact_hashes, "artifact:ci-1": "0" * 64}
    })
    with pytest.raises(PacketValidationError):
        evaluate_case(item.manifest, bad_hash, item.truth, item.result)

    bad_revision = item.packet.model_copy(update={"source_revision": "2" * 40})
    with pytest.raises(PacketValidationError):
        evaluate_case(item.manifest, bad_revision, item.truth, item.result)


def test_unknown_citation_is_visible_but_does_not_crash_evaluation():
    item = scenario("r1-correct")
    result = item.result.model_copy(update={
        "claims": item.result.claims + (
            Claim(category="SOURCE_CAUSE", text="Invented citation.", evidence_ids=("fake:source",)),
        )
    })
    report = validate_result(item.manifest, item.packet, result)
    assert any(issue.code == "unknown_citation" and issue.severity == ValidationSeverity.WARNING
               for issue in report.issues)
    scored = evaluate_case(item.manifest, item.packet, item.truth, result)
    assert scored.dimensions["unsupported_claim_rate"] > 0
    assert not scored.strict_pass


def test_blocked_and_non_synthetic_cases_refuse_evaluation():
    item = scenario("t1-correct-l1-and-l2-abstention")
    blocked = item.manifest.model_copy(update={"readiness": Readiness.PREPARATION_BLOCKED})
    with pytest.raises(BlockedCaseError):
        evaluate_case(blocked, item.packet, item.truth, item.result)

    real = item.manifest.model_copy(update={"synthetic": False})
    with pytest.raises(BlockedCaseError):
        evaluate_case(real, item.packet, item.truth, item.result)


def test_synthetic_suite_is_deterministic_and_not_a_benchmark_result():
    first = evaluate_suite(synthetic_suite())
    second = evaluate_suite(synthetic_suite())
    assert first.suite_hash == second.suite_hash
    assert first.model_dump() == second.model_dump()
    assert first.result_class == "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT"
    assert first.case_count == 29
    assert first.strict_pass_count == 5
