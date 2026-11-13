# Codex handoff: repair evaluation

Date: 2026-11-05. Status: **PARTIALLY COMPLETE**. The restricted benchmark was run; Milestone 3B and general-purpose untrusted execution remain blocked pending validated OS-level isolation.

## Handoff and provenance

HEAD was `b96840fef85585904c9348e213dbbec9c0ca521a`. No staged or working-tree application changes were found. `graphify-out/cache/last_query_stamp` and `stat-index.json` were modified, and 89 graph cache files were untracked in the first status snapshot (the query itself may have updated cache). The checkpoint at `.backup/codex-handoff-20261105/` records HEAD, status, tracked diffs and copies of the two modified tracked cache files; untracked files remain in place. No source, database, or existing report was deleted. Existing Git history and these artifacts provide recovery; no unrelated work was committed.

Freebuff committed fixture corrections in `50fec42` and `a7ee4fe`, the repair implementation in `0f430d7`, and safety/report wording changes in `b96840f`. Contrary to the handoff's last visible progress, `research/27_M3A_PROOF_OF_FIX.md` and `data/milestone3a-run.json` record a completed earlier five-case live run at revision `a7ee4fe`: three test-verified patches, one investigation abstention, and one unreproducible control. That historical run is separate from the new one below. No Milestone 3B report was present.

## Baseline and environment

With the existing `.venv`, `python -m pytest -q` produced **83 passed, 1 warning, 0 skipped in 25.78 s**. `python -m pytest tests/test_repair.py -q` produced **13 passed in 16.36 s**. The warning is Starlette's test-client/httpx deprecation. `python -m compileall -q blackbox scripts tests` succeeded. No project lint or CI configuration was found. Tests were run concurrently, so timings are wall time under shared load.

Docker CLI 29.9.2 exists; `docker version` could not connect to the default daemon pipe. `wsl --status` reports WSL is not installed; Linux container support and the configured image could not be verified, and `BLACKBOX_REPAIR_DOCKER_IMAGE` was not set in the process environment. Container execution was not tested. The existing Docker command includes network disablement, read-only root, capability drops, no-new-privileges and resource limits, but does not explicitly specify a non-root user. Its security effectiveness is unvalidated. The trusted-fixture process jail is not OS-level confinement, and general untrusted repository execution remains blocked. Patch lexical filtering is not a sandbox or comprehensive security boundary.

## Independent fixture audit

At `b96840f`, `content_pinned` confirmed all registry file hashes at the Git revision. Each registered test was executed from materialized Git objects in a disposable process-jail workspace; outputs are in `data/codex-fixture-audit.json`. The original exception markers appeared in each positive case:

| Fixture | Trigger and observed original behavior | Expected behavior and regression checks |
|---|---|---|
| division_by_zero | `average([])` raises `ZeroDivisionError`; reproduction rc 1 | `ValueError` for empty input; normal and single-item averages preserved |
| argument_validation | `parse_port(None)` raises `TypeError`; reproduction rc 1 | `ValueError` for invalid inputs; tests cover None and invalid text, numeric string remains valid |
| off_by_one | absent item in `[1,2,3]` scans past the end and raises `IndexError`; reproduction rc 1 | return -1; first, last, and empty-list checks |
| missing_config | `request_timeout({})` raises `KeyError: 'timeout'`; reproduction rc 1 | default 30; explicit and zero timeout preserved |
| unreproducible | deliberately false recorded `ZeroDivisionError`: `average([])` already raises `ValueError`; reproduction rc 0 | negative control must stop as UNVERIFIED, not be treated as a genuine reproducible incident |

The intentionally false control is valid as a negative test, not as a positive incident. The checks establish these specific inputs, not comprehensive semantics. No fixture was changed during this handoff.

## Fresh live run

Command, from the project root, after setting `BLACKBOX_AI_PROVIDER=ollama`, `BLACKBOX_AI_MODEL=qwen3.5:4b`, `BLACKBOX_OLLAMA_CONTEXT_LENGTH=2048`, and `BLACKBOX_OLLAMA_TIMEOUT_SECONDS=120`:

```
.venv\Scripts\python.exe scripts/evaluate_m3a.py --approve-all --output data/milestone3a-codex-handoff.json
```

Evidence, including proposed diffs, output, token counts, timings, gate results, and source revision, is in `data/milestone3a-codex-handoff.json` and `data/m3a-evaluation-20261105T152215Z.db`. The database is gitignored and must be retained. The script creates a new database and uses HEAD, so reproduce from this revision with matching hashes, installed model and same configuration. `--approve-all` records labelled fixture-level benchmark approvals bound to the evidence and hypothesis; it is **not** human review or production authorization. No patch was manually substituted. `temperature=0`, thinking disabled, 2048 context, local Ollama, process jail.

| Fixture | Investigation | Repair outcome | Patch generation (wall ms; input/output tokens; eval ms) |
|---|---|---|---|
| division_by_zero | INSUFFICIENT_EVIDENCE | blocked, no patch | — |
| argument_validation | LIKELY_CAUSE | VERIFIED_IN_TEST_ENVIRONMENT | 3009; 1372/133; 2423 |
| off_by_one | LIKELY_CAUSE | VERIFIED_IN_TEST_ENVIRONMENT | 3197; 1380/142; 2600 |
| missing_config | INSUFFICIENT_EVIDENCE | blocked, no patch | — |
| unreproducible | LIKELY_CAUSE | UNVERIFIED; original test passed, no patch generated | — |

The two proposals were valid and applied only in disposable copies; both original tests failed with the expected marker, then passed, as did regression. The argument proposal catches TypeError and ValueError; off-by-one removes the extra range step. No rejected, failed, or environment-failed patch occurred in this run; that does not measure their rates. Investigation latency was 6.7–15.3 seconds; details and investigation token counts are in the JSON. Division abstained in this run despite a real reproducible bug, whereas the prior run generated a passing patch: this illustrates outcome variability, not a controlled comparative experiment. Five synthetic cases do not establish broad accuracy. These results are test-environment evidence, not production safety.

## Engineering lessons and next gate

`run_repair` enforces eligibility, reproduction, generation, validation and before/after tests; `materialize` reads and hashes committed bytes rather than trusting working files. Tests that fail before and pass after establish that a patch changed the observed behavior; regression cases constrain collateral damage but cannot prove all behavior. Recorded stack frames are client claims, and the negative control shows why source matching alone is insufficient. Approvals are bound to an evidence and hypothesis digest, but benchmark auto-approval is only a test mechanism. General-purpose isolation needs a separately provisioned and independently tested Linux container environment, explicit non-root execution and adversarial control tests before expanding scope. Do not deploy, merge or run arbitrary repositories based on this report.
