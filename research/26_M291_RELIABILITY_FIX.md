# Milestone 2.9.1 — structured-output reliability fix and revalidation

Date: 2026-11-04. Model and configuration unchanged: local Ollama `qwen3.5:4b` (digest prefix `d8b0f5e9760c`, 3.3 GB Q4_K_M), 2,048-token context, temperature 0, thinking off, `truncate=false`, `shift=false`, 120-second timeout. The 9B model was not used. No context increase and no new dependency.

Artifacts: `data/milestone291-fresh-run.json`, `data/milestone291-replay-run.json`, `data/milestone291-adjudication.json`, `data/milestone291-before-fresh.json`, `data/milestone291-before-replay.json`, `data/m291-fresh.log`, `data/m291-replay.log`, `scripts/evaluate_m29.py`.

## 1. Confirmed failure mechanism

The Milestone 2.9 artifacts were re-read before any change. All six failures in the fresh pin set were `INVESTIGATION_FAILED` with `failure_kind: INVALID_MODEL_RESPONSE` and the error "Model output reached the token limit"; none was an evidence-reference rejection.

`data/m29-truncated-output.json` records the provider-level cause directly:

- `done_reason: length`, `eval_count: 768` — the fixed `num_predict` cap, not the context window.
- `prompt_eval_count: 893` against `num_ctx: 2048`, leaving about 1,155 tokens of headroom.
- The content is 2,096 characters of JSON ending mid-object, after 13 `text` fields, all inside `observed_facts`.

The prompt already instructed "at most three observed_facts, at most three verification_steps", but `Findings.model_json_schema()` permitted 20 of each, and that schema is the one passed to Ollama as `format`. Constrained decoding therefore had no reason to stop; the model enumerated observations until the token cap cut the object. The two failing fresh scenarios were unresolved-source cases whose prompt nudged the model into a long observation list, while the equivalent 2.8 snapshots produced 349-token abstentions.

Two secondary gaps were visible in the same records: provider usage was not persisted when generation ended at the cap (`usage` is null for those six runs), and the 768-token cap did not vary with prompt size, even though the recorded incident's 1,339-token prompt leaves only about 700 tokens of actual headroom.

## 2. Schema fix

`blackbox/investigation_schema.py` now declares:

```python
OBSERVED_FACT_LIMIT = 3
VERIFICATION_STEP_LIMIT = 3
observed_facts: list[Claim] = Field(default_factory=list, max_length=OBSERVED_FACT_LIMIT)
verification_steps: list[str] = Field(default_factory=list, max_length=VERIFICATION_STEP_LIMIT)
```

Because these limits are Pydantic field constraints, they appear as `maxItems: 3` in `Findings.model_json_schema()`, which is sent as the Ollama `format` and the Gemini `response_json_schema`. The same model validates the response, so the bound is enforced during generation and again after parsing. The limits match the existing prompt instruction; no additional constraint was invented.

Preserved behaviour:

- `outcome` still distinguishes `LIKELY_CAUSE`, `INSUFFICIENT_EVIDENCE` and the reserved `ROOT_CAUSE_SUPPORTED`/`INVESTIGATION_FAILED` values, and `ROOT_CAUSE_SUPPORTED` and `INVESTIGATION_FAILED` are still rejected from model output.
- A declared abstention may cite 1–3 steps; an empty step list is still filled with the deterministic default for an abstention only, and an empty list for `LIKELY_CAUSE` still fails.
- Model observations remain discarded from reports; `atomic_claims` remain the only displayed facts, each with evidence IDs and provenance.
- `INVESTIGATION_FAILED` remains a hard terminal state with deterministic facts and no model prose.

## 3. Adaptive output budget

`blackbox/providers.py` adds `output_budget(prompt, context_length)`:

```
estimated_prompt = ceil(len(prompt) / 3.5)
available        = context_length - estimated_prompt - 64
num_predict      = min(768, available)      # error if available < 320
```

- The 768 cap is retained, so resource use for small prompts is unchanged.
- The 3.5 characters-per-token estimate deliberately over-counts: measured prompts in this project run 3.9–5.4 characters per token (893 tokens for 3,484 characters; 1,339 for 4,812). The 64-token reserve covers chat-template overhead and estimate error.
- If fewer than 320 output tokens would fit, the adapter raises `ProviderError('Evidence prompt does not fit safely…')` before calling the model. Evidence is never trimmed to make a request fit. That failure is stored with the new `failure_kind: EVIDENCE_TOO_LARGE`, distinct from a truncation.
- A truncated completion now carries `{input_tokens, output_tokens, output_limit}` on the error, and the investigator persists it in `usage`, so a truncation is measurable rather than silent. `INVESTIGATION_FAILED` is still returned; truncated output is never treated as a successful investigation.

