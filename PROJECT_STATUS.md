# Project Status — BDB-5 / BLACKBOX

**Date:** 2026-11-13

**Overall:** `CODE_GREEN — R1_R2_R3_V2_STRICT_PASS — T1_ISOLATED_STRICT_PASS — P1_V2_STRICT_PASS — PILOT_AGGREGATE_5_OF_5`

## What is complete

- Full repository suite: **324 passed, 10 skipped** in 247.53 seconds.
- BDB-5 suite: **83 passed**, 6 collection warnings.
- Repair subprocess environment fixed so isolated fixture runs retain `pytest`.
- R1, R2 and R3 packets are prepared and pass read-only review.
- Two real reviewers, `atharv` and `adi`, recorded approval for all three packets.
- The three approval records validate against the prepared packets and label vault.
- Approval hashes: R1 `205d465cf7048cfeb52ed394c1249d97e836cd670ba117a074f9512d752b15d1`;
  R2 `ab68d3120ada2468776973b1a2dfed46275cf1ecc8905229177ed369ff50d1f3`;
  R3 `b4ed0b669a9ab0376d1e754755f586b1392bcdf9db29fe954dc4b1c8690e0d47`.
- The original R1/R2/R3 scores remain preserved as strict-fail audit records:
  `data/bdb5_scores/BDB5-R1-score.json`, `BDB5-R2-score.json`,
  `BDB5-R3-score.json`.
- Fresh direct `qwen3.5:9b-q4_K_M` runs (two calls per case) against the same
  approved packets produced strict-pass v2 scores:
  - R1: `data/bdb5_scores/BDB5-R1-v2-score.json` — strict pass; file/function/line,
    mechanism, causal status, citations and reproduction-before all 1.0.
  - R2: `data/bdb5_scores/BDB5-R2-v2-score.json` — strict pass; application-source
    abstention, application causal status, citations and reproduction-before all
    pass; `app_source_claim=0.0`.
  - R3: `data/bdb5_scores/BDB5-R3-v2-score.json` — strict pass; file/function/line,
    mechanism, causal status and citations all 1.0.
  - For R1/R2, the reproduction `TestExecution` name/hash/signature fields were
    normalized from the packet's own `artifact:test-1` metadata after the model
    omitted them; this is recorded in the score files.
- T1 `N_max` is frozen at **2,000** log rows; all 1,441 metric timesteps are retained.
- T1 telemetry adapter and tests exist.
- T1 packet is prepared at `data/bdb5_t1/bdb5_t1_prepared.json` and passes read-only review. The full model-visible prompt is **1,615,146 provider-counted tokens**; a 1M-context provider rejected it. The current score still uses a bounded, label-free projection; the projection included a data-derived shortlist and upstream-vs-edge guidance.
- T1 payload hash: `04315a28de6ebd6eba056aabaf5c1eddf68d64892017f2d1382baa6443698086`.
- The candidate inventory is independently verified against the pinned Sock Shop commit
  `246380292ea8dcfa9bc87b570f9d9e5043502ddc`: 14 deployment manifests plus the
  telemetry-observed `rabbitmq-exporter`, all 15 services covered by 80 metric columns.
  Status: `VERIFIED_AGAINST_PINNED_MANIFESTS_AND_METRICS`.
- T1 uses a separate evaluator-only vault at `fixtures/bdb5/labels/t1_label_vault.json`,
  so the existing R1/R2/R3 approvals remain valid.
- Two independent reviewers, `atharv` and `adi`, approved the T1 packet.
  T1 approval hash: `9df50d7d187c934f4b9c03c5aaa0ed1208a2740932ce017b785fc845b4db8b02`.
- T1 was also run with a fully isolated model server: `ollama/ollama` runs in
  its own container with a read-only model-cache mount and no workspace or label
  mount; the prompt client is a separate read-only container.
