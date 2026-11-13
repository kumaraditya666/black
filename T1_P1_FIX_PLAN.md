# T1/P1 Fix Plan

**Status:** `T1_ISOLATED_STRICT_PASS — P1_V2_STRICT_PASS — PILOT_AGGREGATE_5_OF_5`

This document explains how the missing T1 and P1 infrastructure is being built.
T1 now has an adapter, frozen `N_max`, a prepared packet, a passing read-only
review, two independent packet approvals, a verified inventory, a bounded real
case run, and a strict-pass score. The run used a 26,985-character label-free
projection of the 1.8 MB packet, including a data-derived shortlist and
upstream-vs-edge guidance and a matching read-only container replay. P1 has
a separate preparation and scope adapter, a prepared packet, two independent
packet approvals, a verified isolated execution environment, a real
docstring-preserving candidate, and a fresh v2 label-vault approval. P1’s v2
score is a strict pass.

## Why these are different from R1/R2/R3

R1/R2/R3 already have:

- a prepared model-visible packet;
- a frozen manifest and label vault;
- a passing packet review;
- a provider contract;
- an approval path;
- a scorer.

T1 and P1 now have prepared packets and separate approval records. Their
remaining gaps are execution/isolation preflights, not packet approval.

## T1 — telemetry case

### Completed and residual limits

- The inventory is independently verified against the pinned Sock Shop commit
  `246380292ea8dcfa9bc87b570f9d9e5043502ddc`: 14 deployment manifests plus the
  telemetry-observed `rabbitmq-exporter`; all 15 services are covered by the 80
  metric columns. Status: `VERIFIED_AGAINST_PINNED_MANIFESTS_AND_METRICS`.
- The approved packet remains 1,858,054 bytes. The actual full model-visible
  prompt is **1,615,146 tokens**; the 1M-context provider rejected it. The local
  32,768-token path used a bounded projection; the full-packet provider path is
  separate and does not change the packet.
- The model server is isolated in its own `ollama/ollama` container with a
  read-only model-cache mount and no workspace or label mount. A separate
  read-only prompt client container produced the current result.
- T1 has a real case score: `data/bdb5_scores/BDB5-T1-isolated-score.json`,
  `strict_pass=True`, no failures, all required dimensions 1.0. The earlier
  host-run score remains for audit.
- The full-packet runner is `blackbox/bdb5/full_packet.py`, driven by
  `scripts/bdb5_run_full_packet.py`. The approved-packet preflight is
  `data/bdb5_t1/full_packet_attempt.json`: the live attempt was rejected with
  HTTP 400 at **1,615,146 tokens** against a 1,048,576-token context. The packet
  needs at least **1,621,290** input tokens with output reserve. The runner
  supports `--no-response-format` and `--reasoning-effort none` for free
  OpenRouter routes, but no 1M free route can hold this packet. The rerun is
  deferred until a 1.62M+ context model is affordable.
- The approved packet is still represented by a bounded projection in the
  current T1 score. The live full-packet attempt is recorded at 1,615,146
  tokens and rejected by the 1M context; the rerun is deferred, not pending
  credentials.

Completed on 2026-11-13:

- `N_max = 2,000` is frozen in `blackbox/bdb5/telemetry.py`.
- The telemetry parser/selector and preparation CLI exist.
- The packet exists at `data/bdb5_t1/bdb5_t1_prepared.json`.
- Read-only review returns `REVIEW_PASSED` with no issues.
- A separate T1 label vault exists at
  `fixtures/bdb5/labels/t1_label_vault.json`.
- Two independent reviewers approved the T1 packet with the T1 vault.
  Approval hash: `9df50d7d187c934f4b9c03c5aaa0ed1208a2740932ce017b785fc845b4db8b02`.
- The current T1 status is recorded at `data/bdb5_t1/T1_BLOCKED_STATUS.json`:
  approval valid, review passed, six provider calls across attempts and
  isolation replays, strict-pass score. The packet is 1,858,054 bytes (about
  1,615,146 provider-counted tokens), above every 1M provider limit, so the
  current score records a bounded-projection run.
- Inventory verification is recorded in `fixtures/bdb5/t1/service_inventory.json`
  and repeated in the prepared evaluator-only telemetry metadata.
- The score is `data/bdb5_scores/BDB5-T1-isolated-score.json`; the isolation
  evidence is `data/bdb5_t1/t1_isolation_proof.json`.

### Decisions that must be frozen first

