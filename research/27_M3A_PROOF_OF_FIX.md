# Milestone 3A — restricted Proof-of-Fix engine

Date: 2026-11-04. Local Windows machine, Python 3.14, `qwen3.5:4b` through Ollama, 2,048-token context, thinking off, temperature 0. Fixture revision `a7ee4fe747c6b1cf051412801194ec2693598420`. The investigation and repair code from Milestone 2.9.1 was preserved; its checkpoint is commit `ba797ed`.

Artifacts: `data/milestone3a-run.json`, `data/m3a-evaluation-20261104T190816Z.db`, `fixtures/repair/`, `scripts/evaluate_m3a.py`, `scripts/repair_cli.py`, `tests/test_repair.py`.

## 1. What this milestone is

A local, developer-operated workflow that turns an approved investigation hypothesis into a proposed source change, applies it only inside a disposable copy of a pinned trusted fixture, and reports what actually happened when the same reproduction test and a regression suite ran. It does not merge, push, open a pull request, deploy, or grant autonomous repair permission.

The claim this milestone supports is narrow:

> For these five pinned fixtures, with this model and these tests, three proposed patches were independently executed and passed both the reproduction test and the regression suite in a disposable workspace.

It does **not** claim that the patches are semantically correct beyond those tests, that the model diagnoses arbitrary repositories, or that the process is safe for untrusted code.

## 2. Preserved baseline

Before any change, the working tree was inspected. Milestone 2.9.1 was already committed at `ba797ed`; only generated `graphify-out/cache` files were dirty. The existing suite passed 70 tests. No application code was recreated and the incident/investigation schema and endpoints are unchanged.

The project now runs **83 tests: 83 passed**, one Starlette test-client deprecation warning. Thirteen of them are the new repair tests. The five fixture repositories are excluded from project test discovery by `pytest.ini`; their own suites are executed only inside temporary copies.

## 3. Eligibility gate

`blackbox/repair/eligibility.py` re-reads persisted state and refuses repair unless every one of these checks passes:

1. the investigation exists;
2. its status is `completed`;
3. its outcome is `LIKELY_CAUSE`;
4. every evidence reference in the stored findings resolves in the stored snapshot;
5. the observed failure cites the recorded event;
6. a cited source frame is resolved at the recorded revision;
7. the cited frame is in the fixture's allowed patch files;
8. the cited frame matches the registered fixture failure location;
9. the recorded Git revision exists;
10. every fixture file matches its registry content hash;
11. the repository is this project's trusted fixture repository;
12. a review record matches the exact hypothesis hash and the exact evidence hash.

`INVESTIGATION_FAILED`, `INSUFFICIENT_EVIDENCE`, missing revisions, unresolved frames, invalid references, unknown fixtures, untrusted repositories and missing/stale approvals are hard blocks. The model's confidence is never read; no confidence field exists in the patch prompt or gate.

Changing the hypothesis text, the evidence snapshot or the evidence hash invalidates an approval because all three are part of the match. The approval API stores a reviewer and optional note; re-approving the same unchanged hypothesis is idempotent.

## 4. Patch generator

`blackbox/repair/patch.py` sends only:

- the recorded exception and revision;
- the human-approved hypothesis and its supporting evidence IDs;
- the relevant resolved frame and a bounded set of deterministic claims;
- the pinned source of the allowed files;
- the trusted reproduction test;
- the fixture's expected behaviour and fixed constraints.

The model receives no tools, no shell, no repository write access and no arbitrary command channel. It must return `PatchProposal`: a summary, one to three `{path, find, replace, explanation}` changes, and up to three risks. The JSON schema is used for constrained decoding and validation; list and text sizes are bounded.

Validation happens before anything is written:

- only paths in `allowed_files` are accepted; traversal, absolute paths and test-file edits are rejected;
- `find` must occur exactly once;
- `find` and `replace` must differ and be bounded in size;
- added lines are scanned for process, network, dynamic-code and similar constructs;
- the resulting file must parse as Python;
- the rendered diff is bounded.

A rejected proposal is recorded as `PATCH_REJECTED`; no file is written. No model-proposed command is ever executed. The live fixture repository is never modified: files are read with `git show` and written only to a temporary directory.

## 5. Reproduction and isolation

Before generation, the pipeline materializes the exact recorded revision into a temporary directory and runs the predetermined reproduction test from the fixture registry. The bug counts as reproduced only when the process exits with test failures and the recorded failure signature appears. A passing reproduction stops the pipeline as `UNVERIFIED` before the model is called.

After a validated patch, the same test runs in a fresh temporary copy, followed by the fixture's regression suite.

Isolation detection found no Docker binary (`docker: command not found`), so the evaluation ran in **process-jail mode**:

- temporary working directory;
- sanitized environment allowlist (no `BLACKBOX_*`, provider keys, cloud tokens or unrelated credentials);
- Python-level socket blocking and disabled third-party pytest plugin autoloading;
- 60-second default test timeout;
- no shell, no network command, no repository write.