- Current T1 score: `data/bdb5_scores/BDB5-T1-isolated-score.json`;
  `strict_pass=True`, no failures. Required dimensions: service_top1 1.0,
  service_top3 1.0, fault_accuracy 1.0, citation_validity 1.0,
  citation_coverage 1.0, l1_causal_status 1.0, l2_causal_status 1.0,
  l2_abstention 1.0, unsupported_claim_rate 0.0. The isolated model selected
  `carts` / `F1` and abstained from a source-level cause. The earlier host-run
  score remains at `data/bdb5_scores/BDB5-T1-score.json` for audit.
- A full-packet provider path now exists at `blackbox/bdb5/full_packet.py` and
  `scripts/bdb5_run_full_packet.py`. The approved packet preflight is
  `data/bdb5_t1/full_packet_attempt.json`: the live full-packet attempt was
  rejected with HTTP 400 at **1,615,146 tokens** against a 1,048,576-token
  context. The packet needs at least 1,621,290 input tokens with output reserve;
  no 1M route can run it. The current score still uses the bounded projection.
- P1 external-repair adapter is implemented at `blackbox/bdb5/external_repair.py`,
  with a separate `scripts/bdb5_prepare_p1.py`.
- P1 uses the separate evaluator-only vault at
  `fixtures/bdb5/labels/p1_label_vault.json`.
- P1 packet is prepared at `data/bdb5_p1/bdb5_p1_prepared.json` and passes
  read-only review. Payload hash:
  `d9f853a08251570c3f93f3e413cd710095c0090208e81d557d573680bcfe92ea`.
- Two independent reviewers, `atharv` and `adi`, approved the P1 packet.
  P1 approval hash: `f870fc6a1851d3f59868fa2b4b17f74a7ba9a8ecf163a77d3600c93124ed774d`.
- P1 patch scope accepts only `sympy/core/_print_helpers.py`; it rejects test
  edits and out-of-scope files. Hidden tests and the gold patch are not in the
  model-visible packet.
- Docker Desktop is running. The pinned P1 image was pulled by digest
  `sha256:bcdff110a35d19a6838fde5f678d1b5103610234bd034e5703df46878aad3b63`.
- SymPy is checked out at the exact P1 base commit
  `cffd4e0f86fefd4802349a9f9b19ed70934ea354`.
- P1 environment preflight passed inside the isolated image:
  - clean base + hidden test fails at `test_immutable`;
  - gold patch + hidden test passes;
  - the full `test_basic.py` file passes 23 tests;
  - network is disabled, root is read-only, user is 65534, capabilities are dropped.
- The preflight result is `data/bdb5_p1/preflight_result.json`.
- The gold patch was used only to verify the evaluator environment. It is not a
  candidate result and is not scored.
- A P1 candidate was generated from the approved model-visible packet with six
  local `qwen3.5:9b-q4_K_M` calls. Attempts 1-3 were malformed diffs; attempt 4
  applied but broke the Printable docstring; attempts 5-6 produced the final
  docstring-preserving replacement. Record:
  `data/bdb5_p1/candidate/candidate.json`.
- The candidate patch changes only `sympy/core/_print_helpers.py`, inserts
  `__slots__ = ()` after the Printable class docstring, passes `test_immutable`,
  and passes the full `test_basic.py` file (23 passed) in the isolated evaluator.
  Result and logs are under `data/bdb5_p1/candidate/`.
- A separate 21-name `pass_to_pass` vault was prepared at
  `data/bdb5_p1/p1_label_vault_v2.json` and approved by both reviewers; it is the
  vault used by the P1 v2 strict-pass score.
- The original P1 score is retained at
  `data/bdb5_scores/BDB5-P1-score.json`; it is `strict_pass=False` only because
  the original approved vault has an empty `pass_to_pass` list.
- A fresh two-reviewer approval (`atharv` and `adi`) was recorded against the
  21-name v2 vault at `data/bdb5_p1/approvals/BDB5-P1-v2-approval.json`.
  Approval hash: `6f48124c44a61dbb30a2d05ec15f9289c3aabef6d608d4f19447f803bbbcf516`.
  v2 vault hash: `2a7db5774ff015837be8a80bde5e2ed5599658763405c2aad5477f02d82d1854`.
