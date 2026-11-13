"""Validate an investigation result against a prepared BDB-5 packet.

This command does not call a model. It accepts a result JSON produced elsewhere,
checks the model/evaluator boundary, and stops at RUN_READY_FOR_REVIEW.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.runner import RunnerError, accept_prepared_result
from blackbox.bdb5.scoring import canonical_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a real-case result without scoring or approving it.",
    )
    parser.add_argument("--prepared", required=True, help="prepared JSON output")
    parser.add_argument("--result", required=True, help="InvestigationResult JSON")
    parser.add_argument(
        "--registry",
        default=str(ROOT / "fixtures" / "bdb5" / "bugswarm" / "registry.json"),
        help="optional fixture registry",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = json.loads(Path(args.prepared).read_text(encoding="utf-8"))
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
        run = accept_prepared_result(payload, result, registry=registry)
        print(canonical_json(run.payload()))
        return 0 if run.status == "RUN_READY_FOR_REVIEW" else 2
    except (OSError, ValueError, json.JSONDecodeError, RunnerError) as exc:
        print(canonical_json({
            "status": "RUN_REJECTED",
            "approved": False,
            "scored": False,
            "provider_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
