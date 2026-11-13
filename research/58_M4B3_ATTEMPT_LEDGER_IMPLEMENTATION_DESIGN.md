# M4B.3 Attempt Ledger: Implementation and Failure-Testing Design

**Status:** DESIGN ONLY — NOT IMPLEMENTED  
**Experiment:** unchanged six cases × four arms, at most 24 evaluations, zero retries  
**Inference:** not run or authorized by this document

This document proposes a narrow local ledger for the M4B.3 runner. It is a design for human review, not an implementation, a security certification, or a guarantee of exactly-once model execution. The prospective protocol amendment remains subject to human approval.

## 1. Current verified behavior and proposed scope

Read-only inspection found that `scripts/evaluate_m4b3.py::execute` calls `provider.structured(...)`, catches exceptions, appends the response/error to an in-memory list, and then writes the JSON results file. `main()` checks the empty results template before creating the provider, but there is no attempt ID, durable pre-dispatch marker, startup ledger check, or reconciliation gate. `blackbox/providers.py::Provider.structured` performs the Ollama HTTP POST directly; no pre-dispatch persistence callback exists. The current M4B.3 harness tests plan construction, mocked execution, model/config checks, and template validation, but has no crash-ledger tests. No attempt-ledger database or file is present.

Proposed changes are limited to the later implementation of the M4B.3 runner, provider boundary, and its tests. The case set, arm order, prompt/schema, model configuration, 24-evaluation budget, zero-retry rule, fixtures, and labels do not change.

## 2. State machine

### 2.1 Identities and records

- **Evaluation ID:** stable identity for one registered case/arm pair, derived from the immutable revision, case ID, and arm (for example, `13bdc52…:m4b3_contract_mean:A`). It must be verified against the exact planned 24-pair set; it is not generated anew on restart.
- **Attempt ID:** unique UUID for one persisted attempt record. Under the current zero-retry protocol, an evaluation may have at most one dispatch attempt. A reconciliation event is not an attempt and never creates a new attempt ID to bypass that limit.
- **Run identity:** immutable commit plus a fingerprint of the planned cases/arms and effective model/request configuration. A ledger for a different revision, plan, or configuration must not be silently reused.
- **Event history:** append-only records with sequence number, event type, evaluation ID, attempt ID when applicable, timestamp, and event-specific data. The database is authoritative. Do not update or delete prior events to express a transition.

The deterministic evaluation ID and unique database constraints protect identity; the UUID protects attempt uniqueness. Neither alone proves that a provider request occurred.

### 2.2 Attempt lifecycle and exact state meanings

| State/event | Meaning | Automatic next action |
|---|---|---|
| `PLANNED` | Evaluation belongs to the frozen plan and has no attempt record. | May be started once after startup checks pass. |
| `IN_FLIGHT` | A durable pre-dispatch record exists. The provider request may or may not have been dispatched. | Must not be dispatched again. On startup, unresolved `IN_FLIGHT` blocks the run pending reconciliation. |
| `DISPATCH_INTENT` | Durable marker written at the provider boundary immediately before handing the request to HTTP transport. It narrows the crash boundary but does not prove bytes reached Ollama. | No retry. If no terminal record follows, treat as unknown. |
| `COMPLETED` | A response and its corresponding result record are durably committed in the authoritative ledger, whether semantic validation passed or failed. | Never call provider again for this evaluation. |
| `FAILED` | A definitive terminal failure is durably recorded, and evidence establishes either that dispatch did not occur or that the provider definitively rejected the request without performing an evaluation. It is not an unknown network outcome. | Never automatically retry; under the current one-request rule, do not dispatch again for this evaluation. |
| `UNKNOWN_OUTCOME` | The request may have been dispatched or completed, but durable evidence cannot establish the outcome; includes a timeout/connection loss after dispatch may have occurred and a crash before response/result persistence. | Block until explicit human reconciliation. Never automatically resubmit. |
| `RECONCILIATION` event | Human disposition of an unresolved record, appended without changing the original attempt state. | May clear the global startup block only for a documented permitted disposition; never erases uncertainty or authorizes an unapproved second dispatch. |

