# BDB-5 Human Approval Plan

**Status:** `APPROVAL_DEFERRED`

This is the owner-facing procedure for recording independent human approval for
the prepared R1, R2 and R3 packets. Reviewers should use
`REVIEWER_REQUEST.md` and `REVIEW_HANDOFF.md`.

The agent cannot perform this review. Do not invent reviewer identities,
attestations or sign-offs. If two real people cannot review, the cases remain
unapproved.

## 0. What is being approved

This is **packet approval**, not model-result approval.

Each case approval binds:

- the prepared packet hash;
- the evaluator-only manifest hash;
- the evaluator-only label-vault hash;
- two named reviewers and their attestations.

Approval does not score a model, prove a diagnosis, or make an exploratory
result a benchmark result.

The same two people may review all three cases, but each case needs its own
approval record.

## 1. Preconditions

Confirm these before starting:

- [ ] `data/bdb5_handoff/` exists and its `HANDOFF_MANIFEST.json` hashes match.
- [ ] R1, R2 and R3 are `PREPARED`.
- [ ] No approval file exists under `data/bdb5_handoff/approvals/` except
      `README.md`.
- [ ] `LIVE_INFERENCE_ENABLED` is `False`; this procedure makes no model calls.
- [ ] The R1/R2/R3 exploratory results are contract-valid, unapproved and unscored.

Quick integrity check:

```bash
python - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('data/bdb5_handoff')
manifest = json.loads((root / 'HANDOFF_MANIFEST.json').read_text(encoding='utf-8'))
for item in manifest['files']:
    actual = hashlib.sha256((root / item['path']).read_bytes()).hexdigest()
    assert actual == item['sha256'], item['path']
print('handoff hashes: PASS')
PY
```

## 2. Choose two real reviewers

You need exactly two distinct people:

- one `PRIMARY` reviewer;
- one `SECONDARY` reviewer.

The recorder assigns the first `--reviewer` as PRIMARY and the second as
SECONDARY.

Rules:

- Reviewer IDs may be pseudonymous, but they must identify actual people.
- Do not use the agent, an LLM, or a fabricated identity as a reviewer.
- Do not use the same person twice under two IDs.
- The owner may be one reviewer only if they actually perform the review.
- Each reviewer must attest independence and no conflict of interest.
- Reviewers should not open the evaluator label vault.

If you can review the packets yourself, you are the PRIMARY. You still need one
other real person for SECONDARY.

## 3. Send the review package

Send both reviewers:

- `data/bdb5_handoff/REVIEWER_REQUEST.md`
- `data/bdb5_handoff/REVIEW_HANDOFF.md`
- `data/bdb5_handoff/bdb5_r1_prepared.json`
- `data/bdb5_handoff/bdb5_r2_prepared.json`
- `data/bdb5_handoff/bdb5_r3_prepared.json`
- `data/bdb5_handoff/HANDOFF_MANIFEST.json`

Do not send the label vault. Do not ask reviewers to run a model.

If the reviewers are remote, send the whole `data/bdb5_handoff/` folder and
verify the manifest hashes after transfer.

## 4. Reviewers inspect the packets

Each reviewer independently reads:

- `model_visible_packet` in each prepared JSON;
- `evaluator_only.manifest` in each prepared JSON;
- the pinned source or CI evidence named by the packet.

For each case, they confirm:

- [ ] Case ID matches in packet and manifest.
- [ ] No gold patch, fix commit, hidden test, expected answer, rubric or label
      appears in the model-visible packet.
- [ ] No host path, temporary directory or local username appears.
- [ ] The manifest is `PREPARED`, not synthetic and not approved.
- [ ] The evidence is sufficient to investigate the stated task.
- [ ] R1 source frame and pinned revision are consistent.
- [ ] R2 exposes only CI/test-harness evidence and does not assert an
      application-source cause.
- [ ] R3 issue and pinned Django source are consistent.
- [ ] The read-only review reports `REVIEW_PASSED`.
- [ ] The reviewer has no conflict of interest.

Run the automated boundary check:

```bash
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r1_prepared.json"
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r2_prepared.json"
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r3_prepared.json"
```

Expected for each:

```text
"status":"REVIEW_PASSED"
"issues":[]
"model_calls":0
```

The automated check is not a human review. It only verifies the packet boundary.
If any checklist item fails, stop and record the issue; do not approve that case.

## 5. Agree on the attestation text

Each reviewer must provide a genuine attestation. The current recorder copies
one attestation string into both sign-offs, so both reviewers must approve the
exact same text before it is recorded.

Example text:

> I independently reviewed the R1 packet and manifest against the checklist,
> found no label leakage or boundary violation, and have no conflict of interest.

Requirements:

- reviewer ID: at least 3 characters;
- attestation: at least 20 characters;
- both `--attest-independent` and `--attest-conflict-free` are required.

Do not write an attestation on someone else's behalf without their explicit
approval of that exact wording.

## 6. Record the three approvals

Run one command per case. Keep the approval files in the handoff package:

