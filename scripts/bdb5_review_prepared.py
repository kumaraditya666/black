"""Review a prepared BDB-5 payload without approving it or calling a model."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.review import review_file
from blackbox.bdb5.scoring import canonical_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only boundary review for a prepared BDB-5 case.",
    )
    parser.add_argument("--prepared", required=True, help="prepared JSON output")
    parser.add_argument(
        "--registry",
        default=str(ROOT / "fixtures" / "bdb5" / "bugswarm" / "registry.json"),
        help="optional fixture registry for source-revision checks",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        review = review_file(Path(args.prepared), Path(args.registry))
        print(canonical_json(review.payload()))
        return 0 if review.passed else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({
            "status": "REVIEW_FAILED",
            "approved": False,
            "model_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