This is **not OS-level confinement**. It does not stop native code, direct syscalls, arbitrary filesystem access outside the temporary directory, or CPU/memory exhaustion beyond the wall-clock timeout. A Docker path exists with `--network none`, a read-only root, dropped capabilities, memory/CPU/PID limits and a configurable image, but it was not exercised because Docker is unavailable and no image was configured. Because adequate isolation is unavailable, the pipeline accepts only the pinned trusted fixtures in this repository and **general-purpose repair execution is blocked**. That is a deliberate restriction, not a claim of sandbox security.

## 6. Verification semantics

The only inputs to verification are process exit codes, the recorded revision, and the pinned file contents:

| Status | Meaning |
|---|---|
| `VERIFIED_IN_TEST_ENVIRONMENT` | reproduction failed before, passed after, regression passed, patch applied, revision pinned |
| `PATCH_FAILED` | patch applied but the reproduction or regression suite still fails |
| `UNVERIFIED` | the bug was not reproduced, or the failure did not match the recorded signature |
| `ENVIRONMENT_FAILED` | the disposable environment, timeout or runner failed |
| `PATCH_REJECTED` | the proposal violated path, size, safety or applicability rules |
| `GENERATION_FAILED` | no valid structured proposal was produced |
| `ELIGIBILITY_BLOCKED` | at least one gate check failed; the model was not called |

`VERIFIED_IN_TEST_ENVIRONMENT` means exactly that. It is not production success, semantic correctness, or proof that the test suite is adequate.

## 7. Review interface

`scripts/repair_cli.py` provides local commands:

```powershell
python scripts/repair_cli.py eligibility <investigation-id> --fixture division_by_zero
python scripts/repair_cli.py approve <investigation-id> --hypothesis 0 --reviewer <name>
python scripts/repair_cli.py attempt <investigation-id> --fixture division_by_zero
python scripts/repair_cli.py show <attempt-id>
python scripts/repair_cli.py review <attempt-id> --decision accept|reject --reviewer <name>
python scripts/repair_cli.py list
```

`approve` prints the hypothesis and its hash and refuses to record until the same hash is passed with `--confirm-hash`. `show` prints the original incident, approved hypothesis and its review record, proposed change, unified diff, reproduction-before output, reproduction-after output, regression output, status, timings, token usage, exact revision, risks and developer review. `review` records a decision but cannot alter the test-derived status.

The interface is deliberately local and terminal-only. No dashboard, PR automation, merge or deployment was built.

## 8. Evaluation design

Five pinned fixtures live in `fixtures/repair/`, each with a reproduction test and a regression suite:

| Fixture | Failure | Intended fix |
|---|---|---|
| `division_by_zero` | averaging `[]` raises `ZeroDivisionError` | reject empty input |
| `argument_validation` | `parse_port(None)` leaks `TypeError` | reject every non-numeric argument as `ValueError` |
| `off_by_one` | `find_index` scans one past the list and raises `IndexError` | remove the extra range step |
| `missing_config` | absent timeout key raises `KeyError` | default to 30 while preserving explicit values |
| `unreproducible` | event claims a division error, but that revision already rejects empty input | none; the pipeline must stop as `UNVERIFIED` |

The first three and the control were expected to be diagnosable; `missing_config` was included to observe a conservative abstention. The deterministic tests additionally cover a patch that still fails the reproduction, a naive off-by-one patch that passes the reproduction but breaks regression, an edit to a test file, a forbidden construct, a mismatched `find`, missing approvals, failed/abstained investigations, missing revisions, unresolved frames, bad references, an untrusted repository, an unknown fixture and a stale approval. Those use mocked model responses and are labelled as deterministic integration evidence, not model accuracy.

The real evaluation ran the configured 4B model for investigation and patch generation on all five fixtures. Fixture-level approvals were recorded by the benchmark under reviewer `m3a-benchmark` with an explicit note. **Those approvals are a harness convenience, not evidence of human judgement.** The gate still requires a matching review record; production use requires a developer to run `approve` after reading the hypothesis.

## 9. Real-model results

Five live investigations completed. Four were `LIKELY_CAUSE` and passed the gate; one was `INSUFFICIENT_EVIDENCE` and was blocked before any patch generation.

| Fixture | Investigation | Gate | Attempt | Repro before | Repro after | Regression | Generation |
|---|---|---|---|---|---:|---:|---:|---:|
| division_by_zero | LIKELY_CAUSE | eligible | **VERIFIED** | rc 1 | rc 0 | rc 0 | 3.62 s |
| argument_validation | LIKELY_CAUSE | eligible | **VERIFIED** | rc 1 | rc 0 | rc 0 | 5.71 s |
| off_by_one | LIKELY_CAUSE | eligible | **VERIFIED** | rc 1 | rc 0 | rc 0 | 3.19 s |
| missing_config | INSUFFICIENT_EVIDENCE | blocked | not attempted | — | — | — | — |
| unreproducible | LIKELY_CAUSE | eligible | **UNVERIFIED** | rc 0 | not run | not run | not called |

