# M4B.3 Prospective Amendment

**Amendment ID:** `M4B3-AMENDMENT-01`  
**Status:** `DRAFT — NOT APPROVED`  
**Original preregistration commit:** `13bdc52bad27c49b77e85daac16876133f382009`  
**Date prepared:** 2026-11-07  
**Approval:** ______________________________  
**Approval date:** _________________________

This document proposes prospective clarifications and changes to the M4B.3 preregistration. The pinned Git blob at the commit above is the authoritative record of the original protocol. This draft does not amend that blob, approve an amendment, or authorize execution. No investigator inference has occurred.

## 1. Purpose and scope

The purpose is to resolve the preregistration discrepancy identified in the review at `research/55_M4B3_PREREGISTRATION_DISCREPANCY_REVIEW.md` through Path B: preserve the original registered text and separately document proposed changes before any inference. The current working copy of `research/50_M4B3_EVIDENCE_LAYERED_REASONING.md` contains additions not present in the pinned blob; those additions are not treated here as originally registered methodology.

## 2. Original design preserved

Subject to approval of this amendment, the experiment remains the originally registered held-out comparison:

- Six frozen, synthetic, source-only cases and four arms A, B, C, and D in a 2×2 prompt/schema design.
- Local Ollama model tag `qwen3.5:4b`; the original text specifies Ollama settings, context 2,048, temperature 0, thinking disabled, a provider output limit, a single request budget, and no retries.
- Ground-truth labels remain scorer-only and must never enter investigator evidence or model-facing context.
- No fixture execution, Docker, repair, production routes, external requests, or autonomous patching.
- Maximum 24 planned evaluations (four per case), one request per case/arm, with no automatic retries.
- Causal attribution remains `NOT_ESTABLISHED` without authenticated runtime evidence linking a mechanism to the reported event.

The original preregistration also retains its registered prompt/schema definitions, source-verification requirement, stopping boundary, and prohibition on production or reliability-gate changes. Sections below are proposed additions and must not be backdated or represented as original text.

## 3. Proposed methodological clarifications and changes

### 3.1 A/B raw-output interpretation

For Arms A and B, evaluate the validated raw model response before product-level post-processing. The product path may discard model-authored observed facts before persisted or displayed findings are produced. The proposed A/B estimand is therefore raw legacy-schema capability under the registered evidence package and validation, not the final product's persisted or displayed findings. These arms do not evaluate the complete production user experience, including downstream transformation, presentation, or user interaction.

This narrows the interpretation of A/B outcomes; it does not change the product route. **Proposed change:** interpretation only. **Reason:** make the measurement boundary explicit and avoid extrapolating raw output to product behavior.

### 3.2 Cross-pair interpretation

| Arm | Prompt | Schema | Pairing |
|---|---|---|---|
| A | Current | Current | Aligned |
| B | Layered | Current | Intentionally mismatched diagnostic condition |
| C | Current | Layered | Intentionally mismatched diagnostic condition |
| D | Layered | Layered | Aligned |

B and C are deliberately mismatched diagnostic conditions; A and D are aligned. The current prompt does not request all layered-schema fields, and the layered prompt asks for distinctions the current schema cannot represent. Constrained output may affect the observed interaction between prompt and schema. Comparisons involving B or C therefore describe these particular combinations and their format pressure. Even A-versus-B or C-versus-D comparisons do not, by themselves, isolate a causal effect of changing only the prompt or only the schema, nor establish general prompt/schema main effects.

**Proposed change:** interpretation and reporting. **Reason:** limit factorial conclusions to what the observed combinations support.

### 3.3 Scoring framework

Propose dimension-specific labels `correct`, `partly_correct`, `incorrect`, `unsupported`, and `not_applicable`. Apply only labels that make logical sense for a given dimension. Scores are not ordinal measurements and must not be averaged into a single accuracy score. Preserve separate reporting of unsupported claims, justified abstentions, structured validity, latency, and token usage. Operational scoring rules and case guidance appear in Document 57, which is evaluator-only.

The original preregistration calls for separate dimension scores and no aggregate accuracy; the five-label vocabulary and detailed scoring rules are additions. **Proposed change:** scoring and interpretation. **Reason:** make human coding more repeatable while disclosing that operational rules can affect scores.

### 3.4 Model identity and inference configuration

Proposed fixed configuration for any later approved run:

| Setting | Proposed value |
|---|---|
| Model tag | `qwen3.5:4b` |
| Full installed model digest | `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` |
| Ollama version observed | `0.40.14` |
| Context | 2,048 |
| Temperature | 0 |
| Thinking | Disabled |
| Output cap | 768 tokens |
| Request timeout | 60 seconds |
| Retries | 0 |
| Maximum evaluations | 24 |

