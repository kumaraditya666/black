"""Scan a whole Python codebase for concrete errors and review findings."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blackbox.codebase_audit import AuditResult, explain_findings, scan_codebase
from blackbox.providers import ProviderError, configured_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Scan a whole Python codebase for errors and likely fixes.')
    parser.add_argument('repo', nargs='?', default='.', help='Repository or source directory to scan')
    parser.add_argument('--include-tests', action='store_true', help='Include test files and tests directories')
    parser.add_argument('--ai', action='store_true', help='Ask the configured local model to explain findings')
    parser.add_argument('--max-ai-findings', type=int, default=10, help='Maximum findings sent to the model')
    parser.add_argument('--json', dest='json_path', help='Write the full report as JSON to this path')
    parser.add_argument('--max-output', type=int, default=100, help='Maximum findings printed to the terminal')
    return parser


def _print_header(result: AuditResult) -> None:
    errors = sum(item.severity == 'error' for item in result.findings)
    warnings = len(result.findings) - errors
    print(f'Repository: {result.repo}')
    print(f'Commit: {result.commit or "not a Git repository"}')
    print(f'Python files scanned: {result.files_scanned}')
    print(f'Files skipped: {len(result.skipped)}')
    print(f'Findings: {errors} errors, {warnings} warnings')
    if result.truncated:
        print('Scan truncated at the file limit.')


def _print_finding(finding, index: int) -> None:
    print()
    print(f'[{finding.severity.upper()}] {finding.path}:{finding.line}:{finding.column}')
    print(f'  {finding.message}')
    print(f'  rule: {finding.rule}')
    print(f'  fix: {finding.suggestion}')
    if finding.ai_explanation:
        print(f'  AI: {finding.ai_explanation}')
    if finding.ai_fix:
        print(f'  AI fix: {finding.ai_fix}')
    if finding.ai_confidence:
        print(f'  AI confidence: {finding.ai_confidence}')


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = scan_codebase(args.repo, include_tests=args.include_tests)
    except ValueError as exc:
        print(f'Cannot scan codebase: {exc}', file=sys.stderr)
        return 2

    if args.ai and result.findings:
        try:
            provider = configured_provider()
            explain_findings(result.findings, provider, limit=args.max_ai_findings)
        except ProviderError as exc:
            print(f'AI review skipped: {exc}', file=sys.stderr)

    _print_header(result)
    for index, finding in enumerate(result.findings[:max(0, args.max_output)], 1):
        _print_finding(finding, index)
    if len(result.findings) > args.max_output:
        print(f'\n... {len(result.findings) - args.max_output} more findings omitted; use --max-output or --json.')

    if args.json_path:
        path = Path(args.json_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding='utf8')
        print(f'\nJSON report: {path.resolve()}')

    return 1 if any(item.severity == 'error' for item in result.findings) else 0


if __name__ == '__main__':
    raise SystemExit(main())
