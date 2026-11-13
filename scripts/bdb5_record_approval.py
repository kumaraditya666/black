"""Record an independent two-reviewer approval for a prepared case.

This command does not make a review independent. It requires explicit reviewer
IDs and attestations, writes outside the repository by default, and refuses to
record anything unless the prepared payload passes the read-only review.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.approval import ReviewerSignoff, build_approval
from blackbox.bdb5.label_vault import load_label_vault
from blackbox.bdb5.scoring import canonical_json, digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record two independent reviewer sign-offs for a prepared BDB-5 case.",
    )
    parser.add_argument("--prepared", required=True, help="prepared JSON output")
    parser.add_argument(
        "--vault",
        default=str(ROOT / "fixtures" / "bdb5" / "labels" / "label_vault.json"),
        help="evaluator-only label vault",
    )
    parser.add_argument("--reviewer", action="append", required=True,
                        help="reviewer ID; provide exactly two")
    parser.add_argument("--attestation", required=True,
                        help="reviewer attestation text, copied into both sign-offs")
    parser.add_argument("--attest-independent", action="store_true",
                        help="reviewers explicitly attest independence")
    parser.add_argument("--attest-conflict-free", action="store_true",
                        help="reviewers explicitly attest no conflict of interest")
    parser.add_argument("--output", help="approval JSON path; default is outside the repository")
    parser.add_argument("--registry",
                        default=str(ROOT / "fixtures" / "bdb5" / "bugswarm" / "registry.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        reviewers = list(args.reviewer)
        if len(reviewers) != 2 or len(set(reviewers)) != 2:
            raise ValueError("exactly two distinct --reviewer IDs are required")
        if not args.attest_independent or not args.attest_conflict_free:
            raise ValueError("both independence and conflict-free attestations are required")
        now = datetime.now(timezone.utc)
        signoffs = (
            ReviewerSignoff(
                reviewer_id=reviewers[0], role="PRIMARY", independent=True,
                conflict_free=True, attestation=args.attestation, reviewed_at=now,
            ),
            ReviewerSignoff(
                reviewer_id=reviewers[1], role="SECONDARY", independent=True,
                conflict_free=True, attestation=args.attestation, reviewed_at=now,
            ),
        )
        payload = json.loads(Path(args.prepared).read_text(encoding="utf-8"))
        vault = load_label_vault(Path(args.vault))
        registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
        approval = build_approval(
            payload, vault, signoffs, approved_at=now, registry=registry
        )
        if args.output:
            output = Path(args.output)
        else:
            directory = Path(tempfile.gettempdir()) / "bdb5_approvals"
            directory.mkdir(parents=True, exist_ok=True)
            output = directory / f"{approval.case_id.value}-{approval.approval_hash}.json"
        output.write_text(canonical_json(approval.model_dump(mode="json")) + "\n", encoding="utf-8")
        print(canonical_json({
            "status": "APPROVAL_RECORDED",
            "case_id": approval.case_id.value,
            "approval_hash": approval.approval_hash,
            "reviewers": [item.reviewer_id for item in approval.reviewers],
            "output": str(output),
            "model_calls": 0,
        }))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({
            "status": "APPROVAL_REJECTED",
            "model_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
