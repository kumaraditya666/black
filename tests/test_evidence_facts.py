import pytest
from blackbox.evidence_facts import extract_facts, check_atomic_claim
from blackbox.investigator import normalize_abstention, validate, validate_model_output
from blackbox.investigation_schema import Findings


@pytest.fixture
def snapshot():
    return {'incident_id': 1, 'missing_evidence': ['source absent elsewhere'], 'evidence': [
        {'id':'event:e1', 'type':'event', 'event_id':'e1', 'exception_type':'ZeroDivisionError', 'message':'division by zero', 'commit':'a'*40},
        {'id':'frame:0', 'type':'stack_frame', 'path':'app.py', 'line':26, 'function':'<module>', 'status':'resolved', 'source_line':'main()', 'commit':'a'*40},
        {'id':'frame:1', 'type':'stack_frame', 'path':'app.py', 'line':17, 'function':'main', 'status':'resolved', 'source_line':'return calculate_average([])', 'commit':'a'*40},
        {'id':'frame:2', 'type':'stack_frame', 'path':'app.py', 'line':13, 'function':'calculate_average', 'status':'resolved', 'source_line':'return sum(values) / len(values)', 'commit':'a'*40}]}


def abstention(**overrides):
    data = {'outcome': 'INSUFFICIENT_EVIDENCE',
            'observed_failure': {'text': 'ZeroDivisionError: division by zero', 'evidence_ids': ['event:e1']},
            'observed_facts': [], 'hypotheses': [], 'alternatives': [],
            'missing_evidence': ['source absent elsewhere'], 'verification_steps': ['Collect runtime values.']}
    data.update(overrides)
    return Findings.model_validate(data)


def test_wrong_frame_name_is_contradicted(snapshot):
    facts = extract_facts(snapshot)
    assert check_atomic_claim('frame_function', 'main', ['frame:0'], facts)['verification_status'] == 'CONTRADICTED'
    assert check_atomic_claim('frame_function', 'main', ['frame:1'], facts)['verification_status'] == 'RECORDED'
    assert check_atomic_claim('frame_function', 'main', ['nonexistent'], facts)['verification_status'] == 'UNVERIFIABLE'


def test_matching_record_status_is_reported(snapshot):
    facts = [{'category': 'source_statement', 'value': 'a', 'evidence_ids': ['frame:0'], 'verification_status': 'RECORDED'},
             {'category': 'source_statement', 'value': 'b', 'evidence_ids': ['frame:0'], 'verification_status': 'VERIFIED_SOURCE'}]
    assert check_atomic_claim('source_statement', 'b', ['frame:0'], facts)['verification_status'] == 'VERIFIED_SOURCE'
    assert check_atomic_claim('source_statement', 'c', ['frame:0'], facts)['verification_status'] == 'CONTRADICTED'


def test_division_operand_mechanically_checked(snapshot):
    facts = extract_facts(snapshot)
    assert check_atomic_claim('division_denominator', 'len(values)', ['frame:2'], facts)['verification_status'] == 'VERIFIED_SOURCE'
    assert check_atomic_claim('division_denominator', 'sum(values)', ['frame:2'], facts)['verification_status'] == 'CONTRADICTED'
    assert check_atomic_claim('division_denominator', 'len(values)', ['frame:1'], facts)['verification_status'] == 'UNVERIFIABLE'


def test_stack_order_and_provenance_are_deterministic(snapshot):
    facts = extract_facts(snapshot)
    order = [f for f in facts if f['category'] == 'stack_order']
    assert len(order) == 1
    assert order[0]['value'] == '<module>@app.py:26 > main@app.py:17 > calculate_average@app.py:13'
    assert order[0]['evidence_ids'] == ['frame:0', 'frame:1', 'frame:2']
    positions = [f['value'] for f in facts if f['category'] == 'frame_order']
    assert positions == ['position 1 of 3', 'position 2 of 3', 'position 3 of 3']
    locations = {f['evidence_ids'][0]: f['value'] for f in facts if f['category'] == 'frame_location'}
    assert locations == {'frame:0': 'app.py:26', 'frame:1': 'app.py:17', 'frame:2': 'app.py:13'}
    for fact in facts:
        assert fact['provenance'], 'every deterministic fact must carry provenance'
        assert fact['provenance'][0]['evidence_id'] in fact['evidence_ids']
        assert fact['provenance'][0]['commit'] == 'a' * 40


