"""Private subprocess entry; no model-supplied commands are accepted."""
import json
import sys
from pathlib import Path

from .agent_retrieval import _investigate_with_retrieval
from .providers import Provider
from .repair import fixtures
from .store import Store


def main():
    payload = json.loads(sys.stdin.buffer.read().decode('utf8'))
    registry = Path(payload['registry']).resolve()
    if registry.parent != (fixtures.PROJECT_ROOT / 'fixtures' / 'repair').resolve() or registry.suffix != '.json':
        raise ValueError('registry outside fixture directory')
    fixtures.REGISTRY_PATH = registry
    result = _investigate_with_retrieval(Store(payload['store']), Path(payload['repo']), payload['incident_id'],
        payload['fixture_name'], Provider('ollama', payload['model']), snapshot=payload['snapshot'],
        prompt_version=payload['prompt_version'])
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf8'))


if __name__ == '__main__':
    main()
