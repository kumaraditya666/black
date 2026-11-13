"""Prepare a BDB-5 BugSwarm CI case without model inference.

R1 requires a local checkout at the pinned revision. R2 can be prepared from
the log alone because its evidence is the test-harness result.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.models import CaseId
from blackbox.bdb5.real_cases import CASES, PreparationError, prepare_ci_case
from blackbox.bdb5.scoring import canonical_json, digest
from blackbox.source import resolve


def _read_log(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
        log = payload.get("build_log")
        if not isinstance(log, str):
            raise PreparationError("JSON log payload has no string build_log")
        return log
    return text


def _source_reader(repo, commit, frame):
    if repo is None:
        raise PreparationError("R1 requires --repo pointing at the pinned checkout")
    return resolve(repo, commit, frame, context_lines=3)


def _default_output(case: CaseId, payload: dict) -> Path:
    directory = Path(tempfile.gettempdir()) / "bdb5_preparation"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{case.value}-{digest(payload)}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a real BDB-5 BugSwarm case; no inference or approval.",
    )
    parser.add_argument("--case", required=True, choices=["BDB5-R1", "BDB5-R2"])
    parser.add_argument("--log", required=True, help="BugSwarm JSON response or raw build log")
    parser.add_argument("--repo", help="local Git checkout at the pinned R1 revision")
    parser.add_argument("--output", help="JSON output path; default is outside the repository")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    case = CaseId(args.case)
    try:
        log_text = _read_log(Path(args.log))
        prepared = prepare_ci_case(
            log_text,
            CASES[case],
            repo=Path(args.repo).resolve() if args.repo else None,
            source_reader=_source_reader if case == CaseId.R1 else None,
        )
        payload = prepared.payload()
        output = Path(args.output) if args.output else _default_output(case, payload)
        output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
        print(canonical_json({
            "status": "PREPARED",
            "case_id": case.value,
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
            "case_id": case.value,
            "model_calls": 0,
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