`FAILED` must not be the catch-all for exceptions. Safe examples are deterministic local validation/configuration failures before the dispatch boundary, or an explicit provider rejection whose documented response proves the model evaluation did not begin. Even then, record the failure and do not retry. A timeout, reset, EOF, ambiguous HTTP 5xx, process termination, missing response, or lost result after a possible send is `UNKNOWN_OUTCOME` unless authoritative evidence resolves it. A complete returned response that fails JSON/schema validation is still a `COMPLETED` evaluation with `valid: false`; it is not a provider failure and must not be retried.

The runner may mark a pre-dispatch failure `FAILED` only when it can prove the HTTP transport was never entered. Introduce a durable `DISPATCH_INTENT` callback at the actual provider boundary, immediately before `httpx.post`. By invariant, no request can be handed to transport before that marker commits. An `IN_FLIGHT` record with no `DISPATCH_INTENT` is evidence the transport boundary was not crossed only if implementation and tests establish that invariant. A present `DISPATCH_INTENT` still does not prove Ollama received or completed the request.

Under the registered one-request-per-case/arm and zero-retry rules, a known failed attempt is terminal. An unresolved outcome is never silently sent again. If reconciliation cannot resolve it, preserve the evaluation as missing/unknown. A human may authorize later processing only within the approved protocol: this can mean continuing with other not-yet-attempted evaluations after the unknown one has been explicitly accepted as missing, never replaying the uncertain evaluation. A new provider dispatch for an evaluation that may already have been sent would require a separately approved protocol change and budget decision.

## 3. Durability and crash boundaries

Use the ledger database as the durable source of truth for attempts and raw result records. For a successful response, insert the response/result row and append the `COMPLETED` event in **one SQLite transaction**. Commit only after both records are written. A parse-invalid but fully returned response is stored and completed with its validation failure. Export `data/m4b3-results.json` from committed ledger rows using a temporary file plus atomic replace; the export is a derived artifact and must never trigger a provider call. If the export fails, retry only the export.

This avoids a two-file transaction between the ledger and `data/m4b3-results.json`. If the ledger instead marked `COMPLETED` before response/result persistence, a crash could falsely claim completion. If it wrote the JSON result first and separately committed the ledger, a crash could leave a result with no ledger terminal state. SQLite cannot make arbitrary writes to a separate JSON file atomic with its database transaction. Keep the result payload in the same database transaction as `COMPLETED`, then regenerate the JSON view.

| Crash boundary | Durable records expected | Next process observes | Continue safely? / human reconciliation? | Duplicate request risk |
|---|---|---|---|---|
| 1. Before writing `IN_FLIGHT` | Frozen plan only; no attempt | Evaluation remains `PLANNED` | Yes after startup validation; no reconciliation | No prior request is possible if runner invariant holds |
| 2. After `IN_FLIGHT`, before dispatch | `IN_FLIGHT`; normally no `DISPATCH_INTENT` | Unresolved attempt | Block until ledger evidence/invariant is checked and human records disposition; if no dispatch marker and invariant proves transport was not entered, record `CONFIRMED_NOT_DISPATCHED` and the item remains eligible only for its one original dispatch | None yet; silent continuation would risk a duplicate if invariant were broken |
| 3. During provider dispatch | `IN_FLIGHT` and `DISPATCH_INTENT` | Unknown unless terminal transaction committed | Block; human reconciliation required | Yes if blindly replayed |
| 4. After dispatch, before response | Same as boundary 3 | `UNKNOWN_OUTCOME` | Block; preserve missing if unresolved | Yes if blindly replayed |
| 5. Response received, before result transaction | `IN_FLIGHT` and `DISPATCH_INTENT`; response may have existed only in memory | `UNKNOWN_OUTCOME` after process loss | Block; recover only from a durable, authenticated response record if one exists; otherwise preserve missing | Yes if blindly replayed |
| 6. After result persistence, before `COMPLETED` | In the recommended design, impossible as a committed state: result and terminal event share one transaction. An uncommitted transaction recovers wholly or rolls back. | Either `IN_FLIGHT` with no result or `COMPLETED` with result | If `IN_FLIGHT`, block and reconcile; if `COMPLETED`, continue without provider | Yes if result/ledger split is mishandled |
| 7. During ledger persistence | Transaction is either committed or rolled back, assuming SQLite/filesystem durability; on open, run integrity and schema checks | Valid committed state, or corruption/ambiguous state | If DB cannot be opened/validated or commit result is uncertain, fail closed; no provider call until repaired/reconciled | Prevented by refusing to dispatch without confirmed `IN_FLIGHT` commit |
| 8. Process termination or machine restart | State from last durable commit; in-progress memory is lost | As above; OS releases process lock, SQLite recovers journal/WAL | Validate DB, unresolved attempts, plan and export before continuing; human disposition for unresolved attempts | Never assume termination means Ollama stopped |

