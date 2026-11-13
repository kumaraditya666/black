# BDB-5 R1/R2 Packet Review and Run Envelope

**Date:** 2026-11-10

**Status:** `BDB5_R1_R2_PACKET_REVIEW_PASSED — RUN_ENVELOPE_READY — NO_INFERENCE`

## Outcome

The prepared R1 and R2 payloads now pass a reusable read-only boundary review.
A separate run envelope gives an injected responder only the model-visible
packet and validates the returned result without scoring, approving, or calling
a provider.

This is not a live benchmark run. `approved` and `scored` remain false, and both
cases remain `PREPARED`.

## Packet review

`blackbox/bdb5/review.py` checks:

- the payload is `REAL_CASE_PREPARATION_ONLY` with zero model calls;
- `readiness` is still `PREPARED`, never `APPROVED_FOR_EVALUATION`;
- the manifest is not at the top level;
- the model-visible object contains exactly the packet serializer keys;
- forbidden label fields and private host paths are absent;
- the serialized manifest and packet validate consistently;
- R1 has CI and source evidence with the expected source frame;
- R2 has CI and test-result evidence and no source-excerpt claim;
- source revisions match the fixture registry.

Actual prepared outputs:

| Case | Review | Issues |
|---|---|---|
| BDB5-R1 | `REVIEW_PASSED` | none |
| BDB5-R2 | `REVIEW_PASSED` | none |

CLI:

```bash
python scripts/bdb5_review_prepared.py --prepared <prepared.json>
```

The CLI exits `0` only for `REVIEW_PASSED`; it never approves a case.

## Run envelope

`blackbox/bdb5/runner.py` implements the next boundary:

- reviews the prepared payload before doing anything else;
- reconstructs the manifest and packet;
- gives an injected responder **only** a copy of
  `packet.model_visible_payload()`;
- accepts an `InvestigationResult` or its JSON form;
- runs `validate_result` for case IDs, citations, source revisions and
  unrecorded execution claims;
- returns `RUN_READY_FOR_REVIEW` or `RUN_REJECTED`.

The runner imports no provider, calls no model, does not score, and does not
approve. The CLI validates an already-produced result:

```bash
python scripts/bdb5_run_prepared.py \
  --prepared <prepared.json> \
  --result <investigation-result.json>
```

A future live runner must still add a provider adapter and a separate approval
gate; this envelope is deliberately not that.

## Tests added

| File | Coverage |
|---|---|
| `tests/test_bdb5/test_real_review.py` | good R1/R2 packets, top-level manifest, host path, approval promotion, R2 source leak, CLI failure |
| `tests/test_bdb5/test_real_runner.py` | responder sees only model-visible keys, R2 abstention, tampered payload refusal, CLI result |

Current BDB-5 result:

```text
44 passed
```

## Boundary checks

- The R1/R2 model-visible packets contain no manifest, `allowed_files`,
  `root_cause`, `gold_patch`, `fix_commit`, readiness or host paths.
- The runner's responder cannot see `evaluator_only`.
- The reviewer and runner do not mutate the prepared payload.
- Both cases remain `PREPARED`; neither becomes runnable or approved.
- No provider, model, M4B.3 ledger, repair pipeline or benchmark scorer was used.

## Remaining work

1. Actual independent human review of the R1/R2/R3 labels and packet boundary;
   the approval mechanism exists but no real reviewer has signed off.
2. A real-case model result under the gated provider; one exploratory R2 call
   is in Document 77, but no approved benchmark result exists.
3. T1's frozen `N_max`, complete candidate inventory, telemetry adapter and
   physical isolation boundary.
4. P1's isolated external-repository repair adapter; the trusted-fixture gate
   remains unchanged and P1 remains blocked.
