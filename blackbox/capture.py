"""Capture unhandled FastAPI exceptions into the local BLACKBOX API."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import traceback
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI

LOGGER = logging.getLogger('blackbox.capture')
LOOPBACK_HOSTS = {'127.0.0.1', 'localhost', '::1'}
EXCLUDED_PARTS = {'.venv', 'venv', 'site-packages', 'node_modules', '.git', '__pycache__'}
THIS_FILE = Path(__file__).resolve()


def _repo_path(repo: str | Path | None) -> Path:
    value = Path(repo or os.environ.get('BLACKBOX_REPO') or Path.cwd()).expanduser()
    try:
        path = value.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f'BLACKBOX_REPO does not exist: {value}') from exc
    if not path.is_dir():
        raise RuntimeError(f'BLACKBOX_REPO is not a directory: {path}')
    return path


def _head_commit(repo: Path) -> str:
    result = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        detail = result.stderr.strip() or 'HEAD is unavailable'
        raise RuntimeError(f'BLACKBOX_REPO must be a Git repository with a commit: {detail}')
    return commit


def _api_url(value: str | Path | None) -> str:
    url = str(value or os.environ.get('BLACKBOX_API_URL') or 'http://127.0.0.1:8000/events')
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in LOOPBACK_HOSTS or parsed.username or parsed.password:
        raise RuntimeError('BLACKBOX_API_URL must be an unauthenticated loopback HTTP URL')
    return url


def _relative_frames(exc: BaseException, repo: Path) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for frame in traceback.extract_tb(exc.__traceback__):
        try:
            absolute = Path(frame.filename).resolve()
            relative = absolute.relative_to(repo).as_posix()
        except (OSError, ValueError):
            continue
        # A local virtualenv can live inside the repository. Its packages are
        # dependencies, not application source, and must not become evidence.
        if absolute == THIS_FILE or any(part.lower() in EXCLUDED_PARTS for part in absolute.parts):
            continue
        frames.append({'path': relative, 'line': frame.lineno, 'function': frame.name})
    return frames


def build_event(exc: BaseException, repo: str | Path, commit: str | None = None) -> dict[str, Any]:
    """Build the exact payload accepted by ``POST /events``."""
    repo_path = _repo_path(repo)
    frames = _relative_frames(exc, repo_path)
    if not frames:
        raise ValueError('No traceback frame belongs to BLACKBOX_REPO')
    return {
        'event_id': str(uuid.uuid4()),
        'occurred_at': datetime.now(timezone.utc).isoformat(),
        'commit': commit or _head_commit(repo_path),
        'exception_type': type(exc).__name__,
        'message': str(exc)[:8192],
        'traceback': ''.join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )[:65536],
        'frames': frames,
    }


def send_event(payload: dict[str, Any], api_url: str | None = None, timeout: float = 2.0,
               project_key: str | None = None) -> None:
    """Send one event to a local BLACKBOX or BLACKBOX Cloud endpoint."""
    headers = {'Content-Type': 'application/json'}
    if project_key:
        headers['X-Blackbox-Project-Key'] = project_key
    request = urllib.request.Request(
        _api_url(api_url),
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()


def install_blackbox(
    app: FastAPI,
    *,
    repo: str | Path | None = None,
    api_url: str | None = None,
    timeout: float = 2.0,
    project_key: str | None = None,
) -> None:
    """Capture unhandled exceptions from a FastAPI app.

    The original exception is always re-raised. If BLACKBOX is unavailable, the
    capture failure is logged and the application still returns its normal 500.
    Configuration is validated at startup so a bad repository or non-loopback
    API URL fails fast.
    """
    repo_path = _repo_path(repo)
    commit = _head_commit(repo_path)
    endpoint = _api_url(api_url)

    @app.middleware('http')
    async def capture_exception(request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            try:
                send_event(build_event(exc, repo_path, commit), endpoint, timeout, project_key=project_key)
            except Exception:
                LOGGER.exception('BLACKBOX capture failed for %s %s', request.method, request.url.path)
            raise

    LOGGER.info('BLACKBOX capture enabled for %s at %s', repo_path, endpoint)
