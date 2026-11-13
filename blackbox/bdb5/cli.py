"""Offline CLI for the BDB-5 synthetic harness."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .engine import evaluate_suite
from .models import CaseId
from .scoring import canonical_json, digest
from .spec import run_spec_checks
from .synthetic import self_test, synthetic_case, synthetic_suite


def _default_output(name: str, payload: dict) -> Path:
    directory = Path(tempfile.gettempdir()) / "bdb5_offline"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{name}-{digest(payload)}.json"


def _emit(name: str, payload: dict, output: str | None) -> int:
    path = Path(output) if output else _default_output(name, payload)
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    print(canonical_json(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="BDB-5 synthetic offline dry run; no provider or inference path exists.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true", help="run every synthetic scenario twice")
    group.add_argument("--validate-spec", action="store_true", help="validate static spec/readiness facts")
    group.add_argument("--synthetic-case", choices=[case.value for case in CaseId],
                       help="run synthetic scenarios for one case")
    group.add_argument("--synthetic-suite", action="store_true", help="run every synthetic scenario")
    parser.add_argument("--output", help="write JSON here; default is a temp directory outside the repo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        return _emit("self-test", {"mode": "SYNTHETIC_DRY_RUN", "self_test": self_test()}, args.output)
    if args.validate_spec:
        return _emit("validate-spec", {"mode": "SYNTHETIC_DRY_RUN", "spec": run_spec_checks()}, args.output)
    if args.synthetic_case:
        case = CaseId(args.synthetic_case)
        suite = evaluate_suite(synthetic_case(case))
        payload = {
            "mode": "SYNTHETIC_DRY_RUN",
            "case_id": case.value,
            "suite": suite.model_dump(mode="json"),
        }
        return _emit(f"synthetic-case-{case.value}", payload, args.output)
    if args.synthetic_suite:
        suite = evaluate_suite(synthetic_suite())
        payload = {
            "mode": "SYNTHETIC_DRY_RUN",
            "suite": suite.model_dump(mode="json"),
        }
        return _emit("synthetic-suite", payload, args.output)
    raise AssertionError("argparse allowed no action")
