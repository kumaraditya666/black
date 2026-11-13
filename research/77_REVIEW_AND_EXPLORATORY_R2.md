# BDB-5 R1/R2/R3 Review and Exploratory R2 Live Run

**Date:** 2026-11-10

**Status:** `TECHNICAL_REVIEW_PASSED — SIX_EXPLORATORY_R2_RUNS — 9B_RESULT_ACCEPTED_FOR_REVIEW — NOT_APPROVED — NOT_SCORED`

## 1. Technical packet review

The automated read-only review was run against the three prepared payloads.

| Case | Status | Issues | Model calls |
|---|---|---|---|
| BDB5-R1 | `REVIEW_PASSED` | 0 | 0 |
| BDB5-R2 | `REVIEW_PASSED` | 0 | 0 |
| BDB5-R3 | `REVIEW_PASSED` | 0 | 0 |

This review checks the packet/manifest separation, host-path removal, forbidden
label fields, source evidence, case-specific evidence shape and case hashes. It
is not an independent human sign-off and creates no approval record.

## 2. First exploratory live R2 run

The user explicitly authorized an exploratory live R2 call. It used the local
Ollama native API and the gated provider adapter:

| Property | Result |
|---|---|
| Case | `BDB5-R2` |
| Provider | local Ollama `/api/chat` |
| Model | `qwen3.5:4b` |
| Protocol | native Ollama, thinking disabled |
| Provider calls | `1` |
| Authorization | `EXPLORATORY_USER_AUTHORIZED_ONLY` |
| Independent approval | none |
| Scored | false |
| Runner status | `RUN_READY_FOR_REVIEW` |
| Validation issues | none |
| Input tokens | `2048` |
| Output tokens | `410` |
| Request hash | `da6ccad29d814ed48160ce52597af0b0237d71137e68264102dbcb117c153a1d` |
| Response hash | `275d3f710591fafc5dca8e5309bd6f77b93c868fec7251ccd49af054c75fa1d7` |
| Result hash | `b78369d6081a0573c50d64cf353ca2d5f5fc4d98a4ff2206b7d456ffeb013871` |

The authorization was an explicit exploratory-run record, not an independent
approval and not a benchmark result.

## 3. What the model did

The model produced a valid `InvestigationResult` but did not produce a clean R2
negative-control answer:

- it used a `SERVICE_CAUSE` claim saying the missing file indicated a missing
  fixture or an application-source issue;
- it put the abstention reasoning in an `ABSTENTION` claim;
- it left the structured `abstention` field `null`;
- it set `l2_causal_status` to `NOT_ASSESSED`;
- it added a `REPRODUCTION_BEFORE` test record without an artifact hash.

The runner accepted the schema because these are semantically weak but not
schema-invalid. It did not score the result. On the R2 strict dimensions, this
answer would not establish application-source abstention. That is a model
quality finding, not a benchmark score.

## 4. Boundary

- No independent human approval exists.
- No real score exists.
- No model output was used to change a label.
- No gold patch or hidden test was included in the prompt.
- R1, R2 and R3 remain `PREPARED`.
- The local model was called six times across this report and Document 79;
  each provider gate was opened only in its exploratory process.
- `LIVE_INFERENCE_ENABLED` in the repository remained false.

## 5. Next step

The next valid step is a real two-reviewer approval of R1/R2/R3. The exact
handoff, hashes and recording commands are in Document 78. After that, an
authorized benchmark run can be scored. Running more exploratory calls will not
make the case approved.

## 6. Post-review contract fix

The exploratory result's failure mode was fixed after this review. The provider
now requires a structured abstention whenever `l2_causal_status` is
`NOT_ESTABLISHED`, and it rejects causal claims made without one. The exact
saved result now fails with `missing_structured_abstention` instead of being
accepted. See Document 79. A separate authorized rerun is recorded below.

## 7. Contract-fix rerun

After the fix, one authorized exploratory rerun was made with the same local
model. It produced `l2_causal_status = NOT_ESTABLISHED`, no claims and
`abstention = null`. The provider rejected it with
`missing_structured_abstention` rather than accepting it. This is a guard
success, not a clean abstention. Details and hashes are in Document 79.

The provider schema and prompt were hardened afterward: `abstention` is now a
required response key, every `Abstention` field is required, and the prompt
contains a concrete abstention shape. A hardened-schema call was then made
(section 8). See Document 79.

## 8. Hardened-schema rerun

The third exploratory call used the hardened schema. It produced an
`APPLICATION_SOURCE` abstention object but omitted
`application_source_not_established`, so Pydantic rejected it before the
contract check. This is closer than the previous run but still not a valid
abstention. All five abstention fields are now required. Details and hashes are
in Document 79.

## 9. Fully required rerun

The fourth exploratory call used the schema requiring all five abstention
fields. It produced a valid `APPLICATION_SOURCE` abstention with
`application_source_not_established = true`. The provider accepted it and the
runner returned `RUN_READY_FOR_REVIEW`; contract and validation produced no
errors. It remains unapproved and unscored. Details and hashes are in Document
79.

After that acceptance, the contract was tightened to require artifact hashes for
reproduction and PASS executions. Revalidating the fourth result now fails with
`missing_execution_artifact` for its `REPRODUCTION_BEFORE` record. The result is
historical, not a current accepted result.

## 10. Fresh 4B and 9B comparison

A fresh 4B run still emitted an unrecorded `REPRODUCTION_BEFORE` and was
rejected with `missing_execution_artifact`. The 9B model, run on the same packet,
emitted a valid `APPLICATION_SOURCE` abstention, `OBSERVATION` and
`HARNESS_CAUSE` claims, and no test executions. The provider accepted it and the
runner returned `RUN_READY_FOR_REVIEW` with no validation issues. It remains
unapproved and unscored. Details and hashes are in Document 79; current result
path is `data/bdb5_handoff/bdb5_r2_live6_result.json`.
