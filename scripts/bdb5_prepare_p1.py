"""Prepare the real BDB5-P1 external repair packet without inference or approval."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.external_repair import P1_BASE_COMMIT, prepare_p1_case
from blackbox.bdb5.scoring import canonical_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare the real BDB5-P1 external repair packet; no inference or approval.",
    )
    parser.add_argument("--issue", required=True, help="original issue text")
    parser.add_argument("--source", required=True, help="pinned sympy/core/_print_helpers.py")
    parser.add_argument(
        "--base-commit",
        default=P1_BASE_COMMIT,
        help="pinned SymPy base commit",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "bdb5_p1" / "bdb5_p1_prepared.json"),
        help="prepared JSON path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = prepare_p1_case(
            Path(args.issue),
            Path(args.source),
            base_commit=args.base_commit,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        print(canonical_json({
            "status": "PREPARED",
            "case_id": "BDB5-P1",
            "readiness": "PREPARED",
            "model_calls": 0,
            "packet_validation": payload["evaluator_only"]["packet_validation"],
            "external_repair": payload["evaluator_only"]["external_repair"],
            "output": str(output),
            "payload_hash": payload["payload_hash"],
        }))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({
            "status": "PREPARATION_FAILED",
            "case_id": "BDB5-P1",
            "model_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