```bash
python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r1_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<ATTESTATION_BOTH_APPROVE>" \
  --attest-independent \
  --attest-conflict-free \
  --output "data/bdb5_handoff/approvals/BDB5-R1-approval.json"

python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<ATTESTATION_BOTH_APPROVE>" \
  --attest-independent \
  --attest-conflict-free \
  --output "data/bdb5_handoff/approvals/BDB5-R2-approval.json"

python scripts/bdb5_record_approval.py \
  --prepared "data/bdb5_handoff/bdb5_r3_prepared.json" \
  --reviewer "<REVIEWER_A_ID>" \
  --reviewer "<REVIEWER_B_ID>" \
  --attestation "<ATTESTATION_BOTH_APPROVE>" \
  --attest-independent \
  --attest-conflict-free \
  --output "data/bdb5_handoff/approvals/BDB5-R3-approval.json"
```

Each successful command prints:

```text
"status":"APPROVAL_RECORDED"
"case_id":"BDB5-R1"   # or R2/R3
"approval_hash":"<64 hex characters>"
"reviewers":["<ID_A>","<ID_B>"]
"model_calls":0
```

If a command prints `APPROVAL_REJECTED`, read the error and fix the input. Do not
edit an approval JSON by hand.

## 7. Verify the approvals

List the records:

```bash
ls -1 data/bdb5_handoff/approvals/
```

Inspect one record:

```bash
python - <<'PY'
from pathlib import Path
from blackbox.bdb5.approval import load_approval
approval = load_approval(Path('data/bdb5_handoff/approvals/BDB5-R2-approval.json'))
print(approval.model_dump_json(indent=2))
PY
```

Confirm:

- [ ] Two distinct reviewer IDs.
- [ ] One `PRIMARY` and one `SECONDARY`.
- [ ] Both reviewers are marked independent and conflict-free.
- [ ] Attestation is genuine and at least 20 characters.
- [ ] Approval hash is present.
- [ ] Approval is bound to the R2 packet, R2 manifest, and label vault.
- [ ] `approved_at` is not before either review time.

If a packet or manifest changes, the approval becomes stale. Re-review the new
packet; do not patch the old approval.

## 8. Score only after approval

R1, R2 and R3 now have current contract-valid exploratory results, but scoring
still requires an approval record for each case.

For R2:

```bash
python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r2_prepared.json" \
  --result "data/bdb5_handoff/bdb5_r2_live6_result.json" \
  --approval "data/bdb5_handoff/approvals/BDB5-R2-approval.json"
```

Expected output includes:

```text
"mode":"REAL_CASE_EVALUATION"
"result_class":"REAL_CASE_SCORE_NOT_BENCHMARK_RESULT"
"approved":true
"scored":true
"provider_calls":0
```

Do not score before the approval exists. Do not call an exploratory result a
benchmark result.

For R1 and R3, use their exploratory results:

```bash
python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r1_prepared.json" \
  --result "data/bdb5_exploratory/bdb5_r1_exploratory_result.json" \
  --approval "data/bdb5_handoff/approvals/BDB5-R1-approval.json"

python scripts/bdb5_score_prepared.py \
  --prepared "data/bdb5_handoff/bdb5_r3_prepared.json" \
  --result "data/bdb5_exploratory/bdb5_r3_exploratory_result.json" \
  --approval "data/bdb5_handoff/approvals/BDB5-R3-approval.json"
```

## 9. Record the outcome

After scoring:

- save the score, result and approval paths;
- update the status matrix;
- keep the result class as `REAL_CASE_SCORE_NOT_BENCHMARK_RESULT`;
- do not claim an aggregate BDB-5 benchmark.

R1 and R3 now have current contract-valid results, but still need approval before
scoring. R2 may still fail a strict dimension; that is a score outcome, not an
approval failure.

## 10. Failure handling

| Symptom | Correct action |
|---|---|
| `APPROVAL_REJECTED: exactly two distinct --reviewer IDs are required` | Use two different real reviewers. |
| `both independence and conflict-free attestations are required` | Both reviewers must explicitly agree; add both flags. |
| `reviewer_id` or `attestation` length error | Meet the minimum lengths; do not bypass. |
| `approval requires a passing packet review` | Fix the packet issue or stop; do not approve. |
| Stale packet/manifest/vault hash | Re-review the new packet; do not reuse the old approval. |
| No second real reviewer | Leave the case unapproved. Automated or invented approval is invalid. |
| Approval exists but result absent | Approval is still valid; produce a contract-valid result later. |
| Score fails | Check the approval, result contract, and packet hashes; do not weaken the scorer. |

## 11. Minimum completion checklist

- [ ] Two real, distinct reviewers selected.
- [ ] Both reviewed all three packets independently.
- [ ] Both approved the exact attestation text.
- [ ] Three approval JSON files exist with approval hashes.
- [ ] Approval records pass `load_approval`.
- [ ] R1/R2/R3 results are contract-valid.
- [ ] Each case is scored only after its approval exists.
- [ ] No claim of aggregate benchmark completion.
