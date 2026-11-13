"""Launch the local BLACKBOX dashboard.

This intentionally binds to loopback only. The service has no authentication or
tenant isolation, so it must not be exposed on a public interface.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Launch the local BLACKBOX dashboard.')
    parser.add_argument('--host', default='127.0.0.1', help='Loopback host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, help='Port (default: 8000)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open a browser')
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.host not in ('127.0.0.1', 'localhost', '::1'):
        raise SystemExit('Refusing to bind the unauthenticated dashboard to a non-loopback host.')
    # Make the project package and its relative default data paths work from any
    # current directory, not only the repository root.
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    url = f'http://{args.host}:{args.port}/'
    print(f'BLACKBOX dashboard: {url}')
    print('Local only. Press Ctrl+C to stop.')
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run('blackbox.app:app', host=args.host, port=args.port, log_level='info')


if __name__ == '__main__':
    main()
