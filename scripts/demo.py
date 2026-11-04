"""Start the local service, capture a real sample exception, and save its report."""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'sample_repo'


def main():
    if not (REPO / '.git').exists():
        if REPO.exists() and any(REPO.iterdir()):
            raise SystemExit('sample_repo exists without Git; refusing to overwrite it')
        REPO.mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'sample_template' / 'buggy_app.py', REPO / 'buggy_app.py')
        subprocess.run(['git', 'init', '-q', str(REPO)], check=True)
        subprocess.run(['git', '-C', str(REPO), 'add', 'buggy_app.py'], check=True)
        subprocess.run(['git', '-C', str(REPO), '-c', 'user.name=BLACKBOX Demo', '-c', 'user.email=demo@example.invalid', 'commit', '-qm', 'Add intentionally buggy sample'], check=True)
    env = os.environ.copy()
    env['BLACKBOX_REPO'] = str(REPO)
    env['BLACKBOX_DB'] = str(ROOT / 'data' / 'events.db')
    server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'blackbox.app:app', '--host', '127.0.0.1', '--port', '18765'], cwd=ROOT, env=env)
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError('API server exited during startup')
            try:
                with urllib.request.urlopen('http://127.0.0.1:18765/openapi.json', timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('API server did not start')
        sample = subprocess.run([sys.executable, str(REPO / 'buggy_app.py')], cwd=REPO, capture_output=True, text=True, check=True)
        request = urllib.request.Request('http://127.0.0.1:18765/events', sample.stdout.encode(), {'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=10) as response:
            incident = json.load(response)
        with urllib.request.urlopen(f"http://127.0.0.1:18765/incidents/{incident['incident_id']}/report", timeout=10) as response:
            report = json.load(response)
        report['demonstration'] = 'Intentionally buggy local sample; not a production incident.'
        output = ROOT / 'data' / 'investigation-report.json'
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(f'\nReport saved to {output}')
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == '__main__':
    main()
