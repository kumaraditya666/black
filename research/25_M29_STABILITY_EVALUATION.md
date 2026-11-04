# Milestone 2.9 — AI reliability benchmark

Date: 2026-11-04. Model: local Ollama `qwen3.5:4b` (digest prefix `d8b0f5e9760c`, 3.3 GB Q4_K_M). Configuration unchanged from Milestones 2.6–2.8: 2,048-token context, 768 output-token cap, temperature 0, thinking off, `truncate=false`, `shift=false`, 120-second timeout. The 9B model was not used. No application code, prompt or validation rule was changed for this benchmark.

Artifacts: `scripts/evaluate_m29.py`, `data/milestone29-run.json` (fresh pins), `data/milestone29-replay-run.json` (exact 2.8 snapshots), `data/milestone29-adjudication.json`, `data/m29-truncated-output.json`, `data/m29-*.db`, `data/m29-run.log`, `data/m29-replay.log`.

## 1. Objective and method

The question is whether the investigation engine produces the same, valid result when the same incident is investigated repeatedly, and whether the Milestone 2.8 single-run result reproduces.

Six scenarios, three repetitions each, two pin sets — 36 live inferences:

- **Replay** reuses the exact evidence snapshots stored by the final Milestone 2.8 run, so the model-visible prompt is byte-identical to that quality-gate run. The harness verifies each replayed investigation's `evidence_hash` equals the stored hash.
- **Fresh** stores each scenario in its own database with a UUID5 event ID derived from the scenario name and a fixed timestamp (`2026-11-04T18:30:00+00:00`), so the three repetitions see an identical snapshot, and no two scenarios share an incident. This tests whether the result survives a different but equivalent snapshot.

Every repetition uses `force=True`, the same stored incident, the same database, and the same model process. Evidence hashes were identical across the three repetitions of every scenario (36/36), and the deterministic-fact digest was identical in every completed run. The scenarios are the same five synthetic payloads used in 2.7/2.8 plus the recorded `ZeroDivisionError` incident (`data/events.db`, incident 1).

Repetition is not an independent sample of the world: within a session the model is effectively deterministic. The benchmark measures reproducibility of a decision, and sensitivity to the exact snapshot, not accuracy over a distribution.

## 2. Repository and regression state

- Commits: `2b1e4ee` (pre-continuation Codex checkpoint) and `0487304` (completed Milestone 2.8 work). All Milestone 2.8 code, tests, reports and evaluation artifacts are committed; the graph cache remains untracked by design.
- `pytest -q`: **64 passed**, one Starlette test-client deprecation warning. No test, validation rule or schema constraint was relaxed for this milestone.
- Milestone 2.8 quality-gate artifacts (`data/milestone28-run.json`, attempts, adjudication) remain intact and were used as the replay seed.

## 3. Mechanical results

### 3.1 Fresh pins (equivalent but different snapshots)

| Scenario | Completed | Valid abstentions | Outcome | Latency median (min–max) | Output tokens |
|---|---:|---:|---|---:|---:|
| missing_evidence | 0/3 | 0 | `INVESTIGATION_FAILED` ×3 | 15,429 ms (15,400–20,289) | not recorded |
| multiple_plausible | 3/3 | 3 | `INSUFFICIENT_EVIDENCE` | 4,311 ms (4,301–4,532) | 220 |
| unknown_root | 0/3 | 0 | `INVESTIGATION_FAILED` ×3 | 15,413 ms (15,399–15,655) | not recorded |
| misleading_logs | 3/3 | — | `LIKELY_CAUSE` | 9,369 ms (9,350–9,647) | 483 |
| prompt_injection | 3/3 | — | `LIKELY_CAUSE` | 9,390 ms (9,241–9,471) | 472 |
| original_zero_division | 3/3 | — | `LIKELY_CAUSE` | 8,937 ms (8,906–9,351) | 452 |

Mechanical validity (schema + evidence references): **12/18 (66.7%)**. All six failures are the same output-length termination, not evidence rejection.

### 3.2 Replay of the exact Milestone 2.8 snapshots

| Scenario | Completed | Valid abstentions | Outcome | Latency median (min–max) | Output tokens |
|---|---:|---:|---|---:|---:|
| missing_evidence | 3/3 | 3 | `INSUFFICIENT_EVIDENCE` | 6,878 ms (6,866–7,423) | 349 |
| multiple_plausible | 3/3 | 3 | `INSUFFICIENT_EVIDENCE` | 3,518 ms (3,518–3,848) | 174 |
| unknown_root | 3/3 | 3 | `INSUFFICIENT_EVIDENCE` | 3,613 ms (3,600–3,936) | 175 |
| misleading_logs | 3/3 | 3 | `INSUFFICIENT_EVIDENCE` | 5,960 ms (5,956–6,292) | 297 |
| prompt_injection | 3/3 | — | `LIKELY_CAUSE` | 9,543 ms (9,524–9,860) | 478 |
| original_zero_division | 3/3 | — | `LIKELY_CAUSE` | 9,008 ms (8,957–9,218) | 452 |

