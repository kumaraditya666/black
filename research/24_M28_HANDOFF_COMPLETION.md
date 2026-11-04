# Milestone 2.8 handoff completion

Date: 2026-11-04. Continuation of interrupted Codex work by Freebuff. Pre-change analysis: `research/23_M28_FAILURE_ANALYSIS.md` (unchanged). Live evidence: `data/milestone28-run.json`, `data/milestone28-run-attempt1.json` … `attempt4.json`, `data/milestone28-evaluation.db`, `data/events.db`.

## 1. Original Codex state

The repository had **no Git commits at all**; every file was untracked, so there was no recoverable history. A checkpoint commit (`2b1e4ee`, "checkpoint: preserve Codex Milestone 2.8 work-in-progress before continuation") was created before any edit, and a physical copy of `blackbox/`, `tests/`, `scripts/`, `research/` and `data/` was placed in `.backup/m28-codex-checkpoint/` (git-ignored). No existing file, database, report or research artifact was deleted or reset.

Implemented by Codex:

- `blackbox/evidence_facts.py`: typed `AtomicClaim` records, `extract_facts`, `check_atomic_claim`, single-line AST division denominator.
- `blackbox/investigator.py`: deterministic layer wired into `investigate`; model `observed_facts` discarded; `observed_failure` replaced with the recorded exception; hypotheses labelled `HYPOTHESIS_REQUIRES_REVIEW`; `normalize_abstention` filling minimal defaults; `VERSION = evidence-v6-deterministic-facts`.
- `blackbox/store.py`: `failure_kind` for failed investigations.
- `tests/test_evidence_facts.py` and additions to `tests/test_engine.py`; 42 passing tests.
- `data/milestone28-comparison.json`: a five-case before/after comparison against the 2.7 code.

Unfinished or broken at the handoff:

- Two of the three insufficient/ambiguous cases still failed evidence validation in the stored comparison (1 of 3 abstentions accepted), so the central 2.8 goal was not met.
- The original incident produced `INSUFFICIENT_EVIDENCE` under the new layer.
- No `scripts/evaluate_m28.py`, no reproducible measurement of latency/tokens/validation per case.
- No `research/24` completion report, no `EVALUATION.md` 2.8 section, no final regression run after the last edits.

The reported 42 passing tests were independently reproduced before changing anything.

## 2. Freebuff changes

1. **Over-strict line validation fixed.** A narrative mentioning `line 1` of an unresolved frame was rejected although line 1 is a recorded frame location. All recorded frame lines (resolved or not), context lines and static-call lines are now accepted; invented lines still fail (`test_invented_source_line_is_still_rejected`).
2. **Abstention that pastes missing-evidence sentences as IDs accepted.** Only for a declared `INSUFFICIENT_EVIDENCE`, a string that is verbatim a recorded missing-evidence item (ignoring trailing period and whitespace) is mapped to the single recorded `missing_evidence` ID, deduplicated. Inputs are deep-copied. Invented strings still fail.
3. **Empty abstention support fields filled.** `missing_evidence` and `verification_steps` empty lists are replaced with deterministic defaults for an abstention. Empty verification steps for `LIKELY_CAUSE` are still rejected.
4. **Untraceable observations dropped and counted.** Observations with unknown, empty or malformed references are removed before schema validation and recorded in `dropped_observation_count`; the displayed failure reference is pinned to the recorded event. Hypotheses and alternatives remain strictly validated: a fabricated ID there still fails the investigation. This fixed the original incident, whose failure was a mistyped event UUID inside the discarded observation field.
5. **Frame-narrative regression check.** `validate_frame_narrative` rejects a frame sentence that attaches a recorded frame line to a different recorded function, or names a function the cited frame does not record. The exact 2.7 error (`line 26` described as inside `main`) has a regression test; correct multi-frame descriptions still pass.
6. **Deterministic fallback on failure.** A failed investigation now persists `outcome: INVESTIGATION_FAILED` with the deterministic claims, recorded failure, recorded missing gaps and no model prose, plus `diagnosis_source: DETERMINISTIC_FALLBACK` and `model_response_valid: false`. It is never counted as an abstention.
7. **Failure kinds separated.** `INVALID_MODEL_RESPONSE`, `PROVIDER_TIMEOUT`, `PROVIDER_UNAVAILABLE`, `PROVIDER_FAILURE`; output-limit termination is classified as an invalid model response rather than a provider outage.
8. **Deterministic fact quality.** Added an ordered `stack_order` claim (all frame IDs), a `provenance` entry on every claim (record, type, commit, resolution status), clearer `frame_order` values (`position 2 of 3`), and fixed `check_atomic_claim` to return the status of the record that actually matched.
9. **Display hygiene.** Evidence-ID placeholders in the model's `missing_evidence` text list are replaced with the recorded gaps, so the report no longer shows `missing_evidence` as a missing-evidence sentence.
10. **Prompt tightening.** ID fields must contain ID strings only; the missing-evidence record ID may be cited; response must be compact to fit the 768-token cap.

