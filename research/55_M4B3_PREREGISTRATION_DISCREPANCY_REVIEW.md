# M4B.3 preregistration discrepancy review

## Scope and status

This is a read-only documentation and code audit, except for creation of this report. No Ollama inference, `/api/generate`, `/api/chat`, fixture execution, Docker, repair workflow, model pull, or live runner invocation occurred. `data/m4b3-results.json` remains `template_only_no_model_calls` with `results: []`.

**Status: `READY_FOR_AMENDMENT_REVIEW`**

This means the differences have been inventoried and a prospective documentation path can be reviewed. It does **not** mean the experiment is authorized or ready to run. The recommendation below is not an approved amendment.

The comparison used the exact blob `13bdc52bad27c49b77e85daac16876133f382009:research/50_M4B3_EVIDENCE_LAYERED_REASONING.md`. The diff has four replacement blocks and no other changed lines:

| Pinned lines | Working-copy lines | Diff |
|---|---|---|
| 28 | 28–30 | One paragraph extended and one new cross-pair paragraph added |
| 53 | 55–84 | Frozen-set placeholder replaced; scoring guide and beginner guide/runbook added |
| 57 | 88 | Results placeholder replaced by a no-calls status statement |
| 61 | 92 | Decision placeholder replaced by a pre-results interpretation paragraph |

The pinned blob SHA-256 is `9a8327523165eeec73f004585114c062b193a7a77744a242c0e26d55826d5a7e`; the current working file SHA-256 is `829557b33f39017a328c828ca3b8e9f6af1d4b334be8c294f11b61e43200bccd`. The difference is substantive, not line-ending-only. No file was restored or rewritten during this audit.

## 1. Complete line-level discrepancy inventory

The categories below are: **1** formatting/non-substantive metadata; **2** explanatory clarification without a methodology change; **3** methodological change that can affect execution, scoring, interpretation, or conclusions; **4** unclear and requiring human review.

### Block 1 — A/B post-processing and cross-pair interpretation

**Pinned line 28** says the current `Findings` limitations—including that `investigate` removes model-authored `observed_facts` from the persisted/display result—are part of the control condition and “will not be relaxed.”

**Working line 28** retains that text and adds that A/B are validated with `validate_model_output` before product post-processing, so the experiment tests raw legacy-schema capability rather than what the product ultimately displays.

**Classification: 3 — methodological interpretation change.** It narrows the estimand for A/B. An outcome can support a claim about raw model output, but not automatically about the product's persisted/display behavior. This does not change prompts, schemas, or calls; it changes what a result is allowed to mean.

**Working line 30** adds that B and C have known prompt/schema format pressure, D is the only aligned pair, and cross-arms are retained to measure their failure modes. The pinned text already calls the mismatches “intentional factorial conditions,” but does not state this interpretation.

**Classification: 3 — methodological interpretation change.** This may guide how cross-arm failures are attributed and can temper conclusions about prompt versus schema effects. The registered arms do not change, but this explanation should be dated as part of the protocol rationale rather than silently treated as original text.

### Block 2 — Frozen-set identity placeholder, replaced by working line 55

**Pinned line 53** is a placeholder: “To be filled before inference with the commit, fixture hashes, prompt/schema fingerprints, hardware and model availability.”

**Working line 55** fills it with the commit `13bdc52…`, the mutable ref name, registry/hash-verification behavior, M4B.2 exclusion, model tag and digest prefix, context 2,048, temperature 0, output cap 768, timeout 60 seconds, zero retries, logging fields, and “No inference has been run.”

This is a mixed change:

- The exact commit, source hashes, model tag, and statement that M4B.2 cases are not rerun mostly fill in identity/status fields. The M4B.2 exclusion and six-case fresh-set purpose were already stated in the pinned preregistration. **Classification: 1** for those confirmations.
- The pinned text specifies context 2,048, temperature 0, thinking disabled, a provider output limit, and no retries. It does **not** specify the numerical output limit `768`, a 60-second timeout, or the digest prefix. Adding those values fixes execution settings and model-artifact identity. **Classification: 3.** They are prospective protocol parameters, not merely descriptive prose. They are consistent with the current runner, but their absence from the pinned text means they cannot be represented as values present in that original blob.
- The sentence says the six cases are frozen at the immutable commit “ref `refs/blackbox/m4b3-freeze`.” The ref later moved to descendant `9b5d444…`, while the runner correctly uses the exact `13bdc52…` commit. **Classification: 4** for this wording's present-day referent: it can make the mutable ref appear to identify the same immutable object. The commit ID is the unambiguous identity; the ref should be described historically or omitted in a future amendment.
- The working paragraph says each run records prompt/schema hashes. These are audit fields, not registered outcomes; the original safety section already required response evidence IDs, arm, validation, usage, and latency. **Classification: 1** as additional audit metadata, provided these fields do not replace or alter the registered scoring.
- The placeholder requested hardware information, but the replacement does not provide hardware details. This is an incomplete metadata fill, not an experimental-method change. **Classification: 1**, with the missing field recorded as unresolved.

