from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from blackbox.bdb5.engine import evaluate_case
from blackbox.bdb5.errors import BlockedCaseError
from blackbox.bdb5.models import (
    AbstentionScope,
    CaseId,
    CausalStatus,
    GroundTruth,
    Readiness,
)
from blackbox.bdb5.real_cases import (
    CASES,
    PreparationError,
    R1,
    R2,
    ensure_not_approved,
    parse_ci_log,
    prepare_ci_case,
)
from blackbox.bdb5.validation import validate_packet

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "fixtures" / "bdb5" / "bugswarm"
R1_LOG = LOGS / "109227527.log"
R2_LOG = LOGS / "83523531.log"


def _fake_r1_source(_repo, _commit, frame):
    return {
        "path": frame["path"],
        "line": frame["line"],
        "function": frame["function"],
        "status": "resolved",
        "source_line": "encoding=self.url_charset, errors=self.encoding_errors,",
        "context": [
            {"line": 354, "text": "return self.parameter_storage_class(parse_qsl("},
            {"line": 355, "text": "    wsgi_get_bytes(self.environ.get('QUERY_STRING', '')),"},
            {"line": 356, "text": "    encoding=self.url_charset, errors=self.encoding_errors,"},
            {"line": 357, "text": "))"},
        ],
    }


def _r1_truth() -> GroundTruth:
    return GroundTruth(
        case_id=CaseId.R1,
        expected_files=("verktyg/requests.py",),
        expected_function="args",
        expected_line=356,
        expected_mechanism="query bytes are decoded as ASCII",
        mechanism_term_groups=(("ascii", "decode"),),
        causal_level="L3",
        expected_l2_status=CausalStatus.SUPPORTED,
        require_reproduction_before=True,
    )


def _r2_truth() -> GroundTruth:
    return GroundTruth(
        case_id=CaseId.R2,
        expected_harness_terms=("types_dict.nml", "test_f90nml.py:211"),
        causal_level="L0",
        expected_l2_status=CausalStatus.NOT_ESTABLISHED,
        expected_abstention=True,
        expected_abstention_scope=AbstentionScope.APPLICATION_SOURCE,
        require_reproduction_before=True,
    )


def test_r1_log_parses_primary_application_frame():
    log = parse_ci_log(R1_LOG.read_text(encoding="utf-8"))
    assert log.test_count == 247
    assert log.summary == "FAILED (failures=2, errors=3)"
    assert len(log.failures) == 5
    failure = log.failure("test_modified_url_encoding")
    assert failure.kind == "ERROR"
    assert failure.exception.startswith("UnicodeDecodeError:")
    assert any(
        frame["path"] == "verktyg/requests.py"
        and frame["line"] == 356
        and frame["function"] == "args"
        for frame in failure.frames
    )


def test_r2_log_parses_missing_fixture_without_application_frame():
    log = parse_ci_log(R2_LOG.read_text(encoding="utf-8"))
    assert log.test_count == 38
    assert log.summary == "FAILED (errors=1)"
    failure = log.failure("test_dict_write")
    assert failure.exception.startswith("IOError:")
    assert "types_dict.nml" in failure.exception
    assert all(frame["test_file"] for frame in failure.frames)


def test_r1_preparation_produces_prepared_not_approved_packet():
    prepared = prepare_ci_case(
        R1_LOG.read_text(encoding="utf-8"),
        R1,
        source_reader=_fake_r1_source,
    )
    assert prepared.manifest.case_id == CaseId.R1
    assert prepared.manifest.readiness == Readiness.PREPARED
    assert prepared.packet.case_id == CaseId.R1
    assert prepared.source_frame["path"] == "verktyg/requests.py"
    assert prepared.source_frame["line"] == 356
    assert "UnicodeDecodeError" in prepared.primary_failure.exception
    assert "source:1" in {item.evidence_id for item in prepared.packet.evidence}
    assert prepared.packet_validation["issues"] == []
    assert validate_packet(prepared.manifest, prepared.packet, _r1_truth()).passed
    ensure_not_approved(prepared)


def test_r2_preparation_keeps_harness_and_application_claims_separate():
    prepared = prepare_ci_case(R2_LOG.read_text(encoding="utf-8"), R2)
    assert prepared.manifest.readiness == Readiness.PREPARED
    assert prepared.source_status is None
    assert "test:1" in {item.evidence_id for item in prepared.packet.evidence}
    assert "types_dict.nml" in prepared.packet.evidence[0].text
    assert validate_packet(prepared.manifest, prepared.packet, _r2_truth()).passed
    ensure_not_approved(prepared)


def test_prepared_real_cases_cannot_enter_synthetic_engine():
    prepared = prepare_ci_case(R2_LOG.read_text(encoding="utf-8"), R2)
    assert prepared.packet.case_id == CaseId.R2
    with pytest.raises(BlockedCaseError):
        evaluate_case(
            prepared.manifest,
            prepared.packet,
            _r2_truth(),
            prepared,  # type: ignore[arg-type]
        )


def test_r1_requires_source_and_refuses_unresolved_source():
    with pytest.raises(PreparationError, match="requires an injected source reader"):
        prepare_ci_case(R1_LOG.read_text(encoding="utf-8"), R1)

    def unresolved(_repo, _commit, _frame):
        return {"status": "unresolved", "reason": "commit not found"}

    with pytest.raises(PreparationError, match="did not resolve"):
        prepare_ci_case(
            R1_LOG.read_text(encoding="utf-8"),
            R1,
            source_reader=unresolved,
        )


def test_packet_contains_no_host_paths():
    prepared = prepare_ci_case(
        R1_LOG.read_text(encoding="utf-8"),
        R1,
        source_reader=_fake_r1_source,
    )
    visible = json.dumps(prepared.packet.model_visible_payload())
    assert "/home/travis" not in visible
    assert "/opt/python" not in visible
    assert "C:\\" not in visible
    assert prepared.manifest.synthetic is False


def test_preparation_cli_writes_r2_packet_outside_repo(tmp_path):
    output = tmp_path / "r2.json"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "bdb5_prepare_ci.py"),
        "--case", "BDB5-R2",
        "--log", str(R2_LOG),
        "--output", str(output),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "PREPARED"
    assert summary["model_calls"] == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["case_id"] == "BDB5-R2"
    assert payload["readiness"] == "PREPARED"
    assert "model_visible_packet" in payload
    assert "manifest" not in payload
    assert "manifest" in payload["evaluator_only"]
    assert "ground_truth" not in json.dumps(payload).lower()
    assert "root_cause" not in json.dumps(payload).lower()
