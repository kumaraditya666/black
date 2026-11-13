from __future__ import annotations

import json

from blackbox.bdb5.cli import main
from blackbox.bdb5.spec import run_spec_checks


def test_spec_checks_and_cli_self_test(tmp_path, capsys):
    spec = run_spec_checks()
    assert spec["status"] == "PASS"
    assert spec["live_inference_enabled"] is False

    output = tmp_path / "self-test.json"
    assert main(["--self-test", "--output", str(output)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["mode"] == "SYNTHETIC_DRY_RUN"
    assert printed["self_test"]["status"] == "PASS"
    assert printed["self_test"]["deterministic"] is True
    assert json.loads(output.read_text(encoding="utf-8")) == printed


def test_cli_synthetic_case_and_suite_are_read_only_and_classified(tmp_path, capsys):
    output = tmp_path / "suite.json"
    assert main(["--synthetic-suite", "--output", str(output)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["suite"]["result_class"] == "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT"
    assert payload["suite"]["case_count"] == 29

    case_output = tmp_path / "case.json"
    assert main(["--synthetic-case", "BDB5-R2", "--output", str(case_output)]) == 0
    case_payload = json.loads(capsys.readouterr().out)
    assert case_payload["case_id"] == "BDB5-R2"
    assert case_payload["suite"]["case_count"] == 4