Measured impact of the budget itself: only the recorded incident's 4,812-character prompt was reduced, from 768 to 609 output tokens; all other prompts kept 768. The largest observed output in the revalidation was 504 tokens, so the reduced budget did not bind.

## 4. Tests

`pytest -q`: **70 passed**, one Starlette test-client deprecation warning (11.54 s). No test was removed, skipped or weakened; validation rules were not relaxed.

New focused tests in `tests/test_engine.py`:

- `test_model_facing_schema_bounds_observation_and_step_lists` — inspects the generated JSON schema (`maxItems == 3`), accepts exactly three steps/facts and rejects four.
- `test_output_budget_shrinks_for_large_prompts_without_dropping_evidence` — small prompt keeps 768; a 5,000-character prompt gets a smaller budget; an 8,000-character prompt raises the clear fit error.
- `test_ollama_adapter_sends_bounded_schema_and_adaptive_budget` — the real adapter sends the bounded schema and the computed `num_predict`.
- `test_truncated_json_is_a_hard_failure` — mid-object JSON yields `INVESTIGATION_FAILED`, `INVALID_MODEL_RESPONSE`, deterministic facts only, no hypotheses.
- `test_truncated_completion_keeps_token_usage` — the token counters are persisted on a truncation.
- `test_oversized_evidence_reports_a_distinct_failure` — `EVIDENCE_TOO_LARGE` with the deterministic fallback and no prose.

Existing coverage still exercises valid abstentions, evidence-reference rejection, cached reuse, prompt-injection non-promotion, timeout/unavailability classification, frame-narrative rejection and legacy records.

## 5. Revalidation protocol

Same protocol and pinned evidence as Milestone 2.9, with six live runs per base case (36 total):

- three **fresh** runs on the 2.9 fresh snapshots (identical event IDs, timestamps and databases, so the evidence hashes match 2.9);
- three **replay** runs asserting the exact 2.8 `evidence_hash` for each scenario.

Two previously unseen fresh scenarios were added as a generalization probe, three runs each (6 extra runs, 42 total):

- `unseen_unresolved_import` — `ImportError: No module named "yaml"` at an unresolved `settings.py` frame; expected abstention.
- `unseen_two_frame_division` — two resolved frames at `buggy_app.py` lines 13 and 17, message `float division by zero`; expected empty-list cause.

Neither unseen payload reuses a 2.9 scenario's event ID or timestamp.

## 6. Results

### Base cases — fresh pinned snapshots

| Case | 2.9 result | 2.9.1 result | Latency 2.9 → 2.9.1 (median) | Output tokens |
|---|---|---|---|---:|
| missing_evidence | failed ×3 (truncation) | abstention ×3 | 15,429 → 6,554 ms | 768 → 321 |
| multiple_plausible | abstention ×3 | abstention ×3 | 4,311 → 4,405 ms | 220 → 220 |
| unknown_root | failed ×3 (truncation) | abstention ×3 | 15,413 → 6,497 ms | 768 → 318 |
| misleading_logs | cause ×3 | cause ×3 | 9,369 → 9,524 ms | 483 → 483 |
| prompt_injection | cause ×3 | cause ×3 | 9,390 → 9,395 ms | 472 → 472 |
| original_zero_division | cause ×3 | cause ×3 | 8,937 → 9,592 ms | 452 → 479 |

### Base cases — exact 2.8 snapshots (replay)

| Case | 2.9 result | 2.9.1 result | Latency 2.9 → 2.9.1 (median) | Output tokens |
|---|---|---|---|---:|
| missing_evidence | abstention ×3 | abstention ×3 | 6,878 → 6,974 ms | 349 → 355 |
| multiple_plausible | abstention ×3 | abstention ×3 | 3,518 → 2,863 ms | 174 → 141 |
| unknown_root | abstention ×3 | abstention ×3 | 3,613 → 3,599 ms | 175 → 175 |
| misleading_logs | abstention ×3 | cause ×3 | 5,960 → 9,038 ms | 297 → 454 |
| prompt_injection | cause ×3 | cause ×3 | 9,543 → 9,576 ms | 478 → 479 |
| original_zero_division | cause ×3 | cause ×3 | 9,008 → 9,547 ms | 452 → 479 |

### Unseen scenarios

| Case | Expected | Result | Latency median |
|---|---|---|---:|
| unseen_unresolved_import | abstain | valid abstention ×3 | 7,328 ms |
| unseen_two_frame_division | likely cause | correct cause ×3 | 10,015 ms |

