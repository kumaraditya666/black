"""Score an approved real BDB-5 case. No model or provider call is made."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.approval import load_approval
from blackbox.bdb5.label_vault import load_label_vault
from blackbox.bdb5.models import InvestigationResult
from blackbox.bdb5.real_score import score_approved_case
from blackbox.bdb5.scoring import canonical_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score an approved real BDB-5 case; no inference is performed.",
    )
    parser.add_argument("--prepared", required=True, help="prepared JSON output")
    parser.add_argument("--result", required=True, help="InvestigationResult JSON")
    parser.add_argument(
        "--vault",
        default=str(ROOT / "fixtures" / "bdb5" / "labels" / "label_vault.json"),
        help="evaluator-only label vault",
    )
    parser.add_argument("--approval", required=True, help="independent approval JSON")
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
        result = InvestigationResult.model_validate(
            json.loads(Path(args.result).read_text(encoding="utf-8"))
        )
        vault = load_label_vault(Path(args.vault))
        approval = load_approval(Path(args.approval))
        registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
        run = score_approved_case(payload, result, vault, approval, registry=registry)
        print(canonical_json(run.payload()))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({
            "status": "REAL_CASE_SCORE_REJECTED",
            "approved": False,
            "scored": False,
            "provider_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
