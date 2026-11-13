# BDB-5 R1/R2/R3 Independent Review Handoff

**Date:** 2026-11-10

**Status:** `AWAITING_TWO_REAL_REVIEWERS — R1_R2_R3_EXPLORATORY — NOT_APPROVED`

## 1. Why this handoff exists

The code can record a two-reviewer approval, but it cannot make a reviewer
independent. No approval record has been created for R1, R2 or R3, and none will
be created with invented identities.

Two real people must each:

1. read the model-visible packet and evaluator manifest;
2. confirm the boundary and evidence checks below;
3. provide a reviewer ID, an independence attestation and a conflict-free
   attestation.

The reviewer IDs may be pseudonymous, but they must identify the actual people
who performed the review. They must not be the agent or a fabricated name.

## 2. Case bindings

The prepared payloads are in the durable handoff folder
`data/bdb5_handoff/`. The hashes below bind an approval to the exact content.

| Case | Prepared payload | Payload SHA-256 | Packet SHA-256 | Manifest SHA-256 | Readiness |
|---|---|---|---|---|---|
| `BDB5-R1` | `data/bdb5_handoff/bdb5_r1_prepared.json` | `0e940779081d1fda071f4acec3c2847227a7480056bc46d1d4d897c3806b6c8c` | `668c64cd4361ba1c6f2efe0095aff8fe6de55963ec3b63f700ca407fd93620ce` | `63c797f6c5aaf95cd66117f7b4ee44beb3a91701cd797dd667a677aa150dd2fd` | `PREPARED` |
| `BDB5-R2` | `data/bdb5_handoff/bdb5_r2_prepared.json` | `5b72f085d22f9ae0d38ffde44142e6b5e6206d1e640cc5b62d386f715f82b735` | `a3657e6cb3b23540ec21eb643de8e8ac658280c67fc36fbd7e07aacf0b92b1d1` | `0862f96db453778d53f2cdcb31419e9a3cb548573cff22054b1da38c767ffb23` | `PREPARED` |
| `BDB5-R3` | `data/bdb5_handoff/bdb5_r3_prepared.json` | `041ba6157049aa3df9d78a1cd83d0eb168e94e71a8afaa04b7f614da5c50e37f` | `c3123dfe63ca88a41cd756d3b1ea1d0b94d2ac3b7c8a0fc28955f9c5f33a42c3` | `46930d769995e2a20c354621f282163c7e31228b81e9fa2233eadec95e462a05` | `PREPARED` |

Label vault binding: `bc01e4d46d7d2f8723dea7a774ed3a40d49f5c8d65f0f06acb8c9a8b2f1510a7`.

The vault is evaluator-only. Reviewers do not need to open it and should not
use it to judge whether the packet is answerable.

## 3. Reviewer checklist

For each case, review only:

- `model_visible_packet` in the prepared JSON;
- `evaluator_only.manifest` in the prepared JSON;
- the pinned source or CI evidence named by the packet.

Confirm:

- [ ] The case ID in the packet and manifest matches the case being reviewed.
- [ ] The packet contains no gold patch, fix commit, hidden test name, expected
      answer, rubric, label or evaluator-only field.
- [ ] The packet contains no host path, temporary directory or local username.
- [ ] The manifest marks the case `PREPARED`, not synthetic and not approved.
- [ ] The evidence is sufficient to investigate the stated task without the
      evaluator truth.
- [ ] For R1, the source frame and pinned revision are present and consistent.
- [ ] For R2, the packet correctly exposes only the CI/test-harness evidence and
      does not include application source as a claimed cause.
- [ ] For R3, the Django issue and pinned `django/http/response.py` source are
      present and consistent.
- [ ] Running the read-only review reports `REVIEW_PASSED` with no issues.
- [ ] The exploratory R2 result in section 7 was not treated as approval
      evidence and was not scored before approval.
- [ ] The reviewer has no conflict of interest with the case, its labels or this
      evaluation.

If any item fails, do not approve that case. Record the issue instead.

Run the automated boundary check for each case:

```bash
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r1_prepared.json"
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r2_prepared.json"
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r3_prepared.json"
```

Expected: `"status":"REVIEW_PASSED"`, `"issues":[]`, `"model_calls":0`.

## 4. Recording the sign-offs

Each case needs exactly two distinct reviewers: one `PRIMARY` and one
`SECONDARY`. The CLI assigns the first `--reviewer` as `PRIMARY` and the second
as `SECONDARY`.

Use reviewer IDs and an attestation that the reviewers themselves approve. For
example, the attestation may say:

> I independently reviewed the R1 packet and manifest against the checklist,
> found no label leakage or boundary violation, and have no conflict of interest.

The same attestation text is copied into both sign-offs by the current CLI, so
it must be acceptable to both reviewers. Record each case separately:

```bash
python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r1_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<REVIEWER_A_AND_B_ATTESTATION>" \
  --attest-independent \
  --attest-conflict-free

python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<REVIEWER_A_AND_B_ATTESTATION>" \
  --attest-independent \
  --attest-conflict-free

python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r3_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<REVIEWER_A_AND_B_ATTESTATION>" \
  --attest-independent \
  --attest-conflict-free
```

