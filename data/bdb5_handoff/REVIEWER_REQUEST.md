# Independent review request

I need two independent reviewers for the prepared BDB-5 R1/R2/R3 packets.
This is a packet-boundary review only; you do not need to run a model or open
the evaluator label vault.

Please read `REVIEW_HANDOFF.md` and the three prepared JSON files in this
folder. Confirm the checklist. If you use a terminal, run the read-only review
command for each case. If you don't, read `HOW_TO_APPROVE_SIMPLE.md` and reply
PASS/FAIL; the owner or agent can run the automated checks.

```bash
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r1_prepared.json"
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r2_prepared.json"
python scripts/bdb5_review_prepared.py --prepared "data/bdb5_handoff/bdb5_r3_prepared.json"
```

Expected for each case: `"status":"REVIEW_PASSED"`, `"issues":[]`, and
`"model_calls":0`.

Reply with:

- a reviewer ID (pseudonymous is fine, but it must identify you);
- confirmation that you reviewed each packet independently;
- an attestation that you have no conflict of interest;
- any checklist failure.

Do not send a sign-off unless you actually performed the review. The recorder
will copy one agreed attestation text into both sign-offs, so both reviewers
must approve the exact wording before it is recorded.
