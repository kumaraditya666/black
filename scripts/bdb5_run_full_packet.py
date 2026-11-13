"""Run one approved case with the complete model-visible packet.

This command is deliberately separate from the default closed live gate. It
requires ``--allow-live`` and writes both the raw InvestigationResult and a run
record showing that no projection or truncation was used.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.bdb5.approval import load_approval
from blackbox.bdb5.full_packet import FullPacketError, FullPacketRunner
from blackbox.bdb5.label_vault import load_label_vault
from blackbox.bdb5.provider import (
    MAX_CONTEXT_LENGTH,
    ProviderConfig,
    ProviderError,
)
from blackbox.bdb5.scoring import canonical_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one approved BDB-5 case with the complete packet.",
    )
    parser.add_argument("--prepared", required=True, help="prepared JSON output")
    parser.add_argument("--approval", required=True, help="independent approval JSON")
    parser.add_argument(
        "--vault",
        default=str(ROOT / "fixtures" / "bdb5" / "labels" / "t1_label_vault.json"),
        help="evaluator-only label vault",
    )
    parser.add_argument("--out", required=True, help="raw InvestigationResult output")
    parser.add_argument("--record-out", help="run record output")
    parser.add_argument(
        "--registry",
        default=None,
        help="optional fixture registry",
    )
    parser.add_argument("--model", help="override BLACKBOX_BDB5_MODEL")
    parser.add_argument("--base-url", help="override BLACKBOX_BDB5_PROVIDER_URL")
    parser.add_argument(
        "--protocol",
        choices=("openai", "ollama"),
        help="override BLACKBOX_BDB5_PROTOCOL",
    )
    parser.add_argument(
        "--context-length",
        type=int,
        default=MAX_CONTEXT_LENGTH,
        help="provider input context window; defaults to 1048576",
    )
    parser.add_argument("--max-output", type=int, default=2_048)
    parser.add_argument(
        "--prompt-tokens",
        type=int,
        help="exact prompt token count from the provider tokenizer; required for preflight fit",
    )
    parser.add_argument(
        "--no-response-format",
        action="store_true",
        help="omit response_format for providers that do not enforce structured output",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high"),
        help="OpenRouter reasoning effort; use none for JSON-only extraction",
    )
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="required before any network request is sent",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = ProviderConfig.from_env()
        changes = {"context_length": args.context_length}
        if args.model:
            changes["model"] = args.model
        if args.base_url:
            changes["base_url"] = args.base_url
        if args.protocol:
            changes["protocol"] = args.protocol
        config = replace(config, **changes)
        config.validate()

        payload = json.loads(Path(args.prepared).read_text(encoding="utf-8"))
        approval = load_approval(Path(args.approval))
        vault = load_label_vault(Path(args.vault))
        registry = (
            json.loads(Path(args.registry).read_text(encoding="utf-8"))
            if args.registry
            else None
        )
        with FullPacketRunner(
            config,
            response_format=not args.no_response_format,
            reasoning_effort=args.reasoning_effort,
        ) as runner:
            run = runner.run(
                payload,
                approval=approval,
                vault=vault,
                allow_live=args.allow_live,
                max_output_tokens=args.max_output,
                prompt_tokens_preflight=args.prompt_tokens,
                registry=registry,
            )

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(run.result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        record_path = Path(args.record_out) if args.record_out else out.with_suffix(".run.json")
        record_path.write_text(
            json.dumps(run.payload(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(canonical_json(run.payload()))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ProviderError, FullPacketError) as exc:
        print(canonical_json({
            "status": "FULL_PACKET_RUN_REJECTED",
            "approved": False,
            "scored": False,
            "provider_calls": 0,
            "context_mode": "FULL_PACKET",
            "error": str(exc),
        }), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
