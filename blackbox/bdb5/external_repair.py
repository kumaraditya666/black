"""Preparation and scope checks for the external BDB5-P1 repair case.

This module is deliberately separate from ``blackbox.repair.eligibility``. The
trusted-fixture gate remains unchanged; P1 is an external repository case with
its own manifest and evaluator-only materials.

The preparation path is offline and deterministic. It never reads a hidden test
patch, a gold patch, or a fixed revision. The execution helper only builds
disposable candidate/evaluator workspaces: the candidate workspace never sees
the hidden tests, and the evaluator workspace is the only one passed to the
container runner.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .models import (
    CaseCategory,
    CaseId,
    CaseManifest,
    EvidenceItem,
    EvidencePacket,
    EvidenceType,
    Readiness,
)
from .scoring import digest
from .validation import validate_packet

P1_DATASET = "SWE-bench Verified"
P1_DATASET_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"
P1_REPOSITORY = "https://github.com/sympy/sympy"
P1_BASE_COMMIT = "cffd4e0f86fefd4802349a9f9b19ed70934ea354"
P1_ALLOWED_FILES = ("sympy/core/_print_helpers.py",)
P1_IMAGE = "swebench/sweb.eval.x86_64.sympy_1776_sympy-20590:latest"
P1_ADAPTER = "isolated-external-repair-v1"
P1_REQUIRED_DIMENSIONS = (
    "patch_applies",
    "patch_scope",
    "fail_to_pass",
    "pass_to_pass",
    "reproduction_before",
    "reproduction_after",
    "regression_safety",
)
P1_TASK_INSTRUCTIONS = (
    "You are repairing an external Python repository at the pinned revision. "
    "Read the issue and the supplied pinned source excerpt. Return a patch "
    "proposal for the allowed file only. Do not modify tests or any other "
    "file. The hidden tests are not provided; do not claim that a test ran or "
    "passed unless an execution artifact is supplied. The patch must target "
    "the observed regression and preserve existing behavior."
)
PATCH_HEADER = re.compile(r"^(?:---|\+\+\+) ([ab]/)?([^\t\n]+)")
PATCH_MARKER = re.compile(r"(?m)^\s*(?:diff --git |--- [ab]/|\+\+\+ [ab]/)")


class ExternalRepairError(ValueError):
    """The external case is incomplete, malformed, or outside its pin."""


@dataclass(frozen=True)
class ExternalRepairSpec:
    """Evaluator-side execution settings for one external repair case."""

    base_commit: str = P1_BASE_COMMIT
    allowed_files: tuple[str, ...] = P1_ALLOWED_FILES
    image: str = P1_IMAGE
    python_executable: str = "/opt/miniconda3/envs/testbed/bin/python"
    test_node: str | None = None
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.base_commit):
            raise ExternalRepairError("base commit must be a 40-character lowercase SHA")
        if not self.allowed_files or len(set(self.allowed_files)) != len(self.allowed_files):
            raise ExternalRepairError("allowed_files must be non-empty and unique")
        for item in self.allowed_files:
            _safe_repo_path(item)
        if not self.image.strip():
            raise ExternalRepairError("image must be non-empty")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_repo_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or ":" in value
        or value.startswith("-")
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in value.split("/"))
        or any(ord(char) < 32 for char in value)
    ):
        raise ExternalRepairError("path must be a repository-relative POSIX path")
    return value


def is_test_path(path: str) -> bool:
    """Return true for paths that must never be edited by a candidate patch."""

    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else ""
    return (
        "test" in parts
        or "tests" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def changed_files_from_patch(patch: str) -> tuple[str, ...]:
    """Extract changed repository paths from a unified diff."""

    if not patch.strip():
        raise ExternalRepairError("candidate patch is empty")
    found: list[str] = []
    for line in patch.splitlines():
        match = PATCH_HEADER.match(line)
        if not match:
            continue
        path = match.group(2).strip()
        if path == "/dev/null":
            continue
        path = path[2:] if path.startswith(("a/", "b/")) else path
        _safe_repo_path(path)
        if path not in found:
            found.append(path)
    if not found:
        raise ExternalRepairError("candidate patch has no changed file paths")
    return tuple(found)


def check_patch_scope(
    patch: str,
    allowed_files: Iterable[str] = P1_ALLOWED_FILES,
) -> tuple[str, ...]:
    """Validate patch scope without applying it or consulting a label."""

    allowed = tuple(allowed_files)
    if not allowed:
        raise ExternalRepairError("allowed file scope is empty")
    changes = changed_files_from_patch(patch)
    outside = sorted(set(changes) - set(allowed))
    if outside:
        raise ExternalRepairError("patch changes files outside the allowed scope: " + ", ".join(outside))
    tests = sorted(item for item in changes if is_test_path(item))
    if tests:
        raise ExternalRepairError("patch changes test files: " + ", ".join(tests))
    return changes


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
    )
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=env,
        check=False,
    )


def verify_checkout(repo: Path, spec: ExternalRepairSpec = ExternalRepairSpec()) -> None:
    """Verify that the checkout is the pinned base and contains allowed files."""

    repo = Path(repo).resolve()
    if not repo.is_dir():
        raise ExternalRepairError("repository directory does not exist")
    inside = _git(repo, "rev-parse", "--is-inside-work-tree")
    if inside.returncode or inside.stdout.strip() != "true":
        raise ExternalRepairError("path is not a Git worktree")
    head = _git(repo, "rev-parse", "HEAD")
    if head.returncode or head.stdout.strip() != spec.base_commit:
        raise ExternalRepairError("checkout is not at the pinned base commit")
    dirty = _git(repo, "status", "--porcelain")
    if dirty.returncode or dirty.stdout.strip():
        raise ExternalRepairError("checkout is not clean")
    for item in spec.allowed_files:
        if not (repo / item).is_file():
            raise ExternalRepairError(f"allowed source file is missing: {item}")


def _copy_worktree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ExternalRepairError(f"destination already exists: {destination}")
    shutil.copytree(source, destination, symlinks=True)


def _apply_patch(repo: Path, patch: str, *, check: bool = False) -> None:
    args = ["apply", "--check"] if check else ["apply"]
    result = subprocess.run(
        ["git", "-C", str(repo), *args, "-"],
        input=patch,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ExternalRepairError("patch does not apply: " + detail[:1000])


def build_workspaces(
    base_repo: Path,
    candidate_patch: str,
    hidden_test_patch: str,
    destination: Path,
    spec: ExternalRepairSpec = ExternalRepairSpec(),
) -> tuple[Path, Path]:
    """Create separate candidate and evaluator copies.

    The candidate copy receives only the candidate patch. The evaluator copy
    receives the candidate patch and the hidden test patch, and is the only
    workspace that may be mounted into the execution container.
    """

    if not hidden_test_patch.strip():
        raise ExternalRepairError("hidden test patch is empty")
    changes = check_patch_scope(candidate_patch, spec.allowed_files)
    verify_checkout(base_repo, spec)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    candidate = destination / "candidate"
    evaluator = destination / "evaluator"
    try:
        _copy_worktree(base_repo, candidate)
        _copy_worktree(base_repo, evaluator)
        _apply_patch(candidate, candidate_patch, check=True)
        _apply_patch(candidate, candidate_patch)
        _apply_patch(evaluator, candidate_patch, check=True)
        _apply_patch(evaluator, candidate_patch)
        _apply_patch(evaluator, hidden_test_patch, check=True)
        _apply_patch(evaluator, hidden_test_patch)
        candidate_changes = _git(
            candidate, "diff", "--name-only", "--ignore-space-at-eol"
        ).stdout.splitlines()
        if tuple(candidate_changes) != changes:
            raise ExternalRepairError("candidate workspace changed files do not match the patch")
        evaluator_changes = _git(
            evaluator, "diff", "--name-only", "--ignore-space-at-eol"
        ).stdout.splitlines()
        if not set(changes).issubset(evaluator_changes):
            raise ExternalRepairError("evaluator workspace lacks the candidate patch")
        if any(is_test_path(item) for item in changes):
            raise ExternalRepairError("candidate patch changes tests")
        return candidate, evaluator
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def build_evaluator_workspace(
    base_repo: Path,
    hidden_test_patch: str,
    destination: Path,
    spec: ExternalRepairSpec = ExternalRepairSpec(),
) -> Path:
    """Create a clean evaluator-only workspace with hidden tests applied."""

    if not hidden_test_patch.strip():
        raise ExternalRepairError("hidden test patch is empty")
    verify_checkout(base_repo, spec)
    destination = Path(destination)
    if destination.exists():
        raise ExternalRepairError(f"destination already exists: {destination}")
    try:
        _copy_worktree(base_repo, destination)
        _apply_patch(destination, hidden_test_patch, check=True)
        _apply_patch(destination, hidden_test_patch)
        changed = tuple(
            _git(destination, "diff", "--name-only", "--ignore-space-at-eol")
            .stdout.splitlines()
        )
        if not changed or any(not is_test_path(item) for item in changed):
            raise ExternalRepairError("hidden test patch must change test files only")
        return destination
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _test_arguments(test_node: str) -> list[str]:
    """Translate a test identifier into the image's ``bin/test`` arguments."""

    file, separator, keyword = test_node.partition("::")
    if not file:
        raise ExternalRepairError("test_node must include a test file")
    _safe_repo_path(file)
    arguments = [file]
    if separator and keyword:
        arguments.extend(["-k", keyword])
    return arguments


