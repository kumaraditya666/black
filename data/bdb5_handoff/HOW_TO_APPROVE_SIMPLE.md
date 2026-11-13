# How to approve — plain English

You do **not** need to code. I can run every command. Approval only needs two
real people to read the review packet and confirm it is clean.

## What approval means

Approval means two people checked that the task given to the AI does not
accidentally contain the answer, the fix, a hidden test, a label, or a local
file path.

It is a review of the **packet**, not a vote on whether the AI was right.

## What you need

- About 10–15 minutes per person.
- Two real people. You can be one of them.
- The second person can be a friend, coworker, or classmate.
- No coding and no model run.

The same two people can review all three cases: R1, R2 and R3.

## Step 1 — Pick two people

- Reviewer A: you, if you are willing to read the checklist.
- Reviewer B: one other real person.

Use a name or nickname for each reviewer ID. The ID must identify the actual
person who did the review; it can be pseudonymous.

Do not use me as a reviewer. Do not use two names for the same person. Do not
give me names of people who did not actually read the packet.

If you cannot find a second real person, the cases stay unapproved. That is the
honest outcome; I will not invent a reviewer.

## Step 2 — Both people read the review handoff

Open this file:

`data/bdb5_handoff/REVIEW_HANDOFF.md`

Read sections 1–3. For each case, confirm:

- [ ] The case ID is correct: R1, R2 or R3.
- [ ] The model-visible packet does not contain the answer, the fix commit, a
      hidden test name, a label, a rubric, or an expected answer.
- [ ] The packet does not contain a local username, a Windows path, or a
      temporary folder path.
- [ ] The evidence is enough to investigate the task without the answer key.
- [ ] R1 has a source frame and pinned revision.
- [ ] R2 shows only CI/test-harness evidence and does not claim an application
      source cause.
- [ ] R3 has the Django issue and the pinned `django/http/response.py` source.
- [ ] The reviewer has no conflict of interest with the case or its labels.
- [ ] The exploratory R2 result was not used as approval evidence and was not
      scored before approval.

If everything passes, the reviewer says **PASS** for that case. If anything
fails, the reviewer says **FAIL** and names the case and the problem.

You do not have to run the Python commands. I can run the automated boundary
check after you tell me the human review is done.

## Step 3 — Each person replies

Ask each reviewer to send a short reply like:

> I reviewed R1, R2 and R3 independently. I found no label leakage, answer
> leakage, hidden test, local path, or other boundary problem. I have no
> conflict of interest.

They can also reply per case:

> R1: PASS. R2: PASS. R3: PASS. Reviewed independently; no conflict.

If a reviewer says FAIL, stop. Do not record approval for that case.

## Step 4 — Agree on one sentence

The recorder copies one sentence into both sign-offs. Both reviewers must agree
to the exact sentence before I record it.

Example:

> We independently reviewed the R1, R2 and R3 packets, found no label leakage or
> boundary violation, and have no conflict of interest.

Both people must approve that wording. Do not write it for someone who has not
agreed to it.

## Step 5 — Send me four things

Send me:

1. Reviewer A ID:
2. Reviewer B ID:
3. The exact agreed sentence:
4. Confirmation that both people actually read the packet and said PASS.

That is all I need. I will run the recorder for R1, R2 and R3 and save the
approval files under:

`data/bdb5_handoff/approvals/`

## Step 6 — What I do next

I will:

- run the approval recorder for each case;
- save `BDB5-R1-approval.json`, `BDB5-R2-approval.json` and
  `BDB5-R3-approval.json`;
- verify the two reviewer IDs, both attestations, and the packet hashes;
- score R1, R2 and R3 only after their approval records exist.

Approval does **not** unblock T1 or P1. Those are separate engineering blockers.

## Copy-paste message for the second reviewer

> Hi — can you spend about 10 minutes reviewing three AI benchmark packets? You
> don’t need to code. Open `data/bdb5_handoff/REVIEW_HANDOFF.md`, read sections
> 1–3, and tell me PASS or FAIL for R1, R2 and R3. The main check is that the
> packet does not contain the answer, the fix, a hidden test, a label, or a local
> file path. If you’re willing, also confirm you have no conflict of interest.
> Thank you.

## The short version

1. You and one other real person read the checklist.
2. Both say PASS for R1, R2 and R3.
3. Both agree to one sentence.
4. Send me the two IDs and the sentence.
5. I record the approvals and verify them.