The tag and digest identify the installed model artifact observed during preflight; context, temperature, thinking, output cap, timeout, retry count, and evaluation budget are request/protocol settings. Neither model identity nor settings guarantee answer quality. The original preregistration does not record the numerical 768-token cap, 60-second timeout, or full digest. The preflight recorded the full digest and Ollama version; it did not record hardware details. **Hardware: not recorded.** The runner's digest-prefix check and full digest record are proposed prospective safeguards, not original registered text.

**Proposed change:** execution configuration and artifact identity, with interpretation/reporting consequences. **Reason:** remove ambiguity about the exact request budget and locally installed model. These values must be reverified before any approved inference.

### 3.5 Frozen source identity

The immutable commit `13bdc52bad27c49b77e85daac16876133f382009` is the authoritative fixture and label identity. The name `refs/blackbox/m4b3-freeze` is a mutable Git ref and must not be described as an immutable identifier. The current runner is reported to read registry, labels, source, and documentation blobs from the pinned commit and verify registered hashes. This is a provenance clarification/correction relative to the earlier runner behavior described in the provenance audit; the ref name alone is not a sufficient identity.

**Proposed change:** execution provenance and interpretation. **Reason:** make the source snapshot independently reproducible and distinguish the immutable commit from its movable alias.

### 3.6 Interpretation and limitations

There is no registered numerical success threshold and no automatic rule for declaring a winning arm. Results are descriptive evidence, not a production reliability certification. No result can establish real-world causal attribution without appropriate authenticated runtime evidence. Six synthetic cases and one local model cannot establish general debugging capability. Scores may inform a bounded comparison on these cases only; they do not authorize product, route, repair, or reliability-gate changes.

**Proposed change:** explicit pre-results interpretation limits. **Reason:** prevent post hoc thresholds or overgeneralized reliability claims. This amendment adds no pass/fail criterion.

### 3.7 Evaluator guidance and disclosure

Document 57 proposes an evaluator-only rubric with case-specific evidence boundaries and scoring cues. The evaluator will see likely mechanisms and contract availability, so is not fully blinded; evaluator priming is a material limitation. The rubric must not be provided to the investigator model or placed in prompts, retrieval results, or investigator evidence. Human reviewers should decide whether this evaluator process is acceptable before any scoring.

**Proposed change:** scoring procedure and evaluator disclosure. **Reason:** improve consistency while making potential priming explicit.

### 3.8 Durable attempt ledger and crash-boundary handling

The earlier preflight identified ambiguity at the crash boundary: the process can dispatch an inference request and terminate before its response and result are durably recorded. A later run could then silently submit the same case/arm evaluation again, violating the one-request-per-case/arm and zero-retry design. Subject to approval, a durable attempt ledger is a prerequisite to any live inference.

For every planned evaluation, the runner must assign a stable evaluation ID; for each actual dispatch attempt, it must assign a unique attempt ID. Before dispatching a model request, it must durably append an `IN_FLIGHT` record containing at least the case ID, arm, evaluation ID, attempt ID, model identity/configuration reference, and attempt-start timestamp. The ledger must preserve attempt transitions as an append-only audit history; earlier records must not be silently rewritten or erased.

After the request, record one of these terminal states:

- `COMPLETED`: the response and corresponding result record have both been durably saved.
- `FAILED`: a failure is known and recorded; it does not trigger an automatic retry.
- `UNKNOWN_OUTCOME`: it is uncertain whether the request was dispatched or completed, or whether its response was lost before durable result persistence.

At startup, inspect and validate the ledger before allowing any evaluation. Fail closed when an unresolved `IN_FLIGHT` or `UNKNOWN_OUTCOME` attempt exists. Do not silently resubmit an evaluation with an uncertain prior outcome and do not automatically retry failed or uncertain attempts. Require explicit human reconciliation before proceeding; preserve the decision and its evidence in the audit history. If evidence cannot establish the outcome, preserve the uncertainty rather than marking the evaluation completed or failed.

A local durable ledger records that the process was about to dispatch, but cannot always prove whether Ollama received the request at the crash boundary. An unresolved `IN_FLIGHT` record must therefore be treated as `UNKNOWN_OUTCOME`. This proposal does not guarantee exactly-once model execution, and an uncertain request must never be replayed automatically.

The attempt-ledger requirement is proposed, not implemented or verified. Its presence in this amendment does not authorize inference. Read-only inspection of the current runner confirms that it records a result only after the provider returns or raises; the provider sends the Ollama request without a pre-dispatch ledger callback. The existing tests do not verify ledger transitions or unresolved-attempt blocking.