1. **Freeze `N_max`.** Use a versioned constant before any label-aware work.
   The current recommendation is `2,000` rows for the deterministic log
   excerpt. It is a log-row cap, not a cap on metrics: all 1,441 metric
   timesteps and their 80 columns remain in the packet. Once frozen, `N_max`
   cannot be tuned after seeing the model output.
2. **Choose the authoritative inventory source.** The pinned Sock Shop
   deployment manifests at commit `246380292ea8dcfa9bc87b570f9d9e5043502ddc`
   provide the 14 manifest services; `rabbitmq-exporter` is present only in the
   observed metrics and is recorded explicitly. Do not silently substitute the
   15 observed identifiers for the manifest set.
3. **Choose the physical boundary.** The model server runs in its own
   `ollama/ollama` container with a read-only model-cache mount and no workspace
   or label access. The prompt client is a separate read-only container. The
   remaining boundary issue is packet context, not the model-server process.

### Implementation

Create a new telemetry adapter, for example:

`blackbox/bdb5/telemetry.py`

Responsibilities:

- read and validate the pinned `logs.parquet`, `metrics.parquet`, and
  `inject_time.txt`;
- verify the Parquet schema, timestamp column, Unix-seconds unit, row count and
  file hashes;
- select the inclusive window from the pinned timestamps;
- use the original zero-based Parquet row ordinal as the tie-breaker because
  no stable row ID exists;
- apply the frozen `N_max` evenly across the sorted log rows;
- include the complete 1,441-row metrics table, with explicit null handling;
- assign stable evidence IDs to the selected log rows and metric timesteps;
- build an `EvidencePacket` with telemetry evidence, the unranked candidate
  inventory, and no source revision or invented stack frame;
- never read `root_cause.txt` or label fields.

Implementation now present:

- `blackbox/bdb5/telemetry.py`;
- `scripts/bdb5_prepare_t1.py`;
- `tests/test_bdb5/test_telemetry.py`;
- `fixtures/bdb5/t1/service_inventory.json`;
- `fixtures/bdb5/labels/t1_label_vault.json`.

### T1 acceptance before a model call

- [x] `N_max` is frozen in code/manifest.
- [x] Parquet hashes and schema match the preflight.
- [x] Window selection is deterministic and label-free.
- [x] Packet review is `REVIEW_PASSED`.
- [x] Inventory source is independently confirmed complete for the case.
- [x] The container prompt/staging boundary cannot read the repository or label vault.
- [x] The model server is isolated from the workspace and label vault.
- [x] Two real reviewers approve the packet with the T1 vault.
- [x] No test/execution claim is invented.
- [x] T1 is packet-approved, run, and scored from the isolated server; the score
  is a bounded-projection real case score, not a full-packet claim.
- [x] The full-packet runner and approved-packet preflight are implemented.
- [ ] T1 uses the complete 1.8 MB packet in a live provider run rather than a
  bounded projection.

## P1 — external-repository repair

### What is missing

- The current repair gate only accepts the trusted local fixture repository.
- The separate external-repair adapter exists and its isolated environment
  preflight has passed.
- A candidate patch, six model calls, and a P1 score now exist. The final
  candidate preserves the Printable docstring, passes the hidden test and the
  full test file.
- The 21-name v2 vault has fresh approvals from `atharv` and `adi`:
  `data/bdb5_p1/approvals/BDB5-P1-v2-approval.json`,
  hash `6f48124c44a61dbb30a2d05ec15f9289c3aabef6d608d4f19447f803bbbcf516`.
- P1 v2 score: `data/bdb5_scores/BDB5-P1-v2-score.json`; `strict_pass=True`,
  no failures, all seven required dimensions 1.0.
- The original strict-fail score remains at
  `data/bdb5_scores/BDB5-P1-score.json` for audit.
- The evaluator-only metadata now records the verified `bin/test` command,
  the pinned image digest, and `execution_verified=true`. The model-visible
  packet and manifest are unchanged, so the existing approvals still validate.

`blackbox/repair/eligibility.py` must remain unchanged. P1 gets a separate
evaluation path; do not relax the trusted-fixture gate.

Implementation now present:

- `blackbox/bdb5/external_repair.py`;
- `scripts/bdb5_prepare_p1.py`;
- `tests/test_bdb5/test_external_repair.py`;
- `fixtures/bdb5/labels/p1_label_vault.json`;
- `data/bdb5_p1/bdb5_p1_prepared.json` (read-only review passed).

