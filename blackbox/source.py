import os
import ast
import subprocess
from pathlib import Path
from .redaction import redact


def static_callers(repo: Path, commit: str, frame: dict) -> list[dict]:
    """Bounded same-file AST search; syntactic references are not runtime calls."""
    if not frame['path'].endswith('.py') or not frame['function'].isidentifier():
        return []
    env = os.environ.copy()
    env.update({'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_NO_REPLACE_OBJECTS': '1'})
    try:
        result = subprocess.run(['git', '-C', str(repo), 'show', f"{commit}:{frame['path']}"], capture_output=True, timeout=10, env=env, check=False)
        if result.returncode or len(result.stdout) > 1024 * 1024 or b'\0' in result.stdout:
            return []
        text = result.stdout.decode('utf-8')
        tree = ast.parse(text)
        lines = text.splitlines()
        matches = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == frame['function']:
                    # Skip nested scopes to avoid attributing their calls to the outer function.
                    nested = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)) and n is not node and n.lineno <= child.lineno <= getattr(n, 'end_lineno', n.lineno) for n in ast.walk(node))
                    if not nested:
                        matches.append({'caller': node.name, 'callee': frame['function'], 'path': frame['path'],
                                        'line': child.lineno, 'commit': commit, 'source_line': redact(lines[child.lineno - 1])[:300],
                                        'notice': 'Static same-file name match only; execution and binding are unverified.'})
        return matches[:3]
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, SyntaxError, RecursionError):
        return []


def resolve(repo: Path, commit: str, frame: dict, context_lines: int = 0) -> dict:
    result = {'path': frame['path'], 'line': frame['line'], 'function': frame['function'], 'commit': commit}
    env = os.environ.copy()
    env.update({'GIT_TERMINAL_PROMPT': '0', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_NO_REPLACE_OBJECTS': '1'})
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=10, env=env, check=False)
    try:
        check = git('cat-file', '-t', commit)
        if check.returncode or check.stdout.strip() != b'commit':
            return {**result, 'status': 'unresolved', 'reason': 'commit not found or not a commit'}
        blob = git('show', f"{commit}:{frame['path']}")
        if blob.returncode:
            return {**result, 'status': 'unresolved', 'reason': 'file not found at commit'}
        if len(blob.stdout) > 1024 * 1024 or b'\0' in blob.stdout:
            return {**result, 'status': 'unresolved', 'reason': 'source is binary or exceeds 1 MiB'}
        lines = blob.stdout.decode('utf-8', errors='replace').splitlines()
        if frame['line'] > len(lines):
            return {**result, 'status': 'unresolved', 'reason': 'line not present in file at commit'}
        result = {**result, 'status': 'resolved', 'source_line': redact(lines[frame['line'] - 1])}
        if context_lines:
            start = max(0, frame['line'] - 1 - context_lines)
            end = min(len(lines), frame['line'] + context_lines)
            result['context'] = [{'line': n + 1, 'text': redact(lines[n])} for n in range(start, end)]
        return result
    except (OSError, subprocess.TimeoutExpired):
        return {**result, 'status': 'unresolved', 'reason': 'Git unavailable, repository inaccessible, or lookup timed out'}