def test_wrong_frame_description_is_rejected(snapshot):
    # The exact Milestone 2.7 error: line 26 belongs to the module frame, not to main.
    findings = abstention(verification_steps=['The module frame at line 26 is within main.'])
    with pytest.raises(ValueError, match='different function'):
        validate(findings, snapshot)


def test_wrong_frame_id_function_is_rejected(snapshot):
    findings = abstention(verification_steps=['frame:1 records calculate_average, which divides by zero.'])
    with pytest.raises(ValueError, match='cited frame'):
        validate(findings, snapshot)


def test_correct_frame_description_is_accepted(snapshot):
    findings = abstention(verification_steps=['The module frame is at line 26 and main is at line 17.',
                                              'calculate_average at line 13 divides by len(values).'])
    validate(findings, snapshot)  # does not raise


def test_recorded_unresolved_frame_line_is_citeable():
    snapshot = {'incident_id': 1, 'missing_evidence': ['source absent'], 'evidence': [
        {'id': 'event:e1', 'type': 'event', 'event_id': 'e1', 'exception_type': 'RuntimeError',
         'message': 'operation failed', 'commit': '0' * 40},
        {'id': 'frame:0', 'type': 'stack_frame', 'path': 'missing.py', 'line': 1, 'function': 'unknown',
         'status': 'unresolved', 'reason': 'commit not found or not a commit', 'commit': '0' * 40}]}
    findings = abstention(observed_facts=[{'text': 'The frame is at line 1 of missing.py.',
                                           'evidence_ids': ['frame:0']}],
                          missing_evidence=['source absent'])
    validate(findings, snapshot)  # recorded frame location, not an invented line


def test_invented_source_line_is_still_rejected(snapshot):
    findings = abstention(missing_evidence=['source absent elsewhere'],
                          verification_steps=['Inspect line 99 of app.py.'])
    with pytest.raises(ValueError, match='unknown source line'):
        validate(findings, snapshot)


def test_minimal_abstention_uses_recorded_facts(snapshot):
    result = Findings.model_validate(normalize_abstention({'outcome':'INSUFFICIENT_EVIDENCE'}, snapshot))
    assert result.outcome == 'INSUFFICIENT_EVIDENCE' and not result.hypotheses
    assert result.observed_failure.evidence_ids == ['event:e1']
    assert result.missing_evidence == ['source absent elsewhere']


def test_abstention_with_empty_optional_fields_is_completed(snapshot):
    # A small model returns the right abstention but leaves suggestion lists empty.
    raw = {'outcome': 'INSUFFICIENT_EVIDENCE',
           'observed_failure': {'text': 'ZeroDivisionError: division by zero', 'evidence_ids': ['event:e1']},
           'observed_facts': [], 'hypotheses': [], 'alternatives': [],
           'missing_evidence': [], 'verification_steps': []}
    result = Findings.model_validate(normalize_abstention(raw, snapshot))
    assert result.missing_evidence == ['source absent elsewhere']
    assert result.verification_steps == ['Collect missing evidence and re-investigate.']
    validate(result, snapshot)


def test_empty_verification_steps_still_rejected_for_likely_cause(snapshot):
    raw = {'outcome': 'LIKELY_CAUSE',
           'observed_failure': {'text': 'ZeroDivisionError: division by zero', 'evidence_ids': ['event:e1']},
           'observed_facts': [], 'alternatives': [], 'missing_evidence': ['runtime values absent'],
           'verification_steps': [],
           'hypotheses': [{'explanation': 'Empty input reaches the division.', 'contradicting_evidence': [],
                           'supporting_evidence': ['event:e1', 'frame:2']}]}
    with pytest.raises(ValueError, match='verification steps'):
        Findings.model_validate(normalize_abstention(raw, snapshot))