P1 packet hash: `d9f853a08251570c3f93f3e413cd710095c0090208e81d557d573680bcfe92ea`.
P1 approval hash: `f870fc6a1851d3f59868fa2b4b17f74a7ba9a8ecf163a77d3600c93124ed774d`.
Two independent reviewers approved the P1 packet with the P1 vault.

P1 environment preflight:

- image pulled by digest `sha256:bcdff110a35d19a6838fde5f678d1b5103610234bd034e5703df46878aad3b63`;
- clean base + hidden test fails at `test_immutable`;
- gold patch + hidden test passes;
- full `test_basic.py` passes 23 tests;
- result at `data/bdb5_p1/preflight_result.json`;
- gold patch is an environment check only, not a model result or score.

### Implementation

Create a new adapter, for example:

`blackbox/bdb5/external_repair.py`

Responsibilities:

- pin the base commit and allowed-file scope;
- clone or materialize a clean external repository at the base commit;
- verify the repository identity and commit;
- keep hidden tests and the test patch outside the candidate workspace;
- apply the candidate patch only to a disposable copy;
- apply the evaluator test patch only in the evaluator copy;
- run the hidden FAIL_TO_PASS test and the PASS_TO_PASS suite in an isolated
  container/image;
- reject test-file edits and out-of-scope files;
- record reproduction-before, reproduction-after, patch scope, regression
  result, image digest, timings and failures;
- never use the gold patch to judge the candidate patch;
- never expose hidden tests or the label vault to the model.

Add:

- `scripts/bdb5_prepare_p1.py`;
- P1 label-vault entry containing hidden tests and expected patch scope;
- tests for scope rejection, test-edit rejection, hidden-test isolation,
  network denial, repeatability, and fail-to-pass/pass-to-pass parsing.

### P1 acceptance before a model call

- [x] A pinned SWE-bench-compatible image is available by digest.
- [x] The external repository is cloned at the exact base commit.
- [x] Hidden tests are outside the candidate workspace by construction.
- [x] The candidate workspace is separate from the evaluator workspace.
- [x] Patch scope is limited to the approved file.
- [x] Reproduction-before fails with the recorded signature.
- [x] A clean base plus the evaluator test patch fails as expected.
- [x] The trusted fixture gate is untouched.
- [x] Packet review is `REVIEW_PASSED`.
- [x] Two real reviewers approve the packet.
- [x] A candidate patch is generated and scored. The docstring-preserving v2
  score is `data/bdb5_scores/BDB5-P1-v2-score.json`; `strict_pass=True` with
  all seven required dimensions at 1.0.

## Order of work

1. Freeze T1 `N_max`, inventory source, and isolation design.
2. Implement the T1 telemetry adapter and prepare/review the T1 packet.
3. Implement the P1 external-repair adapter and prepare/review the P1 packet.
4. Run both external preflights with pinned hashes/images. P1 is done; T1 is not.
5. Get two real reviewers for each prepared packet. Both are done.
6. P1 candidate generation, v2 label approval, scoring and evaluator metadata
   correction are done. T1 inventory, isolated run and score are done. The
   full-packet rerun requires a provider with at least 1,621,290 input tokens;
   it is deferred until one is affordable and is not a project blocker.
7. Completion matrix and pilot aggregate are updated. Do not describe the
   single-entrant pilot aggregate as an external leaderboard.

## What I can implement without inventing anything

- The T1 telemetry parser, selector, packet builder, tests, and preparation
  script — after the three decisions above are fixed.
- The P1 external-repair adapter, tests, preparation script, and isolated
  environment preflight are present. The remaining work is candidate generation
  and scoring.
- Review packets, approval records, scoring and documentation.

## What I cannot honestly do

- Pretend the 15 observed T1 services are a complete inventory; the manifest
  set and the telemetry-only exporter are recorded separately.
- Claim the T1 run consumed the full 1.8 MB packet; it used a bounded projection.
- Describe the single-entrant pilot aggregate as an external leaderboard.
- Run P1 through the trusted-fixture gate.
- Invent P1 hidden tests, image availability, or patch results.
- Create human approval.

T1 and P1 packets are approved. P1’s environment preflight has passed, its
candidate has run, and its v2 score is a strict pass under the fresh two-reviewer
approval. T1 has a verified inventory, a bounded-projection strict-pass score
from an isolated model server, and a separate prompt client. Full-packet T1
context remains unproven. R1/R2/R3 are separate and scored.