If disk is full or `IN_FLIGHT` cannot be committed and synchronized, do not call the provider. If the request may already have been sent and the terminal transaction cannot be committed (disk full, process termination, database I/O error), preserve the last durable `IN_FLIGHT` record; startup treats it as unknown and blocks. A later failure to export JSON is not grounds to repeat inference.

SQLite transactions are atomic within the database. In WAL mode, `synchronous=FULL` requests a WAL sync after each transaction commit, improving durability across power loss relative to `NORMAL`; actual guarantees still depend on the OS, filesystem, storage device, and their honoring sync requests. See [SQLite PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous), [Write-Ahead Logging](https://www.sqlite.org/wal.html), and [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html). This does not make the model call transactional with the database.

## 4. Storage design and recommendation

| Option | Strengths | Risks / fit |
|---|---|---|
| Append-only JSONL + flush/fsync | Human-readable; easy to copy; each event is naturally append-shaped. | A crash can leave a partial final line; concurrent append locking and sequence validation are manual; multi-record transitions and result payload require recovery rules; Windows durability and directory sync need platform-specific handling. |
| SQLite event ledger | Transactions group state and response/result atomically; unique constraints and foreign keys enforce identities; integrity checks and locking are built in; standard library `sqlite3` avoids a new package. | Binary and less directly inspectable; WAL sidecars must be kept with the DB while active; durable outcome still depends on storage honoring syncs; local administrators can tamper with it. |

**Recommendation:** a single local SQLite database, for this single-user, 24-evaluation experiment. Proposed path: `data/m4b3-attempt-ledger.sqlite3`. Keep a separate append-only event table, evaluation table, attempt table, result-payload table, and reconciliation table. Use `journal_mode=WAL`, `synchronous=FULL`, foreign keys, a bounded busy timeout, schema versioning, and a startup `PRAGMA integrity_check`. Never delete WAL/SHM sidecars while a process may own the database. The raw result JSON is exported from committed database contents; it is not the ledger.

Use database constraints and a narrow writer API to enforce:

- Unique evaluation ID and unique `(revision, case_id, arm)`; validate the plan has exactly the six frozen cases × four registered arms.
- Unique attempt ID and at most one dispatch-eligible attempt per evaluation under this protocol.
- No more than 24 planned evaluation IDs and no more than 24 provider dispatch intents. Reconciliation does not increase either limit.
- Legal event ordering (`IN_FLIGHT` before `DISPATCH_INTENT`; one terminal event per attempt; reconciliation only after an unresolved/terminal record).
- No update/delete path for event history; export and inspection use read-only queries.

The database should be created with restrictive user-only filesystem permissions/ACLs. Prevent concurrent runner processes with a separate OS-level exclusive lock held for the entire live run (Windows byte-range lock on the lock file; POSIX advisory lock on supported platforms). A second process must fail before provider construction. SQLite write locks alone protect individual transactions, not the whole evaluation loop. The lock is coordination, not tamper protection; after a crashed process the OS releases it.

Detect truncated/corrupt database files through SQLite open/recovery, schema-version checks, `integrity_check`, foreign-key checks, contiguous event sequence validation, and run/evaluation/attempt invariants. Fail closed on any anomaly. For JSONL, the equivalent would reject malformed interior lines and any partial trailing line, never silently truncate it. Append-only should be reinforced by application design and constraints/triggers, not described as tamper-proof: a local user with file access can replace the database, drop triggers, or rewrite history. A hash chain can detect accidental or unsophisticated edits only if a trusted chain head is stored elsewhere; for this prototype it adds complexity without protecting against the same local owner. Do not claim security certification.

## 5. Human reconciliation

Reconciliation is an appended administrative event; it does not rewrite the original `IN_FLIGHT`, `DISPATCH_INTENT`, `FAILED`, or `UNKNOWN_OUTCOME` record. Record reviewer identity, timestamp, evaluation/attempt IDs, evidence examined (paths/hashes or authenticated server record references), rationale, and disposition. Preserve the raw artifacts and original event order.

Allowed dispositions:

1. **`CONFIRMED_NOT_DISPATCHED`** — only with evidence that the provider transport boundary was not crossed (for example, no durable `DISPATCH_INTENT` under the tested invariant). Keep the original event history. A reviewer may authorize the one original dispatch only if no provider request was made, the approved protocol remains applicable, and this does not exceed the 24 actual-request budget. It is not a retry.
2. **`CONFIRMED_COMPLETED`** — only with a recoverable response/result record and evidence tying it to the attempt. Persist the recovered result and terminal record transactionally; never call the provider again.
3. **`CONFIRMED_FAILED`** — only with evidence of a definitive terminal failure and no completed evaluation. Preserve failure and do not resend under the current zero-retry rule.
4. **`ACCEPTED_UNKNOWN_MISSING`** — when evidence cannot resolve the outcome. Keep the attempt `UNKNOWN_OUTCOME`, record it as missing for scoring, and do not resend that evaluation. After the reviewer explicitly closes the reconciliation block, the run may continue only with other planned evaluations that have no attempt, subject to all remaining safeguards.

Forbidden dispositions include silently converting unknown to completed/failed, deleting or editing events, treating timeout as proof of non-dispatch, replaying a possibly dispatched evaluation, exceeding the budget, or using reconciliation to change model settings or arm/case identity. If the outcome cannot be established, uncertainty remains in the record. Any proposal to send another request after a possible dispatch needs a separately approved prospective protocol; it is not authorized by this design.

## 6. Failure-injection test matrix

All tests must use a fake provider, deterministic fault hooks, and temporary local databases. No test needs Ollama, fixture execution, Docker, production routes, or real inference. For crash cases, run the evaluator in a child process and terminate it at a named checkpoint; reopen the database in a fresh process. Verify both durable rows/events and provider call count.

| Test | Setup and injected failure | Expected durable state | Expected runner behavior | Provider call allowed? |
|---|---|---|---|---|
| 1. Before dispatch | Start a planned evaluation; crash before `IN_FLIGHT` transaction | `PLANNED`, no attempt | Startup validates plan and can start its one attempt | No call before restart; one fake call after valid start |
| 2. After dispatch, before result persistence | Fake provider records receipt, then child terminates before result commit | `IN_FLIGHT` + `DISPATCH_INTENT`; no result/terminal event | Restart marks unresolved outcome and blocks pending reconciliation; never resends that evaluation | One prior fake call; none on restart for that evaluation |
| 3. Known provider failure | Inject deterministic pre-dispatch validation failure or explicit definitive rejection | `FAILED` with error class and evidence of no inference/completion | Record failure; continue only to other untouched evaluations; no retry | No call for pre-dispatch failure; one rejected fake call for explicit server rejection |
| 4. Timeout after possible dispatch | Fake transport records receipt then raises timeout | `IN_FLIGHT` + `DISPATCH_INTENT`, then `UNKNOWN_OUTCOME` if terminal write succeeds; otherwise unresolved `IN_FLIGHT` | Block until reconciliation; never treat timeout as known failure or resend | One fake call; no further call for evaluation |
| 5. Result persistence failure | Fake provider returns; inject DB write/commit failure for response transaction | Prior `IN_FLIGHT`/`DISPATCH_INTENT`; no durable result or `COMPLETED` | Fail closed; restart sees unresolved attempt; reconcile, do not repeat | One fake call; no provider call while ledger unavailable |
| 6. Crash after result persistence but before `COMPLETED` | Attempt to inject between result and terminal write | Recommended single-transaction design makes this intermediate durable state impossible; either transaction rolls back or both commit | Assert atomic outcome; if both committed, continue/export; if neither, unresolved and reconcile | One fake call; no repeat |
| 7. Startup with unresolved `IN_FLIGHT` | Seed valid DB with `IN_FLIGHT` only | Original event preserved | Block before provider construction; require reconciliation | No |
| 8. Startup with `UNKNOWN_OUTCOME` | Seed valid DB with unknown attempt and no resolving disposition | Unknown preserved | Block before provider construction until explicit disposition | No |
| 9. Corrupt/truncated ledger | Truncate DB/WAL or alter a record in a test copy | Integrity/schema check fails; original test fixture retained for diagnosis | Fail closed; do not auto-repair/delete/recreate or use JSON template as permission to start | No |
| 10. Duplicate evaluation ID | Insert/plan same revision/case/arm twice | Unique constraint rejects transaction | Abort before provider construction | No |
| 11. Duplicate attempt ID | Insert the same UUID for a second attempt | Unique constraint rejects append | Fail closed and preserve existing event history | No |
| 12. Concurrent runner startup | Two processes contend for exclusive run lock | One owner; no competing writes | Second exits before planning live dispatch/provider construction | At most one process can call fake provider |
| 13. Exceed 24-evaluation budget | Supply a plan with a 25th ID or 25th dispatch intent | Constraint/plan validation rejects it | Fail closed before the 25th call | At most 24 calls; test may assert zero for invalid plan |
| 14. Resubmit an attempted case/arm | Seed `FAILED`, `COMPLETED`, or unresolved attempt; request same evaluation again | Existing attempt remains immutable | Reject as duplicate; reconciliation cannot silently create another attempt | No |

Add assertions that valid returned-but-schema-invalid output is `COMPLETED` with `valid: false`, JSON export failure never dispatches again, disk-full/ledger-write failure prevents dispatch, reconciled unknown-missing permits only untouched later evaluations, and no code path automatically retries. Fault injection must cover transaction commit uncertainty and process termination at provider-boundary checkpoints. These are proposed tests, not tests run here.

## 7. Security and operational limitations

- Store the ledger under user-only ACLs/permissions and protect its backups. It contains raw model responses and experiment metadata. Accidental edits should be detected by integrity/invariant checks, but a local owner can tamper with or replace it.
- Hash chaining is optional and not recommended for this prototype without an independently trusted chain head. It does not protect against an owner who can rewrite both records and hashes.
- Disk-full, access denied, failed `fsync`, database busy timeout, or I/O error before `IN_FLIGHT` commit means no provider dispatch. The runner must stop. After possible dispatch, failed persistence means unknown and blocks.
- On Windows, use a local filesystem and SQLite's supported locking; test abrupt process termination and restart on the target filesystem. Do not assume a flushed language-level buffer alone is durable. Power loss and device/controller behavior remain outside a small unit test's guarantees.
- The ledger is independent of WSL2 and Docker: it must not require fixture execution, a container, or a Docker daemon. Keep it local to the runner's host filesystem, not a shared/network filesystem.
- A database or lock failure is a stop condition. Never create a fresh empty ledger automatically when an existing ledger is missing, corrupt, inaccessible, or mismatched; require explicit operator review.
- This design reduces replay risk and improves auditability; it is not a security certification and does not guarantee exactly-once behavior at Ollama.

## 8. Existing code locations for a later implementation

No files below were modified for this design.

| Existing location | Proposed later work |
|---|---|
| `scripts/evaluate_m4b3.py::plan` | Validate the exact 24 stable evaluation IDs against pinned case/arm order. |
| `scripts/evaluate_m4b3.py::execute` | Create attempt IDs; commit `IN_FLIGHT`; coordinate `DISPATCH_INTENT`; classify known vs unknown failures; atomically store result plus terminal event; enforce no retry. |
| `scripts/evaluate_m4b3.py::main` | Acquire run lock and inspect ledger before provider construction; block unresolved attempts; export results from DB; reject mismatched ledger/configuration. |
| `blackbox/providers.py::Provider.structured` near the Ollama `httpx.post` | Add a narrow, mandatory pre-dispatch callback after local request validation and immediately before transport. Ensure there is no request path that bypasses it. Keep HTTP/retry semantics explicit. |
| `tests/test_m4b3_harness.py::MockProvider`, `test_mock_executes_every_arm_and_records_invalid_response`, plus new isolated ledger tests | Add deterministic fault injection, child-process crash/restart, concurrency, corruption, budget, and no-resubmission coverage from Section 6. |
| Future `data/m4b3-attempt-ledger.sqlite3` | Runtime database only; create during a separately approved implementation/run, never as part of this design. |
| `data/m4b3-results.json` export path in runner | Generate as a derived view after committed DB results; never use it alone to infer that an uncheckpointed request did not happen. |

## 9. Document 56 wording review

Document 56 already says that an unresolved `IN_FLIGHT` is treated as `UNKNOWN_OUTCOME`, that uncertain requests are not automatically replayed, and that reconciliation is required. One additional clarification is recommended to distinguish known failures from network ambiguity and to close the manual-replay loophole. Suggested wording for a future reviewed edit:

> A timeout, connection loss, or other error after dispatch may have occurred is `UNKNOWN_OUTCOME`, not `FAILED`. Reserve `FAILED` for a definitively known terminal failure supported by evidence. Human reconciliation must not silently authorize another request for an evaluation that may already have been dispatched; under the current zero-retry protocol, preserve that evaluation as missing/unknown unless authenticated evidence resolves its outcome. A request may proceed only when reconciliation establishes that no provider dispatch occurred and the single planned request remains unused.

This is a recommendation only. Document 56 was not edited in this design task.

## 10. Open decisions for human review

1. Approve SQLite and its location, durability settings, backup/retention, and read-only inspection format.
2. Define exactly which provider rejection responses prove inference did not begin; otherwise classify post-dispatch errors conservatively as unknown.
3. Approve the provider callback boundary and the invariant that every network POST is preceded by a committed `DISPATCH_INTENT`.
4. Decide whether a proven pre-dispatch interruption may resume the one unused planned dispatch after explicit reconciliation, while keeping the zero-retry rule intact.
5. Specify reviewer identity and evidence requirements for reconciliation, plus who may close an unknown as missing.
6. Confirm filesystem, Windows process-lock behavior, disk-full behavior, and how exported JSON is regenerated without changing model records.

No model inference, fixture execution, Docker, repair workflow, or production route was used or authorized for this design. No source code, existing document, prompt, schema, fixture, label, registry, or results file was modified.

**Final status:** `LEDGER_DESIGN_READY_FOR_REVIEW — IMPLEMENTATION_NOT_STARTED — LIVE_EXECUTION_NOT_AUTHORIZED`
