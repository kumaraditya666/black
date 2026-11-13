from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from blackbox.bdb5.real_cases import R1, R2, prepare_ci_case
from blackbox.bdb5.review import review_payload

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "fixtures" / "bdb5" / "bugswarm"
R1_LOG = LOGS / "109227527.log"
R2_LOG = LOGS / "83523531.log"
REGISTRY = LOGS / "registry.json"


def _fake_source(_repo, _commit, frame):
    return {
        "path": frame["path"],
        "line": frame["line"],
        "function": frame["function"],
        "status": "resolved",
        "source_line": "encoding=self.url_charset, errors=self.encoding_errors,",
        "context": [
            {"line": 356, "text": "    encoding=self.url_charset, errors=self.encoding_errors,"},
        ],
    }


def _r1_payload():
    return prepare_ci_case(
        R1_LOG.read_text(encoding="utf-8"), R1, source_reader=_fake_source
    ).payload()


def _r2_payload():
    return prepare_ci_case(R2_LOG.read_text(encoding="utf-8"), R2).payload()


def test_review_accepts_r1_and_r2_boundaries():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for case_id, payload in (("BDB5-R1", _r1_payload()), ("BDB5-R2", _r2_payload())):
        review = review_payload(payload, registry)
        assert review.case_id == case_id
        assert review.passed, review.issues
        assert review.status == "REVIEW_PASSED"
        assert review.payload()["approved"] is False
        assert review.payload()["model_calls"] == 0


def test_review_rejects_top_level_manifest_and_host_path():
    payload = _r2_payload()
    payload["manifest"] = payload["evaluator_only"]["manifest"]
    review = review_payload(payload)
    assert not review.passed
    assert any(item.startswith("no_top_level_manifest:") for item in review.issues)

    payload = _r2_payload()
    payload["model_visible_packet"]["evidence"][0]["text"] += "\n/home/travis/secret"
    review = review_payload(payload)
    assert not review.passed
    assert any(item.startswith("no_private_paths:") for item in review.issues)


def test_review_rejects_approval_and_application_source_leak_in_r2():
    payload = _r2_payload()
    payload["readiness"] = "APPROVED_FOR_EVALUATION"
    review = review_payload(payload)
    assert not review.passed
    assert any(item.startswith("prepared_not_approved:") for item in review.issues)

    payload = _r2_payload()
    payload["model_visible_packet"]["evidence"].append({
        "evidence_id": "source:1",
        "evidence_type": "SOURCE_EXCERPT",
        "text": "application source",
        "structured": None,
        "source_revision": payload["model_visible_packet"]["source_revision"],
    })
    review = review_payload(payload)
    assert not review.passed
    assert any(item.startswith("r2_no_source_evidence:") for item in review.issues)


def test_review_cli_writes_machine_readable_failure(tmp_path):
    payload = _r2_payload()
    payload["manifest"] = payload["evaluator_only"]["manifest"]
    prepared = tmp_path / "r2-tampered.json"
    prepared.write_text(json.dumps(payload), encoding="utf-8")
    command = [
        sys.executable,
        str(ROOT / "scripts" / "bdb5_review_prepared.py"),
        "--prepared", str(prepared),
        "--registry", str(REGISTRY),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 2
    output = json.loads(result.stdout)
    assert output["status"] == "REVIEW_FAILED"
    assert output["approved"] is False
    assert output["model_calls"] == 0
