"""Intentionally buggy sample; emits its real exception as a local event."""
import json
import subprocess
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def calculate_average(values):
    return sum(values) / len(values)


def main():
    return calculate_average([])


if __name__ == '__main__':
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--', 'buggy_app.py'], text=True)
    if dirty:
        raise SystemExit('Sample source differs from its commit; commit or restore it before capture')
    try:
        main()
    except Exception as exc:
        frames = []
        for frame in traceback.extract_tb(exc.__traceback__):
            try:
                path = Path(frame.filename).resolve().relative_to(ROOT).as_posix()
            except ValueError:
                continue
            frames.append({'path': path, 'line': frame.lineno, 'function': frame.name})
        print(json.dumps({'event_id': str(uuid.uuid4()), 'occurred_at': datetime.now(timezone.utc).isoformat(),
                          'commit': commit, 'exception_type': type(exc).__name__, 'message': str(exc),
                          'traceback': ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                          'frames': frames}))