### Block 3 — New scoring guide, working lines 57–69

The pinned file already says to score each arm separately, not use aggregate accuracy, and names static facts, runtime reports, contracts, mechanism hypotheses, causal attribution, abstention, unsupported claims, citations, structured validity, tokens, and latency. It also says a correct static finding with `NOT_ESTABLISHED` causality is useful and schema validity alone is not a correct diagnosis. The working copy adds operational rules and categorical labels:

| Working line | Added text/rule | Classification and effect |
|---:|---|---|
| 57, 59 | New “Layer-specific scoring guide”; labels each layer `correct`, `partly_correct`, `incorrect`, `unsupported`, or `not_applicable`; says not to average these labels. | **3.** The no-aggregate rule repeats the original, but the discrete scale is new and can change scorer coding and final summaries. |
| 61 | Static claims are judged against cited frozen source; gives `len(values)-1` and `handle → transform` as examples; static reachability is not execution. | **4.** The source-versus-execution boundary is registered, but the examples disclose likely case mechanisms to a human evaluator before scoring. A human must decide whether this is acceptable evaluator guidance or an unblinding risk. |
| 62 | Distinguishes a client-reported exception from proven execution or an input value; unsupported absent authenticated telemetry. | **3.** It is consistent with the original prompt/evidence model, but makes the scoring consequences explicit and may change scorer coding. |
| 63 | Contracts score only against supplied documentation; says five cases lack contract evidence and invented contracts are unsupported. | **4.** This is consistent with the registered evidence design, but is also a case-specific scorer cue. A human should decide whether this guidance belongs in an evaluator-only rubric and how scorer awareness is disclosed. |
| 64 | Mechanism scoring asks whether pinned code could produce an exception under a hypothetical condition, separately from whether it occurred; special note for the negative case. | **3.** This operationally separates mechanism capability from incident causality and can change which answers receive credit. |
| 65 | States `NOT_ESTABLISHED` is the only correct causal status for these packages and `ESTABLISHED` is unsupported/rejected. | **3.** The schema/validator and original design already reject causal establishment without telemetry. The guide converts that constraint into an explicit scorer key; it does not alter the validator. |
| 66 | Defines when abstention is appropriate and says not to penalize a correct local mechanism because attribution abstains. | **3.** This is an explicit reward/penalty rule that can change scores and conclusions. |
| 67 | Separates parse validity, evidence-ID validity, evidence-type validity, and semantic correctness; explains what Pydantic/custom validation do not prove. | **2.** The original lists these as separate metrics; this clarifies their interpretation without changing the dimensions. |
| 69 | States the 24-arm run is planned, dry-run has zero calls, and mocked tests do not establish model behavior. | **1.** Status/evidence note; does not alter design or scoring. |

Overall scoring-guide classification: **3**, because the new labels and operational credit rules were not present in the pinned preregistration. They are sensible candidates for a prospective rubric, but they must not be represented as if they were in the frozen text.

### Block 4 — New beginner guide/runbook, working lines 71–84

There is no corresponding section in the pinned file.

