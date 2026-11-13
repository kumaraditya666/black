"""Prepare the real BDB5-T1 telemetry packet without inference or approval."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.scoring import canonical_json, digest
from blackbox.bdb5.telemetry import T1_N_MAX, prepare_t1_case


def _default_output(payload: dict) -> Path:
    directory = Path(tempfile.gettempdir()) / "bdb5_preparation"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"BDB5-T1-{digest(payload)}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare the real BDB5-T1 telemetry packet; no inference or approval.",
    )
    parser.add_argument(
        "--raw-dir",
        required=True,
        help="directory containing the three pinned T1 artifacts",
    )
    parser.add_argument(
        "--inventory",
        default=str(ROOT / "fixtures" / "bdb5" / "t1" / "service_inventory.json"),
        help="pinned unranked candidate inventory",
    )
    parser.add_argument(
        "--nmx",
        "--n-max",
        dest="n_max",
        type=int,
        default=T1_N_MAX,
        help=f"frozen log-row cap (must be {T1_N_MAX})",
    )
    parser.add_argument(
        "--output",
        help="prepared JSON path; default is outside the repository",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = prepare_t1_case(
            Path(args.raw_dir),
            Path(args.inventory),
            n_max=args.n_max,
        )
        output = Path(args.output) if args.output else _default_output(payload)
        output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        print(canonical_json({
            "status": "PREPARED",
            "case_id": "BDB5-T1",
            "readiness": "PREPARED",
            "model_calls": 0,
            "n_max": args.n_max,
            "packet_validation": payload["evaluator_only"]["packet_validation"],
            "telemetry": payload["evaluator_only"]["telemetry"],
            "output": str(output),
            "payload_hash": payload["payload_hash"],
        }))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({
            "status": "PREPARATION_FAILED",
            "case_id": "BDB5-T1",
            "model_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