Totals: **4 eligible, 4 attempted, 3 verified, 1 unverified, 0 patch failures, 0 invalid rejections, 0 environment failures, 0 generation failures**. Patch generation succeeded for **3 of 3** attempts that reached generation.

Measurement:

- investigation latency median **9.05 s** (7.58–9.68 s);
- repair pipeline **4.9–7.3 s** per verified case;
- end-to-end median **14.43 s**, maximum **17.14 s**;
- patch generation requests **3.62–5.71 s** wall time (Ollama evaluation **2.56–5.11 s**);
- patch prompt **1,326–1,381 input tokens**; proposals **139–278 output tokens**;
- local inference stayed on the same 2,048-token context and the same 4B model; no resource limit was raised.

### What the model proposed

The division patch added an empty-input guard and raised `ValueError`. The off-by-one patch removed `+ 1` from `range(len(items) + 1)`. Both are the intended minimal changes and passed both suites.

The argument patch added an explicit `if value is None: raise ValueError(...)` instead of broadening `except ValueError` to `except (TypeError, ValueError)`. It passes the reproduction test and the three regression tests, but it fixes only the observed `None` case rather than the class of non-numeric arguments. This is a real example of a patch that is verified by the available tests while remaining narrower than the expected behaviour. It must not be described as a general fix.

### The most important result

For `unreproducible`, the model returned `LIKELY_CAUSE` with the explanation "Division by zero caused by empty values list passed to average function" — at a revision where `average([])` already raises `ValueError`. The reproduction test passed before any patch, so the pipeline stopped at `UNVERIFIED` and never called the patch generator. This is the intended inversion of the product claim: the model thought there was a bug, and the recorded test evidence showed there was no reproducible failure.

## 10. Deterministic integration results

`tests/test_repair.py` contains 13 deterministic tests. They establish:

- a real verified run requires the same test to fail before and pass after, plus regression success;
- a patch that still fails the reproduction becomes `PATCH_FAILED`;
- a naive off-by-one patch passes the reproduction and is rejected by regression (`PATCH_FAILED`);
- an unreproducible bug becomes `UNVERIFIED` without calling the model;
- no approval, a stale evidence hash, a changed hypothesis and untrusted state are blocked;
- failed and abstained investigations are hard-blocked;
- path escapes, test edits, forbidden constructs and non-matching `find` strings are rejected before writing;
- the fixture repository is byte-for-byte untouched;
- review cannot change verification status;
- repair history and provenance are persisted.

Three unsafe/unapplicable proposals were rejected in the deterministic suite; zero were accepted. No real-model proposal was rejected in this run, so the live rejection rate is **not measured**.

## 11. What remains unverified

- **Test adequacy.** Passing the provided tests is not proof of correctness. The argument patch already demonstrates a narrow fix that satisfies them.
- **Generalisation.** Five tiny fixtures from one repository family, one model and one session are not a benchmark. The model abstained on `missing_config`; a different prompt or session might behave differently.
- **Session variability.** Milestone 2.9.1 observed `misleading_logs` change outcome across sessions on identical bytes. That issue is not solved here and remains visible in `research/26_M291_RELIABILITY_FIX.md`. Nothing in this milestone establishes stable diagnosis.
- **Evidence semantics.** Gate validity means references resolve; it does not prove that the hypothesis explains the failure.
- **Human review.** The benchmark approvals are fixture-level and automated; they are not evidence that a developer reviewed each hypothesis. The CLI supports deliberate hash-confirmed approval, but the benchmark did not exercise that human step.
- **Isolation.** The process jail is cooperative, not OS-level. No arbitrary repository was executed and none should be until real container isolation is verified.
- **Repair quality.** No patch was merged, deployed or reviewed by an independent human. No production behaviour was observed.
- **Scale.** The prior 2.9.1 result (42/42 on six synthetic scenarios plus two unseen controls) remains a limited synthetic result, not evidence of real-world diagnostic accuracy.

## 12. Is Milestone 3B justified?

**Conditionally yes, but only as a restricted continuation — not as a production repair system.**

The evidence supports continuing because the system can now do the thing the milestone set out to prove: it can take a reviewed hypothesis, generate a bounded patch, apply it in a disposable copy at a pinned revision, and produce a report showing the same test failing before and passing after, with regression output and no write to the source repository. It also correctly refused a model-claimed bug when the reproduction passed.

Milestone 3B should not begin unless it keeps these constraints:

1. real container isolation is implemented and verified before any repository outside `fixtures/repair` is executable;
2. fixtures remain trusted, pinned and hash-checked;
3. approvals remain explicit, hash-bound and human-owned; benchmark auto-approval must not become a production path;
4. hidden or held-out fixtures and independent adjudication are added before any repair-accuracy claim;
5. a passing test is never represented as production success, and no automatic merge, PR or deployment is added;
6. the unresolved 2.9.1 session variability and the limited synthetic base remain disclosed.

## 13. Not built

No final dashboard. No GitHub or other remote PR automation. No deployment. No autonomous repair permission. No merge. No production credentials or network execution. Milestone 3B was not started.
