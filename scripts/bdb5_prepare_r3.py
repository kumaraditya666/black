"""Prepare the BDB-5 R3 issue/source packet without inference or approval."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.issue_cases import R3, prepare_issue_case
from blackbox.bdb5.scoring import canonical_json, digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare BDB5-R3; no inference or approval.")
    parser.add_argument("--issue", default=str(ROOT / "fixtures" / "bdb5" / "r3" / "issue.txt"))
    parser.add_argument("--source", default=str(ROOT / "fixtures" / "bdb5" / "r3" / "response.py"))
    parser.add_argument("--output", help="JSON output path; default is outside the repository")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        prepared = prepare_issue_case(
            Path(args.issue).read_text(encoding="utf-8"),
            R3,
            source_path=Path(args.source),
        )
        payload = prepared.payload()
        output = Path(args.output) if args.output else (
            Path(tempfile.gettempdir()) / "bdb5_preparation"
            / f"BDB5-R3-{digest(payload)}.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        print(canonical_json({
            "status": "PREPARED",
            "case_id": "BDB5-R3",
            "readiness": prepared.manifest.readiness.value,
            "model_calls": 0,
            "packet_validation": prepared.packet_validation,
            "output": str(output),
            "payload_hash": payload["payload_hash"],
        }))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({
            "status": "PREPARATION_FAILED",
            "case_id": "BDB5-R3",
            "model_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