def test_abstention_maps_verbatim_missing_text_but_not_invented_text():
    snapshot = {'incident_id': 1, 'missing_evidence': ['Source file absent at commit.'], 'evidence': [
        {'id': 'event:e1', 'type': 'event', 'event_id': 'e1', 'exception_type': 'RuntimeError',
         'message': 'operation failed', 'commit': '0' * 40},
        {'id': 'missing_evidence', 'type': 'missing_evidence', 'items': ['Source file absent at commit.']}]}
    raw = {'outcome': 'INSUFFICIENT_EVIDENCE',
           'observed_failure': {'text': 'RuntimeError: operation failed', 'evidence_ids': ['event:e1']},
           'observed_facts': [], 'hypotheses': [],
           'alternatives': [{'explanation': 'Cannot locate the failure.', 'contradicting_evidence': [],
                             'supporting_evidence': ['Source file absent at commit', 'missing_evidence']}],
           'missing_evidence': ['Source file absent at commit.'], 'verification_steps': ['Retry with a resolvable commit.']}
    normalized = normalize_abstention(raw, snapshot)
    assert normalized['alternatives'][0]['supporting_evidence'] == ['missing_evidence']
    assert raw['alternatives'][0]['supporting_evidence'][0] == 'Source file absent at commit', 'input must not be mutated'
    validate(Findings.model_validate(normalized), snapshot)
    invented = {**raw, 'alternatives': [{'explanation': 'Cannot locate the failure.', 'contradicting_evidence': [],
                                         'supporting_evidence': ['Source file vanished entirely']}]}
    with pytest.raises(ValueError, match='unknown evidence IDs'):
        validate(Findings.model_validate(normalize_abstention(invented, snapshot)), snapshot)


def test_untraceable_observation_is_dropped_not_fatal(snapshot):
    raw = {'outcome': 'INSUFFICIENT_EVIDENCE',
           'observed_failure': {'text': 'ZeroDivisionError: division by zero', 'evidence_ids': ['event:e1']},
           'observed_facts': [{'text': 'A fact with no reference', 'evidence_ids': []},
                              {'text': 'A fact with an invented reference', 'evidence_ids': ['event:missing']},
                              {'text': 'A traceable fact', 'evidence_ids': ['frame:1']}],
           'hypotheses': [], 'alternatives': [], 'missing_evidence': ['source absent elsewhere'],
           'verification_steps': ['Collect runtime values.']}
    findings, dropped = validate_model_output(raw, snapshot)
    assert dropped == 2 and [claim.text for claim in findings.observed_facts] == ['A traceable fact']
    assert findings.outcome == 'INSUFFICIENT_EVIDENCE'


def test_evidence_id_placeholders_in_missing_evidence_are_replaced(snapshot):
    raw = {'outcome': 'LIKELY_CAUSE',
           'observed_failure': {'text': 'ZeroDivisionError: division by zero', 'evidence_ids': ['event:e1']},
           'observed_facts': [], 'alternatives': [], 'missing_evidence': ['missing_evidence', 'event:x'],
           'verification_steps': ['Collect runtime values.'],
           'hypotheses': [{'explanation': 'Empty input reaches the division.', 'contradicting_evidence': [],
                           'supporting_evidence': ['event:e1', 'frame:2']}]}
    findings, _ = validate_model_output(raw, snapshot)
    assert findings.missing_evidence == ['source absent elsewhere']


def test_untraceable_hypothesis_reference_is_fatal(snapshot):
    raw = {'outcome': 'LIKELY_CAUSE',
           'observed_failure': {'text': 'ZeroDivisionError: division by zero', 'evidence_ids': ['event:e1']},
           'observed_facts': [], 'alternatives': [], 'missing_evidence': ['runtime values absent'],
           'verification_steps': ['Collect runtime values.'],
           'hypotheses': [{'explanation': 'The empty list causes the division.',
                           'supporting_evidence': ['event:e1', 'frame:missing'], 'contradicting_evidence': []}]}
    with pytest.raises(ValueError, match='unknown evidence IDs'):
        validate_model_output(raw, snapshot)


def test_malformed_diagnosis_not_silently_promoted(snapshot):
    with pytest.raises(ValueError):
        Findings.model_validate(normalize_abstention({'outcome':'LIKELY_CAUSE'}, snapshot))
