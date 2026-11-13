"""One-time fixture authoring: refuses to overwrite any existing case or metadata."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'fixtures/repair'
CASES = [
    ('m4b_inventory', {'app.py': 'from limits import limit\n\ndef select(items, config):\n    return items[:limit(config)]\n',
                       'limits.py': 'def limit(config):\n    return config["limit"]\n',
                       'tests/test_reproduction.py': 'from app import select\n\ndef test_default():\n    assert select([1, 2], {}) == [1, 2]\n',
                       'tests/test_regression.py': 'from app import select\n\ndef test_explicit():\n    assert select([1, 2], {"limit": 1}) == [1]\n'},
     'limits.py', 'item limit should default to 10', 'KeyError', "'limit'", 'limit', 2, True),
    ('m4b_average', {'app.py': 'def average(values):\n    return sum(values) / (len(values) - 1)\n',
                     'tests/test_reproduction.py': 'from app import average\n\ndef test_single():\n    assert average([4]) == 4\n',
                     'tests/test_regression.py': 'from app import average\n\ndef test_multiple():\n    assert average([2, 4]) == 3\n'},
     'app.py', 'mean divides by the number of values', 'ZeroDivisionError', 'division by zero', 'average', 2, True),
    ('m4b_origin', {'app.py': 'def parse_count(raw):\n    return int(raw)\n',
                    'tests/test_reproduction.py': 'import pytest\nfrom app import parse_count\n\ndef test_bad_input():\n    with pytest.raises(ValueError):\n        parse_count("unknown")\n',
                    'tests/test_regression.py': 'from app import parse_count\n\ndef test_number():\n    assert parse_count("4") == 4\n'},
     'app.py', 'source of malformed input is not recorded', 'ValueError', "invalid literal for int() with base 10: 'unknown'", 'parse_count', 2, False),
    ('m4b_negative', {'app.py': 'def first_or_none(items):\n    return items[0] if items else None\n',
                      'tests/test_reproduction.py': 'from app import first_or_none\n\ndef test_empty():\n    assert first_or_none([]) is None\n',
                      'tests/test_regression.py': 'from app import first_or_none\n\ndef test_nonempty():\n    assert first_or_none([5]) == 5\n'},
     'app.py', 'empty inputs return None; reported IndexError is unsupported', 'IndexError', 'list index out of range', 'first_or_none', 2, False),
]


def main():
    metadata = [BASE / 'm4b-registry.json', BASE / 'm4b-ground-truth.json']
    if any(p.exists() for p in metadata) or any((BASE / x[0]).exists() for x in CASES):
        raise RuntimeError('refuse overwrite')
    fixtures, labels = [], []
    for name, files, allowed, expected, kind, message, function, line, positive in CASES:
        files['conftest.py'] = 'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n'
        hashes = {}
        for relative, source in files.items():
            target = BASE / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = source.encode('utf8')
            target.write_bytes(raw)
            hashes[relative] = hashlib.sha256(raw).hexdigest()
        frame = {'path': f'fixtures/repair/{name}/{allowed}', 'line': line, 'function': function}
        fixtures.append({'name': name, 'approved_for_m3a': True, 'description': 'Locally authored M4B trusted evaluation fixture',
                         'expected_behavior': expected, 'files': hashes, 'allowed_files': [allowed],
                         'event': {'exception_type': kind, 'message': message, 'frame': frame},
                         'reproduction': {'test': 'tests/test_reproduction.py::' + ('test_default' if name == 'm4b_inventory' else 'test_single' if name == 'm4b_average' else 'test_bad_input' if name == 'm4b_origin' else 'test_empty'), 'failure_marker': kind, 'reproducible': positive},
                         'regression': {'test': 'tests/test_regression.py'}})
        labels.append({'case': name, 'expected': expected, 'diagnosable': positive, 'required_source': frame['path'],
                       'mechanism': {'m4b_inventory': 'missing key', 'm4b_average': 'subtracting one from length', 'm4b_origin': 'invalid integer conversion', 'm4b_negative': 'unreproduced report'}[name],
                       'upstream': 'unknown' if not positive else expected})
    for path, value in zip(metadata, ({'fixtures': fixtures}, {'labels': labels, 'author_scorer': 'same operator, unblinded'})):
        path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf8'))


if __name__ == '__main__':
    main()
