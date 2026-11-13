# BDB-5 Completion Matrix

**Date:** 2026-11-13

**Status:** `R1_R2_R3_V2_STRICT_PASS — T1_ISOLATED_STRICT_PASS — P1_V2_STRICT_PASS — FULL_SUITE_GREEN — PILOT_AGGREGATE_5_OF_5`

This matrix is the current truth. It distinguishes implemented machinery,
reproduced evidence, external approvals and model results.

## Case matrix

| Item | State | Evidence |
|---|---|---|
| R1 exact Python 3.5.0 | **Reproduced** | 247 tests, 2 failures, 3 errors |
| R1 BugSwarm image | **Reproduced with Python 3.4.2 mismatch** | Document 70 |
| R1 Python 3.5.10 | **Reproduced** | Document 70 |
| R2 pinned image | **Reproduced with Python 3.2.5** | 38 tests, 1 error; Document 72 |
| R1/R2 packet review | **Passed** | `REVIEW_PASSED`, no issues |
| R3 issue/source preparation | **Prepared** | Django base `879cc3...` |
| R3 review | **Passed** | `REVIEW_PASSED` |
| Provider adapter | **Implemented, repository gate closed** | `LIVE_INFERENCE_ENABLED=False`; no repository network call |
| Evaluator label vault | **Implemented** | Truth separated from model-visible packets |
| Independent approval record | **Implemented and populated** | Two reviewer IDs for R1/R2/R3/T1/P1 |
| Real-case scorer | **Implemented and exercised** | `score_approved_case` |
| Original R1 score | **Strict fail retained** | `data/bdb5_scores/BDB5-R1-score.json` |
| Original R2 score | **Strict fail retained** | `data/bdb5_scores/BDB5-R2-score.json` |
| Original R3 score | **Strict fail retained** | `data/bdb5_scores/BDB5-R3-score.json` |
| R1 fresh v2 score | **Strict pass** | `data/bdb5_scores/BDB5-R1-v2-score.json` |
| R2 fresh v2 score | **Strict pass** | `data/bdb5_scores/BDB5-R2-v2-score.json` |
| R3 fresh v2 score | **Strict pass** | `data/bdb5_scores/BDB5-R3-v2-score.json` |
| T1 telemetry adapter | **Implemented** | Frozen `N_max=2,000`; 1,441 metric timesteps |
| T1 candidate inventory | **Verified** | Pinned Sock Shop commit `246380...`; 14 manifests plus `rabbitmq-exporter` |
| T1 packet | **Prepared and approved** | `data/bdb5_t1/bdb5_t1_prepared.json`; approval `9df50d...` |
| T1 model run | **Completed, bounded projection** | 6 provider calls across attempts and isolation replays; 26,985-character projection |
| T1 score | **Strict pass** | `data/bdb5_scores/BDB5-T1-isolated-score.json` |
| T1 model-server isolation | **Verified** | `ollama/ollama` container; read-only model-cache mount; no workspace or label mount |
| T1 prompt boundary | **Verified** | Separate read-only Python client container |
| T1 full-packet context | **Deferred; 1M attempt rejected** | `data/bdb5_t1/full_packet_attempt.json`; **1,615,146 tokens** vs 1,048,576; rerun deferred until a >=1,621,290-context model is affordable |
| P1 external-repair adapter | **Implemented** | `blackbox/bdb5/external_repair.py` |
| P1 environment preflight | **Passed** | Pinned image digest; hidden test and full file behavior verified |
| P1 candidate | **Generated and evaluated** | `data/bdb5_p1/candidate/` |
| P1 original score | **Strict fail retained** | Empty original `pass_to_pass` |
| P1 v2 score | **Strict pass** | `data/bdb5_scores/BDB5-P1-v2-score.json` |
| Full repository suite | **Green** | 324 passed, 10 skipped in 247.53s |
| Pilot aggregate | **5/5 strict passes** | `data/bdb5_scores/BDB5-pilot-aggregate.json`; not an external leaderboard |

## What “implemented” means

- The code paths exist and have tests.
- The R1/R2/R3 preparation, approval and scoring paths have been exercised.
- T1 preparation, approval, bounded run, scoring and container replay have been
  exercised.
- P1 preparation, approval, preflight, candidate generation, scoring and
  evaluator metadata correction have been exercised.
- The pilot aggregate is a fixed-case strict-pass count; it is not an aggregate
  accuracy score, blind benchmark or external leaderboard.

## T1 residual limits

T1 is scored from an isolated model server, but two context limits remain:

1. The 1.8 MB packet exceeds the 32,768-token provider limit. The run used a
   bounded projection; it was not a full-packet run.
2. The projection included a data-derived shortlist and upstream-vs-edge
   guidance. The score is a real case score, not an unaided full-context result.
3. A full-evidence service-partitioned neutral attempt was executed as a
   diagnostic and did not pass; it is not used as the T1 score.

## P1 status

P1 is complete for the pilot:

- external repository pinned;
- hidden tests outside the candidate workspace;
- patch scope restricted to `sympy/core/_print_helpers.py`;
- preflight passed;
- candidate preserves the Printable docstring and passes the hidden test and
  full `test_basic.py`;
- fresh two-reviewer v2 approval;
- v2 score is a strict pass under that approval.

`blackbox/repair/eligibility.py` remains unchanged.

## Non-claims

- No BDB-5 aggregate accuracy or external leaderboard.
- No claim that the original R1/R2/R3 strict-fail scores were erased.
- No full-packet T1 run.
- The pilot aggregate is a single-entrant, retrospective summary, not a blind
  comparison.
- No claim that the P1 gold-patch environment check is a model result.
- No exploratory output is a benchmark score.