| Working line(s) | Added content | Classification and effect |
|---:|---|---|
| 71 | “Beginner guide and runbook” heading. | **1.** Structural/documentation addition. |
| 73 | Explains static analysis with the pinned `mean` function and `len(values)-1` example. | **4.** This is explanatory, but it also states a likely mechanism in one test case before human scoring. A reviewer should decide whether this evaluator-facing clue risks priming the scorer. |
| 74 | Explains that event evidence is a client report and does not prove execution or recover function arguments. | **2.** This clarifies the registered distinction between reports and authenticated runtime evidence. |
| 75 | Says only `contracted_mean/REQUIREMENTS.md` provides a contract and describes the `latest` case's undocumented expectation. | **4.** This is case-specific evaluator guidance that could disclose scoring expectations and prime a human scorer. Human review should decide whether to keep it in an evaluator-only guide and how blinding limitations are stated. |
| 76 | Explains mechanism hypotheses versus causal attribution and the `NOT_ESTABLISHED` status. | **2.** Re-explains the registered layered design. |
| 77 | Explains Pydantic, validation, citations, and evidence IDs. | **2.** Documentation only; no schema or validation behavior changes. |
| 78 | Explains why layers are scored separately. | **2.** Consistent with the original separate-score/no-aggregate rule. |
| 79–80 | Provides mocked-test and dry-run commands and states the dry run is not live execution. | **1.** Runbook details and status; the original stop rule is unchanged. |
| 82 | Adds an implementation map of existing files. | **1.** Navigation metadata. |
| 84 | Lists model improvement, semantic correctness, generalization, runtime execution, and causality as unproven; says production/repair controls were not changed. | **2.** Limitations recap; no change to the registered endpoint or stopping rule. |

The guide contains no new model-facing prompt text. Its case-specific examples can nevertheless affect human scoring; that is an evaluator-process question, not prompt leakage.

### Block 5 — Results placeholder, working line 88

**Pinned line 57** says results will be filled after calls and reused/fresh cases kept separate. **Working line 88** says no calls have been made and the run is pending.

**Classification: 1 — status metadata.** It is consistent with the empty results template and the earlier “no inference” record. It does not change the case set or scoring.

### Block 6 — Decision placeholder, working line 92

**Pinned line 61** says to fill the decision after scoring and disallows production/reliability-gate changes. **Working line 92** adds that the layered schema can represent a mechanism without established causality, that the current schema/prompt does not provide that distinction clearly, and that improvement remains unknown.

**Classification: 4 — human review required.** These statements are design rationale and pre-results expectations, not observed M4B.3 findings. They do not add a numerical pass/fail threshold, but they could frame interpretation before outcomes are seen. Preserve them as dated rationale or amendment text only if the reviewer agrees.

### Registered elements that did not change

The primary research question, 2×2 arms, evidence-layered prompt text, schema description, six case types, M4B.2 exclusion, scorer-only label rule, single-scorer/synthetic-set limitations, no aggregate accuracy rule, 24-call maximum, one call per arm/case, no retries, source verification requirement, no execution/Docker/repair, and stop-after-report boundary are unchanged in the four diff blocks. No ground-truth labels or fixture contents were edited for this review.

Neither version defines a numeric success threshold or a formal criterion for declaring one arm superior. The working copy adds a more detailed rubric, but it does not register a new promotion threshold. This absence should remain explicit in any amendment; do not infer a reliability-gate pass from descriptive scores alone.

## 2. Documentation recommendation

**Recommend path B: preserve the pinned original as the canonical preregistration and prepare a prospective, versioned amendment.** This is a recommendation for human review, not approval.

The prospective amendment should enumerate at least: the raw-output A/B estimand; cross-pair interpretation; the scoring scale and each new operational scoring rule; the 768-token cap; 60-second timeout; model digest constraint; exact source commit identity; the case-specific scorer guide; and the pre-results interpretation paragraph. For each item it should record rationale, whether it changes execution or interpretation, and its expected effect on conclusions. It should explicitly state that no investigator inference has occurred and that the amendment must be approved before any call.

Do not silently make the working copy look like the pinned blob. The preferred record is an immutable copy of the pinned text plus a separately named, dated amendment. Because the current file contains case-specific scorer guidance, the reviewer should also decide whether it belongs in an evaluator guide with an acknowledged unblinded single-scorer limitation.

## 3. Interruption-window audit

### Verified behavior in current code

- `scripts/evaluate_m4b3.py::execute` builds a result record in memory, calls `provider.structured(...)`, catches ordinary exceptions, appends the response/error record, and then calls `out_path.write_text(...)` with status `partial`.
- `blackbox/providers.py::Provider.structured` makes the Ollama `/api/chat` POST. There is no callback or ledger write before that request.
- There is no persisted attempt ID, `IN_FLIGHT` state, write-ahead marker, or resume ledger in the runner or results template.
- The partial results write occurs after the response or handled error. It is not an attempt-start record and is not shown to use an atomic replace, `fsync`, or write-ahead log.
- `main()` accepts a fresh run when `validate_template()` sees `template_only_no_model_calls`, matching revision, and an empty `results` array. There is no attempt-ledger check.