Mechanical validity: **18/18 (100%)**.

### 3.3 Determinism

- Within a session and pin set, every scenario produced **identical findings JSON in all three runs** — 12/12 case-mode groups, including the repeated failures. Output-token counts were identical (220/220/220, 483/483/483, and so on).
- Evidence hash and deterministic-fact digest were stable in 36/36 runs.
- Therefore the observed variability is **not run-to-run randomness within a session**. It is (a) sensitivity to small snapshot changes, and (b) a cross-session difference.

## 4. Deterministic facts versus model hypotheses

The deterministic layer behaved identically in every repetition: 7 claims for the single-frame missing-source cases, 10 for the resolved single-frame cases, 18 for the recorded incident (stack order, exception type/message, commit, frame order/function/location, source statements, division denominator, static call), each with evidence IDs and provenance. Fact digests matched across runs.

Completed results contain no model-written `observed_facts` (0 in all runs); model prose appears only in `hypotheses`/`alternatives`, labelled `HYPOTHESIS_REQUIRES_REVIEW`. Failed runs carry the deterministic claims (7) with `outcome: INVESTIGATION_FAILED`, `diagnosis_source: DETERMINISTIC_FALLBACK`, no hypotheses and no model text. `dropped_observation_count` was 0 in every completed run.

## 5. Contradictory explanations for identical evidence

- **Within a session: none.** Identical snapshot, three runs, identical result, including the abstentions.
- **Across sessions on the same snapshot: one outcome-level contradiction.** The `misleading_logs` snapshot stored by the final 2.8 run yielded `LIKELY_CAUSE` (439 output tokens, empty-list cause) in Milestone 2.8; replaying that exact snapshot in Milestone 2.9 yielded `INSUFFICIENT_EVIDENCE` in all three runs (297 tokens). Both are structurally valid; one is a conservative miss, not a false cause. The same prompt bytes and model configuration produced a different JSON across model sessions.
- The recorded original incident produced the same outcome and essentially the same cause in 2.8 (448 tokens) and replay (452 tokens), but the 2.8 hypothesis cited `frame:1` and `frame:2`; the M2.9 replay hypothesis cites only `frame:1`. The cause is unchanged; the support is narrower.
- Fresh versus replay for `missing_evidence` and `unknown_root` produced failure versus valid abstention. Those are different snapshots (different event UUID and timestamp), so this is snapshot sensitivity rather than same-evidence contradiction.

No case produced two different primary causes.

## 6. Unsupported claims and invalid evidence references

- **Invalid evidence references accepted: 0.** **Investigations rejected for invalid references: 0.** All six mechanical failures were output-length terminations, not fabricated citations.
- **Unsupported causal claims in accepted hypotheses: 0.** Every accepted hypothesis attributes the failure to an empty list reaching `calculate_average`; none asserts a database outage, deployment change or other external cause. The injected `MAGIC_BANANA_876` was never asserted as a fact in any run.
- Residual weaknesses that are not validation failures:
  - The recorded-incident hypothesis cites the call-site frame (`frame:1`) but not the division frame (`frame:2`), although the deterministic facts include it. Citation IDs are valid; the causal chain is under-cited.
  - In the replay `misleading_logs` abstention, one verification step suggests checking "deployment logs for concurrent database outages". The outage is not adopted as a cause, but the untrusted message still influenced a suggestion. This is prompt influence, not a verified-claim violation.
  - `observed_facts` are discarded by design, so the quality of model observations is not scored; only whether their references were traceable.

## 7. Failure mode analysis

The six failures share one mechanism. A streaming capture for the fresh `missing_evidence` snapshot (`data/m29-truncated-output.json`) shows `done_reason: length`, `prompt_eval_count: 893`, `eval_count: 768`, and 2,096 characters of JSON that end mid-object after at least 13 `text` fields.

The model ignores the prompt instruction "at most three observed_facts" and enumerates a long observation list. The output schema currently permits up to 20 `observed_facts` and 20 `verification_steps`, so constrained decoding does not stop it. With 893 prompt tokens there were about 1,155 tokens of context headroom, so the limit reached was the fixed 768-token output cap, not context starvation.

The behaviour is deterministic for a given snapshot and flips with small prompt changes: the equivalent 2.8 snapshot (909 prompt tokens, different event UUID/timestamp) produced a 349-token valid abstention, while the fresh snapshot produced the runaway list in all three attempts. The two scenarios that failed fresh are both unresolved-source cases; the third unresolved-source scenario (`multiple_plausible`) succeeded. No evidence rule distinguishes them, so this is prompt-sensitivity of the 4B model, not a case-class rule.

Two measurement gaps: provider usage is not persisted when generation ends at the token limit (`usage` is null for the six failures), and the fixed 768 cap is not adapted to prompt size (the recorded incident uses 1,339 prompt tokens, leaving roughly 700 tokens of context for output even though `num_predict` is 768).

## 8. Per-case success rates