**Proposed change:** execution control and auditability. **Reason:** prevent silent duplicate requests after crashes and preserve the registered no-retry/one-request budget. **Execution impact:** requires runner implementation and validation before inference. **Scoring impact:** none directly; uncertain or missing outcomes remain explicitly missing and are not scored as completed responses. **Interpretation impact:** incomplete and uncertain evaluations remain visible.

## 4. Change classification table

“Original registered position” below refers to the pinned text at the original commit, not its current working-copy additions.

| Item | Original registered position | Proposed change | Reason | Execution impact | Scoring impact | Interpretation impact | Human approval required? |
|---|---|---|---|---|---|---|---|
| A/B raw output | Current schema validation is retained; post-processing boundary is not specified as the A/B estimand. | Score validated raw response before product post-processing. | Define what A/B measures. | None to prompts/calls; fixes observation point. | Raw output is scored. | No claim about persisted/displayed product UX. | Yes |
| Four-arm interpretation | 2×2 arms and intentional mismatch exist; limits on cross-pair attribution are not fully operationalized. | Label A/D aligned and B/C diagnostic mismatches; qualify cross-pair comparisons. | Avoid overclaiming isolated prompt/schema effects. | None. | Preserve all arm identities. | Combination-specific descriptive inference only. | Yes |
| Scoring labels and rules | Separate listed dimensions and no aggregate accuracy; no five-level vocabulary or detailed operational rubric. | Adopt five labels dimension by dimension; use evaluator-only Document 57. | Increase repeatability and surface unsupported claims/abstention. | Adds no model input. | Can affect human coding and summaries. | No aggregate score or implicit winner. | Yes |
| Model/request settings | Tag, context 2,048, temperature 0, thinking off, provider output limit, single request budget, no retries. | Record exact digest, observed Ollama version, cap 768, timeout 60 seconds, and fixed maximum 24. | Reproducibility and precise budget. | Fixes parameters for any run. | Adds token/latency reporting context. | Yes |
| Frozen source identity | Six source-only cases to be frozen; exact immutable commit was a placeholder in original text. | Pin all inputs to commit `13bdc52…`; treat named ref as mutable; report runner blob reads. | Correct provenance and avoid ref drift. | Requires pinned-commit reads and hash checks. | Keeps case/label identity stable. | Makes source scope auditable. | Yes |
| Interpretation limits | No production/reliability change authorized; numeric success and arm winner criteria unspecified. | State no threshold, no automatic winner, descriptive scope, no causal proof without telemetry, and limited generalization. | Prevent post hoc decision rules and overclaiming. | None. | None beyond existing separate dimensions. | Constrains conclusions. | Yes |
| Durable attempt ledger | Original preregistration does not specify a durable attempt-ledger mechanism. | Add durable attempt state, pre-dispatch persistence, fail-closed startup, unresolved-attempt blocking, and manual reconciliation. | Prevent silent duplicate requests after crashes and preserve the no-retry/one-request budget. | Requires runner implementation and validation before inference. | None directly; uncertain or missing outcomes remain missing rather than scored as completed responses. | Makes incomplete and uncertain evaluations visible. | Yes |
| Evaluator disclosure | Single author/scorer and exposed diagnostic-case limitations are noted; no separate operational evaluator guide. | Add evaluator-only case guidance and disclose priming/unblinded status. | Support consistent scoring and disclose bias risk. | Rubric excluded from model context. | Makes scoring cues explicit. | Scores remain vulnerable to evaluator priming. | Yes |

## 5. Approval gate before inference

This draft remains **`DRAFT — NOT APPROVED`**. No inference is authorized. Before any inference, a human reviewer must:

- [ ] Review and approve each proposed methodological, execution, and scoring change.
- [ ] Confirm that the immutable commit and source hashes are the intended frozen inputs.
- [ ] Verify the model digest, Ollama version, and request settings at the time of the proposed run; decide how unrecorded hardware is handled.
- [ ] Approve the A/B observation point and the limits on cross-arm interpretation.
- [ ] Review Document 57's evaluator-only disclosure, case cues, and priming risk.
- [ ] Confirm the results template is still empty and that the 24-evaluation/no-retry budget and all safety boundaries remain in force.
- [ ] Implement and review the attempt ledger before inference; test interruption before dispatch, after dispatch but before result persistence, known provider failure, result persistence failure, and startup with unresolved attempts.
- [ ] Verify that the runner refuses to continue with an unresolved attempt, performs no automatic retry or silent resubmission, and preserves the append-only audit history.
- [ ] Record an explicit approval name/signature and date in the approved version before any investigator call.

**Approval:** ______________________________  
**Approval date:** _________________________

Until these items are resolved in an approved version, do not conduct inference or treat this draft as authorization.
