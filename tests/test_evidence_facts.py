import json
import pytest
from blackbox.evidence_facts import extract_facts, check_atomic_claim
from blackbox.investigator import normalize_abstention
from blackbox.investigation_schema import Findings


@pytest.fixture
def snapshot():
    return {'incident_id': 1, 'missing_evidence': ['source absent elsewhere'], 'evidence': [
        {'id':'event:e1', 'type':'event', 'event_id':'e1', 'exception_type':'ZeroDivisionError', 'message':'division by zero', 'commit':'a'*40},
        {'id':'frame:0', 'type':'stack_frame', 'path':'app.py', 'line':26, 'function':'<module>', 'status':'resolved', 'source_line':'main()', 'commit':'a'*40},
        {'id':'frame:1', 'type':'stack_frame', 'path':'app.py', 'line':17, 'function':'main', 'status':'resolved', 'source_line':'return calculate_average([])', 'commit':'a'*40},
        {'id':'frame:2', 'type':'stack_frame', 'path':'app.py', 'line':13, 'function':'calculate_average', 'status':'resolved', 'source_line':'return sum(values) / len(values)', 'commit':'a'*40}]}


def test_wrong_frame_name_is_contradicted(snapshot):
    facts = extract_facts(snapshot)
    assert check_atomic_claim('frame_function', 'main', ['frame:0'], facts)['verification_status'] == 'CONTRADICTED'
    assert check_atomic_claim('frame_function', 'main', ['frame:1'], facts)['verification_status'] == 'RECORDED'
    assert check_atomic_claim('frame_function', 'main', ['nonexistent'], facts)['verification_status'] == 'UNVERIFIABLE'


def test_division_operand_mechanically_checked(snapshot):
    facts = extract_facts(snapshot)
    assert check_atomic_claim('division_denominator', 'len(values)', ['frame:2'], facts)['verification_status'] == 'VERIFIED_SOURCE'
    assert check_atomic_claim('division_denominator', 'sum(values)', ['frame:2'], facts)['verification_status'] == 'CONTRADICTED'
    assert check_atomic_claim('division_denominator', 'len(values)', ['frame:1'], facts)['verification_status'] == 'UNVERIFIABLE'


def test_minimal_abstention_uses_recorded_facts(snapshot):
    result = Findings.model_validate(normalize_abstention({'outcome':'INSUFFICIENT_EVIDENCE'}, snapshot))
    assert result.outcome == 'INSUFFICIENT_EVIDENCE' and not result.hypotheses
    assert result.observed_failure.evidence_ids == ['event:e1']
    assert result.missing_evidence == ['source absent elsewhere']


def test_malformed_diagnosis_not_silently_promoted(snapshot):
    with pytest.raises(ValueError):
        Findings.model_validate(normalize_abstention({'outcome':'LIKELY_CAUSE'}, snapshot))
