# BDB-5 Independent Review Handoff

**Status:** `APPROVAL_DEFERRED — R1_R2_R3_CONTRACT_VALID — NOT_APPROVED — NOT_SCORED`

This folder is the durable copy of the prepared R1/R2/R3 packets and the
current exploratory R2 result, with pointers to the R1/R3 exploratory results.
It contains no approval record and no score.

## Files

| File | SHA-256 |
|---|---|
| `bdb5_r1_prepared.json` | `0e940779081d1fda071f4acec3c2847227a7480056bc46d1d4d897c3806b6c8c` |
| `bdb5_r2_prepared.json` | `5b72f085d22f9ae0d38ffde44142e6b5e6206d1e640cc5b62d386f715f82b735` |
| `bdb5_r3_prepared.json` | `041ba6157049aa3df9d78a1cd83d0eb168e94e71a8afaa04b7f614da5c50e37f` |
| `bdb5_r2_live6_result.json` | `2658e475d5388778803a399cc188aae0ee177de75260ebf0723bf5b265166fde` |

The current R2 result was produced by `qwen3.5:9b-q4_K_M` and accepted by the
provider contract. It is unapproved and unscored. The historical 4B records are
in `historical/`; they are rejected by the current execution-artifact rule.

The R1 and R3 exploratory 9B results are in `data/bdb5_exploratory/` (see its
`README.md`). They are contract-valid, unapproved and unscored. They are not
approval evidence.

## Review and approval

For the full owner-facing procedure, read `APPROVAL_PLAN.md`.

For a plain-English version that does not require coding, read
`HOW_TO_APPROVE_SIMPLE.md`.

Read `REVIEW_HANDOFF.md` and follow its checklist. Reviewers do not need the
label vault and should not run a model. Record two real sign-offs only after
both reviewers have reviewed independently:

```bash
python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r1_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<ATTESTATION_BOTH_APPROVE>" \
  --attest-independent \
  --attest-conflict-free \
  --output "data/bdb5_handoff/approvals/BDB5-R1-approval.json"
```

Repeat for R2 and R3. After approval, score each case with its matching
result. For R2:

```bash
python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --result "data/bdb5_handoff/bdb5_r2_live6_result.json" \
  --approval "data/bdb5_handoff/approvals/BDB5-R2-approval.json"
```

No approval exists yet. Do not score before the two real reviewers sign.