### Crash cases

1. **Crash before dispatch, before any result write:** the results file remains the empty template. It does not say whether execution was never started or had entered an attempt.
2. **Ollama completes, evaluator stops before checkpoint:** the response is lost from the results file. If this is the first evaluation, the file can still be the empty template and a later `--run-live` passes template validation and can resend the whole plan, including that evaluation. If earlier responses were checkpointed, the file is `partial` and blocks a fresh run; there is no resume path.
3. **Crash during a partial JSON write:** the file could be incomplete/corrupt. It would fail JSON/template validation rather than be accepted as a fresh template, but no durable attempt record identifies the uncertain request.
4. **Daemon cancellation:** the Ollama daemon is outside the evaluator's process lifetime; an evaluator crash does not prove the server stopped processing the request.

Therefore, a durable attempt-start record is **not** written before each request; no such record survives abrupt termination; an uncertain attempt is **not distinguishable** from one never dispatched when its result was not checkpointed. The runner has no automatic retry loop and partial/nonempty files block a fresh run, but this is not exactly-once protection. An empty template can permit replay of an uncheckpointed first attempt.

### Minimal fail-closed attempt ledger recommendation

For a later implementation, use a durable ledger separate from the final results file:

- Assign each planned evaluation a stable `evaluation_id` (revision + case + arm) and each dispatch attempt a unique UUID `attempt_id`.
- Before calling the provider, durably append an `IN_FLIGHT` record containing evaluation/attempt IDs, sequence position, case/arm, commit, evidence hash, prompt/schema fingerprints, model tag/digest, Ollama version, context, temperature, thinking flag, effective output cap, timeout, retry policy, and start timestamp. Flush the file and its directory (or use a transactional journal with equivalent durability).
- On response/error, append a terminal state tied to the same attempt ID: `COMPLETED`, `FAILED`, or `UNKNOWN_OUTCOME`, with response/result hash, validation, usage, latency, and bounded error metadata where available. Never overwrite an earlier state without preserving the transition.
- At startup, scan and validate the ledger. Any unresolved `IN_FLIGHT`/`UNKNOWN_OUTCOME` blocks live execution before provider construction. Do not automatically retry or convert it to “not sent.” Require an operator reconciliation record with identity, timestamp, rationale, and supporting evidence. An uncertain attempt counts against the 24-call budget unless the operator can establish it was never dispatched.
- Treat a persisted in-flight marker as conservative evidence that dispatch may have happened. A local ledger cannot prove whether bytes reached Ollama if the process dies between its durable marker and network send; absent server-side idempotency or trustworthy server logs, that boundary remains an unknown outcome and must stay fail-closed.
- Add crash-injection tests for termination before dispatch, after dispatch, after server response but before result checkpoint, and during ledger writes. Verify restart blocks unresolved attempts and never sends a duplicate automatically.

### Files for a later implementation

| File | Future change |
|---|---|
| `scripts/evaluate_m4b3.py` | Evaluation IDs, durable ledger transitions, startup reconciliation gate, and attempt-budget enforcement. |
| `blackbox/providers.py` | Optional pre-dispatch callback immediately before the actual Ollama POST, so the durable marker and recorded effective request config are tied to the transport boundary. This would be limited to request instrumentation; no investigator or repair behavior should change. |
| `data/m4b3-attempt-ledger.json` | New append-only local ledger, created only for the later authorized run; do not create/populate it during this review. |
| `tests/test_m4b3_harness.py` | Crash/restart, unresolved-attempt, reconciliation, durability, and no-replay regression tests using mocked transport. |
| `data/m4b3-results.json` | No change is needed if the ledger remains separate. If the result envelope is later extended with attempt IDs/ledger digest, update the template validator and template in the same reviewed change. |

The future code change is not part of this task and should not begin until the amendment and implementation are separately reviewed. The current results file remains unchanged and empty.

## 4. What remains unverified

- No live inference has been performed, so answer quality, latency, token usage, and real schema-validation rates are unknown.
- The scoring additions have not been approved as a prospective amendment.
- The provenance/timing of the working-copy edits is not established by this comparison alone; the Git blob comparison proves the textual difference, not who made each change or when relative to decisions.
- The Ollama daemon's handling of an evaluator cancellation and server-side request logs/idempotency are not established by the local runner code.
- The proposed ledger has not been implemented or tested.

**Final status: `READY_FOR_AMENDMENT_REVIEW`**
