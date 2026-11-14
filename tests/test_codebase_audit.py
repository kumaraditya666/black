from types import SimpleNamespace

from blackbox.codebase_audit import explain_findings, scan_codebase


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf8')


def test_scan_finds_pyflakes_and_ast_errors(tmp_path):
    repo = tmp_path / 'repo'
    _write(repo / 'app.py', '''import os

def risky(items=[]):
    return eval("1")

def divide():
    return 1 / 0

def unsafe():
    try:
        pass
    except:
        pass

print(missing_name)
''')

    result = scan_codebase(repo)
    rules = {finding.rule for finding in result.findings}

    assert result.files_scanned == 1
    assert {'UnusedImport', 'mutable-default', 'dynamic-code',
            'division-by-zero', 'bare-except', 'UndefinedName'} <= rules
    assert any(finding.severity == 'error' for finding in result.findings)
    assert all(finding.suggestion for finding in result.findings)


def test_scan_reports_syntax_errors_without_crashing(tmp_path):
    repo = tmp_path / 'repo'
    _write(repo / 'broken.py', 'def broken(:\n    pass\n')

    result = scan_codebase(repo)

    assert result.files_scanned == 1
    assert [finding.rule for finding in result.findings] == ['SyntaxError']


def test_tests_are_skipped_by_default_and_can_be_included(tmp_path):
    repo = tmp_path / 'repo'
    _write(repo / 'app.py', 'value = 1\n')
    _write(repo / 'tests' / 'test_app.py', 'print(undefined_in_test)\n')

    default = scan_codebase(repo)
    included = scan_codebase(repo, include_tests=True)

    assert default.files_scanned == 1
    assert included.files_scanned == 2
    assert any(finding.path == 'tests/test_app.py' for finding in included.findings)


def test_virtualenv_files_are_not_scanned(tmp_path):
    repo = tmp_path / 'repo'
    _write(repo / 'app.py', 'value = 1\n')
    _write(repo / '.venv' / 'Lib' / 'bad.py', 'print(undefined_dependency)\n')

    result = scan_codebase(repo)

    assert result.files_scanned == 1
    assert not any('.venv' in finding.path for finding in result.findings)


def test_ai_explanation_is_attached(tmp_path):
    repo = tmp_path / 'repo'
    _write(repo / 'app.py', 'print(undefined_name)\n')
    result = scan_codebase(repo)

    class FakeProvider:
        def structured(self, *args, **kwargs):
            return SimpleNamespace(text='{"explanation":"The name is not defined.","fix":"Define it first.","confidence":"HIGH"}')

    explain_findings(result.findings, FakeProvider(), limit=1)

    assert result.findings[0].ai_explanation == 'The name is not defined.'
    assert result.findings[0].ai_fix == 'Define it first.'
    assert result.findings[0].ai_confidence == 'HIGH'