def run_evaluator_tests(
    evaluator_workspace: Path,
    spec: ExternalRepairSpec = ExternalRepairSpec(),
) -> dict[str, Any]:
    """Run evaluator tests in Docker using the image's SymPy test runner."""

    if spec.test_node is None or not spec.test_node.strip():
        raise ExternalRepairError("test_node is required for external evaluation")
    image_id = os.environ.get("BLACKBOX_REPAIR_DOCKER_IMAGE_ID", "").strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ExternalRepairError("an explicit local image ID is required for P1")
    if not (Path(evaluator_workspace) / ".git").is_dir():
        raise ExternalRepairError("evaluator workspace is not a Git worktree")
    source = str(Path(evaluator_workspace).resolve())
    name = "blackbox-p1-" + uuid.uuid4().hex
    command = [
        "docker", "run", "--rm", "--name", name,
        "--network", "none", "--user", "65534:65534", "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--memory", "1g", "--memory-swap", "1g",
        "--pids-limit", "256", "--cpus", "1", "--pull", "never",
        "--mount", f"type=bind,source={source},target=/workspace,readonly",
        "-w", "/workspace", "-e", "HOME=/tmp", "-e", "PYTHONPATH=/workspace",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "--entrypoint", spec.python_executable, image_id,
        "/workspace/bin/test", *_test_arguments(spec.test_node),
        "--no-colors", "--no-subprocess",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=spec.timeout_seconds, check=False,
        )
        return {
            "returncode": completed.returncode,
            "timed_out": False,
            "isolation": "docker:bin/test",
            "output": completed.stdout + completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "returncode": None,
            "timed_out": True,
            "isolation": "docker:bin/test",
            "output": output,
        }


