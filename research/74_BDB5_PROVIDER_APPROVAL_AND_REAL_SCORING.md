# BDB-5 Provider Gate, Approval and Real-Case Scoring

**Date:** 2026-11-10

**Status:** `BDB5_PROVIDER_APPROVAL_SCORING_IMPLEMENTED — SIX_EXPLORATORY_R2_CALLS — 9B_RESULT_ACCEPTED_FOR_REVIEW — NO_REAL_APPROVAL`

This document covers the implementation and six exploratory live R2 calls, not
a live benchmark run. The repository-level `LIVE_INFERENCE_ENABLED` remains
`False`; the exploratory call was opened only in a temporary process; no real
reviewer signed off; no real-case score is claimed.

## 1. Provider adapter

`blackbox/bdb5/provider.py` adds one OpenAI-compatible chat-completions adapter.

It:

- accepts only `EvidencePacket.model_visible_payload()`;
- builds a prompt containing the `InvestigationResult` schema and the visible
  packet;
- sends no tools, commands, repository files, labels or evaluator fields;
- validates the returned JSON as `InvestigationResult`;
- rejects a result whose `case_id` differs from the packet;
- requires the `abstention` key in the provider result schema and rejects
  `NOT_ESTABLISHED` results without a structured abstention;
- rejects reproduction or PASS executions that lack an artifact hash;
- never scores or approves the result.

The adapter requires both:

1. `LIVE_INFERENCE_ENABLED` to be true; and
2. an explicit `LiveExecutionGate` with `enabled=True` and an approval hash.

Neither condition is met by default in this checkout. The provider has an injected
transport seam for tests, so the request shape can be verified without a
network call. User-authorized exploratory R2 calls were made separately; they
are recorded in Documents 77 and 79.

Configured environment names, when a future run is authorized:

| Variable | Purpose |
|---|---|
| `BLACKBOX_BDB5_PROVIDER_URL` | API base URL |
| `BLACKBOX_BDB5_MODEL` | model identifier |
| `BLACKBOX_BDB5_API_KEY` | optional bearer token |

The adapter also supports a native Ollama protocol for local loopback models;
that path disables thinking and uses the native `/api/chat` format. The
repository-level `LIVE_INFERENCE_ENABLED` remains false. The exploratory R2
calls are recorded in Documents 77 and 79; none was independently approved or
scored.

## 2. Independent approval record

`blackbox/bdb5/approval.py` adds `ReviewerSignoff` and `ApprovalRecord`.

An approval requires:

- two distinct reviewer IDs;
- one `PRIMARY` and one `SECONDARY` reviewer;
- explicit `independent` and `conflict_free` attestations;
- timezone-aware review and approval timestamps;
- a passing packet review;
- a SHA-256 binding to the packet, manifest and label vault;
- an approval hash over the full record.

`validate_approval()` rejects a stale packet, a different label vault, a
different manifest, a changed reviewer list, or an approval that predates a
reviewer sign-off.

The mechanism cannot establish that a reviewer is real or independent. No
approval file is committed. `scripts/bdb5_record_approval.py` records two
explicit sign-offs outside the repository by default.

## 3. Evaluator-only label vault

`fixtures/bdb5/labels/label_vault.json` contains R1, R2 and R3 truth. It is a
separate evaluator artifact and is never read by the provider, packet builder or
reviewer. Loading verifies case IDs, truth validity, rationales and a canonical
vault hash.

R1 truth: `verktyg/requests.py`, `args`, line 356, L3 `SUPPORTED`, reproduction
required.

R2 truth: missing `types_dict.nml` fixture at `test_f90nml.py:211`, L0
`NOT_ESTABLISHED` for application source, application-source abstention
required, harness identification separately scored.

R3 truth: `django/http/response.py`, `make_bytes`, line 232, L3 `SUPPORTED`.

## 4. Real scoring

`blackbox/bdb5/real_score.py` requires:

1. a passing read-only packet review;
2. a valid independent approval bound to the packet and vault;
3. evaluator truth from the vault;
4. packet and result validation.

It then emits a `CaseScore` with:

- `mode = REAL_CASE_EVALUATION`
- `result_class = REAL_CASE_SCORE_NOT_BENCHMARK_RESULT`
- `synthetic = False`
- `provider_calls = 0`

A score is not an approval, and an approval is not a model result.

`scripts/bdb5_score_prepared.py` scores an explicit result file and an explicit
approval file. It makes no model call.

## 5. Verified behavior

`tests/test_bdb5/test_approval_scoring.py` and
`tests/test_bdb5/test_provider.py` cover:

- stale packet, manifest and label-vault rejection;
- missing second reviewer and missing secondary role;
- R1 and R2 real scoring with a recorded reproduction artifact;
- R2 source abstention separate from the harness claim;
- provider refusal before transport when the gate is closed;
- provider request containing only the visible packet;
- provider result validation and no scoring/approval.

The end-to-end R3 CLI path was also exercised with a temporary test approval:

```text
PREPARED
REVIEW_PASSED
APPROVAL_RECORDED
REAL_CASE_SCORED
provider_calls = 0
strict_pass = true
```

The temporary approval is not a real sign-off and is not stored in the
repository.

## 6. What remains external

- An actual independent human reviewer set.
- An authorized live provider call.
- A real model result and a real scored case.
- T1's frozen selection and isolation decisions.
- P1's isolated external-repository repair adapter.

Do not treat the test approval as approval of R1, R2 or R3.