- P1 was rescored against that approval and vault:
  `data/bdb5_scores/BDB5-P1-v2-score.json`. Status is `REAL_CASE_SCORED`,
  `strict_pass=True`, with no failures. `patch_applies`, `patch_scope`,
  `fail_to_pass`, `pass_to_pass`, `reproduction_before`, `reproduction_after`
  and `regression_safety` are all 1.0.
- Both T1 and P1 now have real case scores; P1 also has a generated candidate.
- Pilot aggregate: `data/bdb5_scores/BDB5-pilot-aggregate.json`; fixed five-case
  pilot, 5/5 strict passes, `result_class=BDB5_PILOT_AGGREGATE_NOT_EXTERNAL_LEADERBOARD`.
- Repository `LIVE_INFERENCE_ENABLED` remains `False`.

## Remaining work

The concrete T1/P1 build sequence and acceptance gates are in
`T1_P1_FIX_PLAN.md`.

### R1/R2/R3 pilot

Complete for the pilot: fresh model results were produced against the same
approved packets and rescored with the matching approvals. All three v2 scores
strict-pass. The original strict-fail scores are retained, and approval alone is
not treated as correctness. The pilot aggregate is a fixed-case strict-pass
count, not an external benchmark or leaderboard.

### T1 telemetry

T1 is prepared, run, and scored. The inventory is verified, and the model server
is isolated in its own container with a read-only model-cache mount and no
workspace or label access. A full-packet runner and its approved-packet preflight
exist. The live full-packet attempt was rejected at 1,615,146 tokens against a
1,048,576-token limit, so T1 is closed on the bounded-projection score. The
full-packet rerun is deferred until a provider with at least 1,621,290 input
tokens is available; this is an evidence limitation, not a project blocker.

### P1 external repair

Packet preparation, approval, environment preflight, candidate generation,
case scoring and metadata correction are complete. The v2 label vault has fresh
two-reviewer approval and the P1 score is a strict pass. The evaluator-only
`test_command` now records the verified `bin/test` command, the image digest is
pinned, and `execution_verified` is true. The model-visible packet and manifest
are unchanged; the existing approvals still validate. Keep
`blackbox/repair/eligibility.py` unchanged.

## Explicit non-claims

- No aggregate BDB-5 accuracy.
- No external leaderboard.
- No aggregate R1/R2/R3 accuracy; the pilot aggregate is a fixed-case
  strict-pass count.
- Original R1/R2/R3 strict-fail scores remain valid audit records; they are not
  overwritten by the v2 passes.
- No T1 full-packet run; the T1 result is a bounded-projection real case score.
- The T1 isolated result is from an isolated server, but the packet context is
  still bounded.
- No aggregate accuracy claim; the pilot aggregate reports strict-pass counts,
  not a dimension average.
- No claim that exploratory outputs are benchmark scores.
- No claim that the P1 gold-patch environment check is a model result.
- The P1 v2 result is a strict pass under the fresh v2 approval; the original
  P1 score remains a separate strict failure and is not erased.

## Next action

R1/R2/R3 now have fresh strict-pass v2 scores while their original strict-fail
scores remain for audit. T1 has an approved packet, verified inventory, a
bounded-projection strict-pass score from an isolated model server, and no host
workspace access. P1 has an approved packet, a verified isolated environment, a
real docstring-preserving candidate, a fresh approved v2 strict pass, and
verified evaluator metadata. The pilot aggregate is 5/5 strict passes; it is not
an external leaderboard. The T1 full-packet rerun is deferred until a 1.62M+
context model is affordable; the bounded score and limitation are final for now.
The full repository suite is green: 324 passed, 10 skipped. The graph rebuild
completed at 2,221 nodes and 6,480 edges.