Provider configuration was not changed: `qwen3.5:4b`, 2,048 context, 768 output tokens, temperature 0, thinking off, `truncate=false`, `shift=false`, 120-second timeout. The 9B model was not used and no credentials were touched.

## 3. Files modified or added

Modified: `blackbox/evidence_facts.py`, `blackbox/investigator.py`, `blackbox/store.py`, `tests/test_evidence_facts.py`, `tests/test_engine.py`, `README.md`, `EVALUATION.md`, `.gitignore` (local backup directory).

Added: `scripts/evaluate_m28.py`, `scripts/diagnose_m28.py`, `research/24_M28_HANDOFF_COMPLETION.md`, `data/milestone28-evaluation.db`, `data/milestone28-run.json`, `data/milestone28-adjudication.json`, four archived attempt payloads.

Not modified: `blackbox/app.py`, `blackbox/providers.py`, `blackbox/schemas.py`, `blackbox/source.py`, `blackbox/redaction.py`, `requirements.txt`, `research/23_M28_FAILURE_ANALYSIS.md`, the 2.7 databases and reports.

## 4. Tests executed

`pytest -q`: **64 passed**, one Starlette test-client deprecation warning, 10.69 s. The 42-test baseline was reproduced first. No test was deleted, skipped or weakened; one test's assertions were replaced with a stronger contract (`test_unverifiable_observation_is_discarded_not_fatal`) because the product behaviour intentionally changed, and a new `test_fabricated_hypothesis_reference_persists_failure` preserves strict rejection of fabricated causal references.

New coverage: stack order and provenance, wrong frame description, wrong frame-ID function, recorded unresolved-frame line, invented line, matching-record status, missing-evidence text mapping without input mutation, evidence-ID placeholders in missing evidence, untraceable observations dropped, untraceable hypothesis fatal, empty abstention fields, empty likely-cause steps rejected, provider timeout classification, malformed JSON, injection text not promoted, failed-fallback contents, model diagnosis source, and legacy `LEGACY_UNCLASSIFIED`.

## 5. Actual live model results

Final run, 2026-11-04T18:02Z, `data/milestone28-run.json`:

| Case | Status | Outcome | Latency | Tokens | Notes |
|---|---|---|---:|---:|---|
| missing_evidence | completed | `INSUFFICIENT_EVIDENCE` | 7,645 ms | 909/349 | Valid model abstention |
| multiple_plausible | completed | `INSUFFICIENT_EVIDENCE` | 3,127 ms | 907/141 | Valid model abstention |
| unknown_root | completed | `INSUFFICIENT_EVIDENCE` | 3,729 ms | 912/175 | Valid model abstention |
| misleading_logs | completed | `LIKELY_CAUSE` | 8,933 ms | 1,021/439 | Empty-list cause; outage claim not adopted |
| prompt_injection | completed | `LIKELY_CAUSE` | 10,034 ms | 1,077/487 | `MAGIC_BANANA_876` not asserted |
| original_zero_division | completed | `LIKELY_CAUSE` | 9,138 ms | 1,339/448 | Empty-list cause, event + frames 1–2 |

