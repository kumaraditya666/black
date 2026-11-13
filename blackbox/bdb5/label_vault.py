"""Evaluator-only label vault for prepared real cases.

The vault is intentionally a separate file from the model-visible packet. It
contains no packet data, and no function here can serialize truth into a packet.
Loading verifies the schema, case IDs, and a content hash so labels cannot be
silently swapped between runs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import CaseId, GroundTruth
from .scoring import digest


VAULT_SCHEMA = "bdb5-label-vault-v1"


class LabelVaultError(ValueError):
    """The evaluator-only label vault is malformed or inconsistent."""


@dataclass(frozen=True)
class LabelVault:
    cases: dict[CaseId, GroundTruth]
    rationales: dict[CaseId, str]
    references: dict[CaseId, tuple[str, ...]]
    vault_hash: str
    source: str

    def truth(self, case_id: CaseId) -> GroundTruth:
        try:
            return self.cases[case_id]
        except KeyError as exc:
            raise LabelVaultError(f"label vault has no truth for {case_id.value}") from exc

    def payload(self) -> dict[str, Any]:
        """Return vault metadata without exposing truth to normal callers."""
        return {
            "schema_version": VAULT_SCHEMA,
            "vault_hash": self.vault_hash,
            "cases": sorted(case.value for case in self.cases),
            "source": self.source,
        }


def _parse_vault(data: dict[str, Any], source: str) -> LabelVault:
    if data.get("schema_version") != VAULT_SCHEMA:
        raise LabelVaultError(f"unsupported label vault schema: {data.get('schema_version')!r}")
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, dict) or not raw_cases:
        raise LabelVaultError("label vault requires a non-empty cases object")

    cases: dict[CaseId, GroundTruth] = {}
    rationales: dict[CaseId, str] = {}
    references: dict[CaseId, tuple[str, ...]] = {}
    for raw_case_id, entry in raw_cases.items():
        try:
            case_id = CaseId(raw_case_id)
        except ValueError as exc:
            raise LabelVaultError(f"unknown case ID {raw_case_id!r}") from exc
        if not isinstance(entry, dict):
            raise LabelVaultError(f"case {raw_case_id} must be an object")
        truth = entry.get("truth")
        if not isinstance(truth, dict):
            raise LabelVaultError(f"case {raw_case_id} has no truth object")
        try:
            parsed = GroundTruth.model_validate(truth)
        except Exception as exc:
            raise LabelVaultError(f"case {raw_case_id} truth is invalid: {exc}") from exc
        if parsed.case_id != case_id:
            raise LabelVaultError(f"case {raw_case_id} truth has a different case_id")
        rationale = entry.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise LabelVaultError(f"case {raw_case_id} requires a rationale")
        refs = entry.get("references", ())
        if not isinstance(refs, list) or any(not isinstance(item, str) or not item for item in refs):
            raise LabelVaultError(f"case {raw_case_id} references must be non-empty strings")
        cases[case_id] = parsed
        rationales[case_id] = rationale
        references[case_id] = tuple(refs)

    return LabelVault(
        cases=cases,
        rationales=rationales,
        references=references,
        vault_hash=digest(data),
        source=source,
    )


def load_label_vault(path: Path) -> LabelVault:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabelVaultError(f"cannot read label vault {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LabelVaultError("label vault root must be an object")
    return _parse_vault(data, str(path))


def label_vault_hash(vault: LabelVault) -> str:
    return vault.vault_hash


__all__ = [
    "LabelVault",
    "LabelVaultError",
    "VAULT_SCHEMA",
    "label_vault_hash",
    "load_label_vault",
]