The recorder defaults to `%TEMP%\bdb5_approvals\`. For this handoff, pass
`--output "data/bdb5_handoff/approvals/BDB5-R1-approval.json"` (or the matching
case) so the record stays with the package. Approval files are not committed.
The command prints `APPROVAL_RECORDED` and the approval hash.

An approval is bound to the packet hash, manifest hash and label-vault hash. If
any of those change, the approval is rejected as stale.

## 5. What approval does and does not establish

Approval establishes that two named people attested to the boundary review. It
does not:

- score a model result;
- establish that a model is correct;
- convert the exploratory R2 output into a benchmark result;
- unblock T1 or P1.

After approval, a result can be scored with:

```bash
python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --result "<RESULT_JSON>" \
  --approval "<APPROVAL_JSON>"
```

The scorer makes no provider call and emits
`REAL_CASE_SCORE_NOT_BENCHMARK_RESULT`.

## 6. Current state

- R1, R2 and R3: `PREPARED`.
- Technical packet review: `REVIEW_PASSED` for all three.
- Independent human approval: **not recorded**.
- Real approved model result: **none**.
- Exploratory model output: the R2 9B, R1 9B and R3 9B results are
  contract-valid and accepted for review. R1 and R3 abstained and made no
  predictions. All remain unapproved and unscored.
- The prior R2 4B result is historical and rejected by the artifact rule.
  Documents 77 and 79.
- Repository `LIVE_INFERENCE_ENABLED`: `False`.

## 7. Prior exploratory R2 result (historical; not approval evidence)

The fourth exploratory call produced a structured application-source
abstention. It was accepted before the execution-artifact rule was added. It is
now kept only as a historical record; it is not a current accepted result, not
a sign-off and not a reason to approve R2.

| Property | Value |
|---|---|
| Case | `BDB5-R2` |
| Model | `qwen3.5:4b` via native Ollama |
| Provider calls | `1` |
| Provider outcome (historical) | `PROVIDER_ACCEPTED` |
| Contract (historical) | passed, no codes |
| Current contract | **rejected**, `missing_execution_artifact` |
| Runner status (historical) | `RUN_READY_FOR_REVIEW` |
| Validation issues | none |
| Request hash | `b0bf2ee143f78516caf545bdaa5f760e8dfa57da5f4950a62e16e2a5f03fe59c` |
| Response hash | `73a7688c45020cdb14fa0622b30902603b3e702046e82000031ac5c643bd786f` |
| Result hash | `5198f8c74b3d137d5f883f22a4320dd4319480a84cc0f4c4e98666017a05a426` |
| Record | `data/bdb5_handoff/historical/bdb5_r2_live4_record.json` |
| Standalone result | `data/bdb5_handoff/historical/bdb5_r2_live4_result.json` |

The result contains `l2_causal_status = NOT_ESTABLISHED` and an
`APPLICATION_SOURCE` abstention with `application_source_not_established`
true. It also contains a `REPRODUCTION_BEFORE` execution with no artifact hash,
so the current provider contract rejects it with
`missing_execution_artifact`. Do not score it as a current accepted result.

After approval, score a result that satisfies the current contract with:

```bash
python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --result "<CURRENT_CONTRACT_VALID_RESULT_JSON>" \
  --approval "<APPROVAL_JSON>"
```

## 8. Current exploratory R2 result (9B; not approval evidence)

The 9B comparison used the same packet and current contract.

| Property | Value |
|---|---|
| Case | `BDB5-R2` |
| Model | `qwen3.5:9b-q4_K_M` via native Ollama |
| Provider calls | `1` |
| Provider outcome | `PROVIDER_ACCEPTED` |
| Contract | passed, no codes |
| Runner status | `RUN_READY_FOR_REVIEW` |
| Validation issues | none |
| Request hash | `9c4a55ade43ae64e88fcb83a3dcf6533b4b098af87d18e6f9a040248d51a739d` |
| Response hash | `0c810422207debdf2ea79e80d826f52daa3931d5434cc1401999e98cfcbb64fd` |
| Result hash | `2658e475d5388778803a399cc188aae0ee177de75260ebf0723bf5b265166fde` |
| Record | `data/bdb5_handoff/bdb5_r2_live6_record.json` |
| Standalone result | `data/bdb5_handoff/bdb5_r2_live6_result.json` |

The result contains `l2_causal_status = NOT_ESTABLISHED`, an
`APPLICATION_SOURCE` abstention with `application_source_not_established`
true, `OBSERVATION` and `HARNESS_CAUSE` claims, and no test executions. It is
unapproved and unscored. After approval it can be scored with:

```bash
python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --result "data/bdb5_handoff/bdb5_r2_live6_result.json" \
  --approval "<APPROVAL_JSON>"
```

## 9. Current exploratory R1/R3 results (not approval evidence)

These are 9B exploratory outputs. They are contract-valid, unapproved and
unscored, and they are not approval evidence.

| Case | Result | Result hash | Record |
|---|---|---|---|
| `BDB5-R1` | `RUN_READY_FOR_REVIEW`; `NOT_ESTABLISHED`; `APPLICATION_SOURCE` abstention | `79d8c7ab0b9419bcd817b27587f59ce3a70606a7246142c0b262b469a6d1cbce` | `data/bdb5_exploratory/bdb5_r1_exploratory_record.json` |
| `BDB5-R3` | `RUN_READY_FOR_REVIEW`; `NOT_ESTABLISHED`; `APPLICATION_SOURCE` abstention | `e96496ca04f82fe280f3ec5eb1fc4c1eabb3c2988bee6ce0e373dce8d616c183` | `data/bdb5_exploratory/bdb5_r3_exploratory_record.json` |

Both outputs contain observations only and no predicted file, function, line or
fault class. Neither records a test execution or patch. The detailed summary is
`data/bdb5_exploratory/README.md`. Do not score these before the matching
approval exists.
