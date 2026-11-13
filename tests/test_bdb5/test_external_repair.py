from __future__ import annotations

from pathlib import Path

import pytest

from blackbox.bdb5.external_repair import (
    ExternalRepairError,
    build_p1_payload,
    check_patch_scope,
    prepare_p1_case,
)
from blackbox.bdb5.label_vault import load_label_vault
from blackbox.bdb5.review import review_payload

ROOT = Path(__file__).resolve().parents[2]
ISSUE = ROOT / "data" / "bdb5_p1" / "inputs" / "issue.txt"
SOURCE = ROOT / "data" / "bdb5_p1" / "inputs" / "_print_helpers_excerpt.py"


def _payload():
    return prepare_p1_case(ISSUE, SOURCE)


def test_p1_payload_is_prepared_and_review_passes():
    payload = _payload()
    assert payload["readiness"] == "PREPARED"
    assert payload["model_calls"] == 0
    review = review_payload(payload)
    assert review.passed, review.issues
    assert review.case_id == "BDB5-P1"
    assert review.payload()["approved"] is False


def test_p1_visible_packet_contains_only_issue_and_source():
    packet = _payload()["model_visible_packet"]
    types = {item["evidence_type"] for item in packet["evidence"]}
    assert types == {"ISSUE_TEXT", "SOURCE_EXCERPT"}
    text = str(packet).lower()
    for forbidden in ("gold_patch", "test_patch", "fail_to_pass", "pass_to_pass", "fix_commit"):
        assert forbidden not in text
    assert packet["source_revision"] == "cffd4e0f86fefd4802349a9f9b19ed70934ea354"
    assert packet["candidate_inventory"] == []


def test_p1_scope_accepts_only_the_allowed_file():
    patch = (
        "diff --git a/sympy/core/_print_helpers.py b/sympy/core/_print_helpers.py\n"
        "--- a/sympy/core/_print_helpers.py\n"
        "+++ b/sympy/core/_print_helpers.py\n"
        "@@ -1,2 +1,3 @@\n"
        " class Printable:\n"
        "+    __slots__ = ()\n"
    )
    assert check_patch_scope(patch) == ("sympy/core/_print_helpers.py",)


def test_p1_scope_rejects_test_and_out_of_scope_changes():
    test_patch = (
        "diff --git a/sympy/core/tests/test_basic.py b/sympy/core/tests/test_basic.py\n"
        "--- a/sympy/core/tests/test_basic.py\n"
        "+++ b/sympy/core/tests/test_basic.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    with pytest.raises(ExternalRepairError, match="outside the allowed scope"):
        check_patch_scope(test_patch)
    other = (
        "diff --git a/sympy/core/basic.py b/sympy/core/basic.py\n"
        "--- a/sympy/core/basic.py\n"
        "+++ b/sympy/core/basic.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    with pytest.raises(ExternalRepairError, match="outside the allowed scope"):
        check_patch_scope(other)


def test_p1_vault_is_separate_and_loads():
    vault = load_label_vault(ROOT / "fixtures" / "bdb5" / "labels" / "p1_label_vault.json")
    truth = vault.cases[next(iter(vault.cases))]
    assert truth.case_id.value == "BDB5-P1"
    assert truth.expected_patch is not None
    assert truth.expected_patch.allowed_files == ("sympy/core/_print_helpers.py",)
    assert truth.expected_patch.fail_to_pass == ("test_immutable",)


def test_p1_source_must_be_pinned():
    with pytest.raises(ExternalRepairError, match="base commit is frozen"):
        build_p1_payload(
            issue_text=ISSUE.read_text(encoding="utf-8"),
            source_text=SOURCE.read_text(encoding="utf-8"),
            issue_reference="https://github.com/sympy/sympy/issues/20567",
            base_commit="0" * 40,
        )
