"""Local CLI: list, preview, investigate, and inspect persisted findings."""
import argparse
import json
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8000'


def request(path, data=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=620) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(exc.read().decode()) from exc
    except OSError as exc:
        raise SystemExit('Cannot reach local service: ' + str(exc)) from exc


def main():
    parser = argparse.ArgumentParser(description='Local incident investigation CLI')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('list')
    for name in ('preview', 'start', 'history'):
        command = sub.add_parser(name)
        command.add_argument('incident', type=int)
        if name == 'start':
            command.add_argument('--consent-external-hash', help='Hash of manually reviewed preview; sends source and telemetry to Gemini')
            command.add_argument('--force', action='store_true')
    command = sub.add_parser('show')
    command.add_argument('investigation_id')
    args = parser.parse_args()
    if args.action == 'list': result = request('/incidents')
    elif args.action == 'preview': result = request(f'/incidents/{args.incident}/context')
    elif args.action == 'history': result = request(f'/incidents/{args.incident}/investigations')
    elif args.action == 'show': result = request(f'/investigations/{args.investigation_id}')
    else:
        result = request(f'/incidents/{args.incident}/investigations', {'force': args.force,
                         'consent_external': bool(args.consent_external_hash),
                         'reviewed_evidence_hash': args.consent_external_hash})
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