### Aggregate, base cases only (36 runs)

| Measure | Milestone 2.9 | Milestone 2.9.1 |
|---|---:|---:|
| Completed runs | 30/36 (83.3%) | **36/36 (100%)** |
| Output truncations | 6 | **0** |
| Valid abstentions on the three insufficient cases | 12/18 (fresh 3/9, replay 9/9) | **18/18** |
| Correct causes on the three sourced cases | 15/18 (fresh 9/9, replay 6/9) | **18/18** |
| Adjudicated correct | 27/36 | **36/36** |
| Conservative misses | 3 | **0** |
| Incorrect causes | 0 | **0** |
| Invalid evidence references accepted | 0 | **0** |
| Max output tokens in any run | 768 (truncated) | 504 |
| Mean latency | fresh 10,799 ms / replay 6,528 ms | fresh 7,977 ms / replay 7,042 ms |

With the two unseen scenarios included, adjudication is **42/42 correct** (`data/milestone291-adjudication.json`, one unblinded reviewer).

## 7. Quality gate

- **Structured output failures decreased:** 6/36 → 0/36. All six failures were truncations; the bounded schema removed them, and the re-run produced no schema or evidence-validation failures.
- **Abstention reliability improved:** 12/18 → 18/18 on the intended insufficient-evidence cases, in both pin sets, and both fresh and replay.
- **Evidence integrity preserved:** zero invalid references accepted; deterministic claim counts unchanged (7 for unresolved single-frame cases, 10 for resolved single-frame cases, 18 for the recorded incident); every hypothesis is labelled `HYPOTHESIS_REQUIRES_REVIEW`; `ROOT_CAUSE_SUPPORTED` remains impossible.
- **Investigation correctness did not regress:** all nine sourced fresh runs and all nine sourced replay runs returned the correct empty-list cause with the event and a resolved frame cited. The recorded incident again cites both `frame:1` and `frame:2`, as in 2.8.
- **Local inference remains practical:** same model, same 2,048 context, no added memory or dependency; medians 6.5–9.6 s per run; slowest single run 15.4 s.
- **All regression tests pass:** 70 passed.

Reproducibility against 2.8: the replay set now reproduces all six 2.8 outcomes, including `misleading_logs = LIKELY_CAUSE` (2.9 had abstained on those bytes). `missing_evidence`, `multiple_plausible` and `unknown_root` token counts are within six tokens of 2.8; the original incident is 479 tokens versus 448 and keeps both cited frames.

## 8. Remaining issues

- **Session-level variability is not eliminated.** `misleading_logs` changed outcome between 2.8, 2.9 and 2.9.1 sessions on the same bytes. The 2.9.1 change is confounded with the schema/budget change, so this run cannot separate session nondeterminism from prompt-distribution change. Within a session, all repetitions were again identical.
- **Cosmetic placeholder:** one fresh `missing_evidence` abstention displays `id:missing_evidence` in the `missing_evidence` text list. The existing normalizer strips bare ID placeholders but not an `id:`-prefixed form. It is not a factual claim and did not affect validity; left unchanged to keep the measured code and the reported results identical.
- **Padded suggestions:** the bounded schema makes the model emit exactly three verification steps, and some are generic ("retrieve deployment logs"). They are suggestions, not claims, but they add little value.
- **Unused live path:** the `EVIDENCE_TOO_LARGE` path is covered by unit tests only; no live scenario exceeded the fit threshold.
- **Limits of the evidence:** one machine, one model, one session, synthetics plus a demo incident, one unblinded reviewer, and two unseen cases from the same repository family. This is not a broad reliability or accuracy claim, and it is not a production benchmark.

## 9. Readiness for a restricted Proof-of-Fix prototype

**Yes, for a restricted, developer-approved Proof-of-Fix prototype**, under these conditions:

- only incidents whose validated outcome is `LIKELY_CAUSE` with a resolved source frame may enter repair;
- `INVESTIGATION_FAILED` (including `EVIDENCE_TOO_LARGE`) and `INSUFFICIENT_EVIDENCE` are hard terminal states that cannot enter repair;
- every hypothesis remains labelled as requiring human review, and the prototype stays local and developer-operated.

This milestone measured structured-output reliability, not repair quality. It does **not** establish broad diagnostic accuracy: six base scenarios and two unseen ones, one reviewer, one model and one session are too small a sample, and the session-level flip on `misleading_logs` shows that repeated evaluations still surface variability.

Milestone 3 was not started. No automatic patching, PR automation, deployment or dashboard was built.