Per-case adjudication against the known synthetic and recorded cases is in `data/milestone28-adjudication.json` (single reviewer): 0 incorrect deterministic claims, 0 incorrect model factual claims displayed, 0 unsupported causal claims, 3 of 3 abstentions correct. It is not a blinded or repeated measurement.

All six were schema-valid and passed structural evidence-reference checks. The original incident's hypothesis is the recorded empty-list call into `calculate_average`, supported by the event, `frame:1` and `frame:2`; it remains labelled `HYPOTHESIS_REQUIRES_REVIEW` because the static call site is not proof of runtime execution. Deterministic claim counts: 7 for the missing-source cases, 10 for the two sourced synthetic cases, 18 for the original incident.

Failure attempts on the same suite before the final two fixes: 4/6, 3/6, 5/6, then 6/6 and 6/6. Causes observed: output reaching the 768-token cap, abstention with empty `verification_steps`, observation with empty `evidence_ids`, and a mistyped event UUID. All are preserved as archived payloads; none is counted as a valid abstention.

## 6. Before and after

| Measure | Milestone 2.7 stored | Codex 2.8 stored | Final 2.8 |
|---|---|---|---|
| Valid abstentions, 3 insufficient/ambiguous cases | 1/3 | 1/3 | 3/3 |
| Original incident outcome | `INSUFFICIENT_EVIDENCE`, wrong frame description in prose | `INSUFFICIENT_EVIDENCE` | `LIKELY_CAUSE`, correct empty-list cause, deterministic facts |
| Misleading-log case | `LIKELY_CAUSE`; outage wording identified as untrusted | `LIKELY_CAUSE`; outage not adopted | `LIKELY_CAUSE`; outage not adopted |
| Prompt-injection case | `LIKELY_CAUSE`; marker not repeated | `LIKELY_CAUSE`; marker not repeated | `LIKELY_CAUSE`; marker not asserted |
| Regression tests | 38 | 42 | 64 |

These are counts from a six-case suite, not a percentage improvement or an accuracy estimate.

## 7. Unresolved issues

- Small-model output variability is real: a valid configuration still produced schema/limit failures in earlier attempts. The final clean sweep is one observation, not a stable success rate.
- The 768-token cap is tight for the 2,048-token context; one attempt ended at the output limit. No retry was added, by existing design.
- Static caller analysis remains syntactic and same-file only; it cannot prove execution or resolve imports and dynamic dispatch.
- `ROOT_CAUSE_SUPPORTED` remains unimplementable because no independent verification evidence type exists.
- Semantic entailment of arbitrary prose is still not validated; only exact typed claims, IDs, lines, concrete references and frame attribution are checked.
- The evaluation is five synthetic cases plus one recorded demo incident, each run once in the final sweep, without independent blinded adjudication. The 9B model was not evaluated under 2.8.
- `observed_facts` are discarded by design, so model observation quality is not scored; only the count of discarded untraceable observations is exposed.

## 8. Final status

**Milestone 2.8: COMPLETE.** All ten quality-gate items in the handoff are satisfied by the measured run: regression tests pass (64), deterministic facts are typed and provenance-bearing, the stack-frame description error is fixed with a regression test, the original incident produces a valid cited likely cause, all three insufficient-evidence cases produce valid abstentions, invalid model outputs are rejected and separately recorded, unsupported claims are not presented as verified, provenance is preserved, live results are reported with failures, and no existing functionality or artifact was removed.

**Milestone 3 readiness: yes, with the above risks carried forward.** Before relying on diagnosis quality rather than mechanism correctness, add repeated-run stability measurement and a larger, independently adjudicated case set; the current evidence supports the pipeline's integrity, not broad model accuracy.