def build_p1_payload(
    *,
    issue_text: str,
    source_text: str,
    issue_reference: str,
    base_commit: str = P1_BASE_COMMIT,
    allowed_files: tuple[str, ...] = P1_ALLOWED_FILES,
) -> dict[str, Any]:
    """Build the model-visible P1 packet without any label or test material."""

    if base_commit != P1_BASE_COMMIT:
        raise ExternalRepairError("P1 base commit is frozen")
    if tuple(allowed_files) != P1_ALLOWED_FILES:
        raise ExternalRepairError("P1 allowed file scope is frozen")
    if not issue_text.strip() or not source_text.strip():
        raise ExternalRepairError("issue text and source text are required")
    if PATCH_MARKER.search(issue_text) or PATCH_MARKER.search(source_text):
        raise ExternalRepairError("model-visible P1 input contains a patch/diff marker")
    lowered = (issue_text + "\n" + source_text).lower()
    for forbidden in ("gold_patch", "test_patch", "fail_to_pass", "pass_to_pass", "fix_commit"):
        if forbidden in lowered:
            raise ExternalRepairError(f"model-visible P1 input contains {forbidden}")

    issue_hash = sha256_text(issue_text)
    source_hash = sha256_text(source_text)
    artifact_hashes = {
        "issue_text": issue_hash,
        "source_excerpt": source_hash,
    }
    evidence = (
        EvidenceItem(
            evidence_id="issue:1",
            evidence_type=EvidenceType.ISSUE_TEXT,
            text=issue_text,
            structured={"reference": issue_reference},
        ),
        EvidenceItem(
            evidence_id="source:1",
            evidence_type=EvidenceType.SOURCE_EXCERPT,
            text=source_text,
            structured={"path": allowed_files[0], "revision": base_commit},
            source_revision=base_commit,
        ),
    )
    packet = EvidencePacket(
        case_id=CaseId.P1,
        task_instructions=P1_TASK_INSTRUCTIONS,
        evidence=evidence,
        candidate_inventory=(),
        source_revision=base_commit,
        artifact_hashes=artifact_hashes,
    )
    manifest = CaseManifest(
        case_id=CaseId.P1,
        dataset=P1_DATASET,
        dataset_revision=P1_DATASET_REVISION,
        repository=P1_REPOSITORY,
        source_revision=base_commit,
        case_category=CaseCategory.REPAIR,
        required_evidence_types=(EvidenceType.ISSUE_TEXT, EvidenceType.SOURCE_EXCERPT),
        allowed_files=allowed_files,
        allowed_scope=allowed_files,
        required_dimensions=P1_REQUIRED_DIMENSIONS,
        readiness=Readiness.PREPARED,
        adapter_requirements=(P1_ADAPTER,),
        artifact_hashes=artifact_hashes,
        synthetic=False,
    )
    report = validate_packet(manifest, packet)
    if not report.passed:
        raise ExternalRepairError(
            "prepared P1 packet failed validation: "
            + ", ".join(item.code for item in report.errors)
        )

    external = {
        "base_commit": base_commit,
        "allowed_files": list(allowed_files),
        "image": P1_IMAGE,
        "adapter": P1_ADAPTER,
        "hidden_test_location": "evaluator_only",
        "test_command": "bin/test <hidden test file> [ -k <test> ]",
        "image_pulled": False,
        "execution_verified": False,
    }
    return {
        "mode": "REAL_CASE_PREPARATION_ONLY",
        "model_calls": 0,
        "case_id": CaseId.P1.value,
        "readiness": Readiness.PREPARED.value,
        "model_visible_packet": packet.model_visible_payload(),
        "evaluator_only": {
            "manifest": manifest.model_dump(mode="json"),
            "packet_validation": report.model_dump(mode="json"),
            "source_frame": {
                "path": allowed_files[0],
                "function": "Printable",
                "revision": base_commit,
            },
            "external_repair": external,
        },
        "payload_hash": digest(
            {
                "case_id": CaseId.P1.value,
                "manifest": manifest.model_dump(mode="json"),
                "packet": packet.model_visible_payload(),
                "external_repair": external,
            }
        ),
    }


def prepare_p1_case(
    issue_path: Path,
    source_path: Path,
    *,
    issue_reference: str = "https://github.com/sympy/sympy/issues/20567",
    base_commit: str = P1_BASE_COMMIT,
) -> dict[str, Any]:
    issue_text = Path(issue_path).read_text(encoding="utf-8")
    source_text = Path(source_path).read_text(encoding="utf-8")
    return build_p1_payload(
        issue_text=issue_text,
        source_text=source_text,
        issue_reference=issue_reference,
        base_commit=base_commit,
    )


__all__ = [
    "ExternalRepairError",
    "ExternalRepairSpec",
    "P1_ADAPTER",
    "P1_ALLOWED_FILES",
    "P1_BASE_COMMIT",
    "P1_DATASET",
    "P1_DATASET_REVISION",
    "P1_IMAGE",
    "P1_REPOSITORY",
    "P1_REQUIRED_DIMENSIONS",
    "P1_TASK_INSTRUCTIONS",
    "build_p1_payload",
    "build_evaluator_workspace",
    "build_workspaces",
    "changed_files_from_patch",
    "check_patch_scope",
    "is_test_path",
    "prepare_p1_case",
    "run_evaluator_tests",
    "sha256_text",
    "verify_checkout",
]