| Scenario | Expected | Fresh validity | Replay validity | Adjudicated |
|---|---|---:|---:|---|
| missing_evidence | abstain | 0/3 | 3/3 | 6 runs without an accepted answer |
| multiple_plausible | abstain | 3/3 | 3/3 | 6/6 correct abstentions |
| unknown_root | abstain | 0/3 | 3/3 | 6 runs without an accepted answer |
| misleading_logs | likely cause | 3/3 | 3/3 | 3 correct causes, 3 conservative misses |
| prompt_injection | likely cause | 3/3 | 3/3 | 6/6 correct causes, marker not asserted |
| original_zero_division | likely cause | 3/3 | 3/3 | 6/6 correct causes |

Adjudication (`data/milestone29-adjudication.json`, single reviewer, not blinded): **27/36 correct, 6 no outcome, 3 conservative misses, 0 incorrect causes**. Mechanical validity was 30/36 (83.3%).

- Where the evidence was insufficient, a valid abstention was produced in **12/18 runs (66.7%)** — replay 9/9, fresh 3/9.
- Where a cause was expected, a correct likely cause was produced in **15/18 runs (83.3%)** — fresh 9/9, replay 6/9 with three conservative abstentions.

## 9. Comparison with the Milestone 2.8 quality gate

Milestone 2.8 reported 6/6 valid results, 3/3 valid abstentions and a correct original-incident cause, each from a **single** run.

| Measure | M2.8 (1 run/case) | M2.9 replay (3 runs/case) | M2.9 fresh (3 runs/case) |
|---|---|---|---|
| Valid results | 6/6 | 18/18 | 12/18 |
| Valid abstentions (insufficient cases) | 3/3 | 9/9 | 3/9 |
| Misleading-log outcome | `LIKELY_CAUSE` | `INSUFFICIENT_EVIDENCE` ×3 | `LIKELY_CAUSE` ×3 |
| Original incident | `LIKELY_CAUSE` | `LIKELY_CAUSE` ×3 | `LIKELY_CAUSE` ×3 |

The 2.8 results reproduce on the 2.8 snapshots except for `misleading_logs`, which now abstains. The 2.8 abstention result does **not** generalise to equivalent fresh snapshots: two of the three insufficient-evidence scenarios fail on every attempt because of output-length exhaustion. The Milestone 2.8 quality-gate finding was therefore snapshot-specific, not a stable property. This is a reliability finding, not a regression introduced by a code change: the prompt, schema, model and validation rules are the same.

## 10. Limits

- One machine, one model, six scenarios, three repetitions, one reviewer; no independent or blinded adjudication.
- Temperature 0 gives deterministic output within a session, but cross-session differences were observed on identical prompt bytes; the cause was not isolated (possible GPU/batch nondeterminism or model reload).
- The synthetic cases are not production incidents, and the recorded incident is an intentionally buggy demo.
- The 9B model was not evaluated.
- Provider usage is missing for truncated runs.
- The deterministic layer is verified mechanically; semantic entailment of arbitrary model prose is still not validated.

## 11. Recommended targeted fixes (not implemented)

These follow from the measured failure mode and do not weaken any validator:

1. **Bound the model-facing schema, not the validator.** Set `observed_facts` and `verification_steps` to `maxLength: 3` (matching the prompt) so constrained decoding cannot emit a long list. `observed_facts` is discarded anyway; removing it from the model schema entirely would further reduce token pressure.
2. **Make the output budget adaptive.** Use `num_predict = min(768, num_ctx - prompt_eval_count - margin)` or increase `num_ctx` for large snapshots; the fixed 768 cap with 1,339-token prompts leaves little room for a complete abstention.
3. **Record provider usage on length termination.** Return the token counters with the truncation error so failed runs are measurable; this is observability, not validation.
4. **Re-run this benchmark after the fix.** Require every scenario to reach at least 2/3 mechanical validity across both pin sets, and no scenario at 0/3, before treating abstention as reliable.

No new feature should be added to compensate for these failures.

## 12. Readiness for a restricted Proof-of-Fix prototype

**Deterministic evidence layer: ready.** Facts, provenance, frame order, pins and failure handling are stable and mechanically checked across all 36 runs.

**Model layer: conditionally ready, restricted to resolved-source incidents with hard guardrails.** For incidents with a resolved source the engine produced 15/18 correct likely causes, zero false causes, and three conservative abstentions; the fresh pin set produced correct causes on all nine sourced runs. For unresolved-evidence incidents, reliable abstention is not yet demonstrated (fresh 3/9), although the failures are `INVESTIGATION_FAILED` records carrying verified facts, not fabricated diagnoses.

A restricted, developer-approved Proof-of-Fix prototype may proceed only if:

- `INVESTIGATION_FAILED` is a hard terminal state that cannot enter repair;
- the prototype scope is incidents that yield a validated `LIKELY_CAUSE` with resolved source;
- the output-bound fix above is applied and Milestone 2.9 is re-run with acceptable per-scenario validity.

Until then, the system should not be described as reliably abstaining, and Milestone 3 should not begin with the repair loop. The recommendation is one targeted reliability fix and a re-run first; no new features, no validator changes.
