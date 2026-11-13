# M4B.3 Attempt Ledger Red-Team Review

**Review type:** Read-only architecture review; one report created  
**Verdict:** `NOT_READY — BLOCKERS_REMAIN`  
**Implementation:** not started  
**Live inference:** not authorized

## 1. Executive verdict

The existing M4B.3 runner has no attempt ledger, no durable marker before its request, and no startup gate for ambiguous attempts. The proposed SQLite architecture in Document 58 is a useful direction, but it does not yet establish the critical guarantees. In particular:

1. The current `execute()` function can be called directly with a plan and a real provider, bypassing `main()`'s empty-template and model-preflight checks.
2. The proposed `DISPATCH_INTENT` callback can narrow the send boundary but cannot prove whether Ollama received a request after the marker commits. The design's `CONFIRMED_NOT_DISPATCHED` reconciliation path must be constrained to the *absence* of that marker, and its exact same-attempt transition is not defined.
3. Document 58 proposes event, evaluation, attempt, result, and reconciliation tables without choosing one authoritative state source or a replay consistency rule. SQLite transactions do not by themselves prevent disagreement between those representations.
4. The design does not fully specify ambiguous SQLite commit handling or how an old nonempty JSON results file without a matching ledger is handled.
5. The current source catches provider and response-validation exceptions together. The runner cannot infer from that catch whether an inference occurred. A timeout or connection error after entering transport must be recorded as unknown, not failed.

The smallest safe next step is to revise the *design* (not the code) to define one append-only event stream as canonical, a precise same-attempt pre-dispatch reconciliation transition, single-use dispatch enforcement, a mandatory M4B3-specific provider boundary, startup refusal rules, and the failure matrix below. Human approval is required before implementation; a prospective amendment must also be approved before inference.

## 2. Scope, provenance, and verification limits

I inspected the working copies of Documents 50 and 55–58, the M4B.3 runner, provider, tests, results template, and `requirements.txt`. No tests, model calls, fixtures, Docker, repair workflow, or route were executed. The source claims below are static readings of the current working tree, not runtime measurements.

Initial `git status --short` contained **18 modified tracked files and 428 untracked entries**. The requested report did not exist. Relevant existing status entries include:

- `scripts/evaluate_m4b3.py`, `tests/test_m4b3_harness.py`, `data/m4b3-results.json`, and `research/50` through `research/58` are untracked working-copy files.
- `blackbox/providers.py` was not listed as modified; it is present as a tracked file in the inspected tree.
- Other existing modified files include `.env.example`, `EVALUATION.md`, `README.md`, `blackbox/investigator.py`, repair modules, `tests/test_repair.py`, and numerous `graphify-out/` files. Existing untracked research, fixture, script, test, and graph cache entries were also present.

This matters for provenance: the current M4B.3 runner, test file, and recent research drafts are not committed in this working tree. This review establishes what their present bytes say, not that those bytes are approved or identical to a released implementation. The original registered methodology remains the pinned blob at `13bdc52bad27c49b77e85daac16876133f382009`; current working-copy additions in `research/50` are not treated as originally registered. Documents 56 and 57 remain `DRAFT — NOT APPROVED`; Document 57 is evaluator-only.

## 3. Existing implementation findings

Line references are to the inspected working copies at review time.

| Location | Verified behavior | Reliability implication |
|---|---|---|
| `scripts/evaluate_m4b3.py::plan`, lines 35–61 | Resolves the exact pinned revision, reads registry/labels/source blobs from Git, checks source hashes and case order, builds four arms per case, and rejects a plan not exactly 24 items. | Strong plan construction inside this function. It does not persist plan IDs or prevent a caller from passing a different `plans` list directly to `execute()`. |
| `scripts/evaluate_m4b3.py::validate_template`, lines 66–70 | Requires `template_only_no_model_calls`, empty `results`, and matching revision. | Prevents a normal CLI run from starting with a nonempty or mismatched JSON file. It does not detect a prior request if the file remained the untouched empty template after a crash. |
| `scripts/evaluate_m4b3.py::execute`, lines 89–109 | Accepts arbitrary plans/provider/output path; loops once per item; invokes `provider.structured()` at lines 103–104; catches any `Exception` together with parsing/validation errors at 106; appends to memory and writes `partial` JSON at 107–108. | Result persistence happens after provider completion/error. An exception does not prove no inference occurred. A process crash after dispatch but before line 108 leaves no durable attempt record. A direct caller bypasses `main()` checks. |
| `scripts/evaluate_m4b3.py::main`, lines 110–128 | CLI requires exactly one of `--dry-run`/`--run-live`; plans and checks revision/template; dry run exits; live path verifies local model then constructs `Provider('ollama', MODEL)` and calls `execute()`. Final JSON is written at 127–128. | The ordinary live CLI hardcodes local Ollama and has no model fallback. Its second template check still cannot detect an unrecorded request after a crash that left the template empty. Writes use `Path.write_text`, not an atomic replace. |
| `scripts/evaluate_m4b3.py`, line 129; imported API | `main()` runs from the `__main__` guard, but tests import and call `execute()` directly. | There is a CLI entry point and a Python-callable execution entry point. No current control makes `main()` the only possible M4B.3 live route. |
| `blackbox/providers.py::Provider.structured`, lines 54–92 | Ollama URL/context/timeout/output-budget validation occurs at 61–79. The actual top-level `httpx.post` occurs at 81–83. `raise_for_status`, response JSON decoding, length check, and content check occur at 84–91. | A dispatch callback would need to be after all local request construction/validation and immediately before line 81. Errors after transport entry are ambiguous unless the returned response itself conclusively establishes a terminal no-inference rejection. The current method discards some HTTP response/error bodies. |
| `blackbox/providers.py`, lines 61–92 | M4B3's current `main()` uses Ollama only. Ollama call specifies `follow_redirects=False` and `trust_env=False`; there is no explicit retry loop or custom retry transport in this code. | No application retry/fallback or redirect retry is visible on this path. HTTPX permits retries when explicitly configured on a transport; none is configured here. The request still cannot prove remote execution count. [HTTPX transport docs](https://www.python-httpx.org/advanced/transports/), [HTTPX API docs](https://www.python-httpx.org/api/). |
| `blackbox/providers.py`, lines 93–120 | `structured()` also supports Gemini and calls `generate_content` with `HttpRetryOptions(attempts=1)` at 99; `configured_provider()` can return Ollama or Gemini at 112–120. | This alternate provider path is not used by M4B3's current `main()`, but a caller can pass another provider to `execute()`. “All calls pass one ledger boundary” is not true of the existing general provider API. |
| `tests/test_m4b3_harness.py::MockProvider`, lines 63–82; execution test 84–92 | Fake provider counts in-process calls; test invokes all 24 plans and checks invalid response recording. | Useful unit-level coverage, but it does not kill a child process, reopen durable state, or test replay prevention. No current test exercises a ledger. |
| `data/m4b3-results.json`; template validation above | Current template envelope has `status`, `revision`, `arms`, and `results`. Per-evaluation records and final envelope are written by the runner. A search found no other code reader for this M4B.3 result file; research docs do read/described it. | Preserve the existing envelope for compatibility unless separately reviewed. No downstream consumer inventory proves external compatibility. A nonempty old results file with no matching ledger must not be imported or overwritten automatically. |
| `requirements.txt` | Uses ranges (`httpx>=0.27,<1`, `pydantic>=2.8,<3`, and `google-genai>=1.0,<3`); no lockfile was found in the inspected root names. | Dependency versions are not pinned by this file. A version range is not a reproducible runtime fingerprint. |

HTTPX's public API does not follow redirects by default, and the current M4B3 Ollama call explicitly disables them. Retry support is exposed through a configured `HTTPTransport`; the current code does not instantiate one. This is evidence of no configured application-level retry on the current path, not evidence that a request accepted by Ollama ran exactly once. HTTPX retries, if later configured, must be disabled or included behind the ledger boundary. (See the official [redirect behavior](https://www.python-httpx.org/compatibility/) and [transport retry documentation](https://www.python-httpx.org/advanced/transports/).)

## 4. Formal state-machine review

Document 58 describes useful states but not a complete transition system. The following is the minimum safe transition proposal. `READY_TO_DISPATCH` is an explicit administrative state recommended to remove the ambiguity in the existing `CONFIRMED_NOT_DISPATCHED` wording; it is a design recommendation requiring human approval, not an approved protocol change.

| Current state | Event | Preconditions | Next state | Permitted action | Forbidden action |
|---|---|---|---|---|---|
| `PLANNED` | `BEGIN_ATTEMPT` | Frozen run fingerprint matches; evaluation is one of 24; no attempt exists; run lock held | `IN_FLIGHT` | Create one attempt ID and commit its identity/config snapshot | Provider call before commit; second attempt ID for same evaluation |
| `IN_FLIGHT` | `DISPATCH_INTENT` | Same attempt ID; all request construction/validation complete; no prior dispatch intent; ledger commit acknowledged as durable | `DISPATCH_INTENT` | Enter transport exactly once after commit | Enter transport before marker; write a second marker or send twice |
| `IN_FLIGHT` | Restart sees no dispatch marker | Invariant that *every* transport call requires a committed marker is verified; ledger integrity passes | `IN_FLIGHT_UNRESOLVED` pending review | Block; allow reviewer to append `CONFIRMED_NOT_DISPATCHED` | Automatically continue or create a new attempt |
| `IN_FLIGHT_UNRESOLVED` | `CONFIRMED_NOT_DISPATCHED` | No `DISPATCH_INTENT`; reviewed event sequence proves transport could not have been entered; reviewer/evidence recorded | `READY_TO_DISPATCH` for the **same** attempt ID | After explicit authorization, append the single `DISPATCH_INTENT` for same attempt and call once | New attempt ID; second request after a marker; relying only on absence of a server receipt |
| `DISPATCH_INTENT` | Complete HTTP response body received | The one transport call returned a complete response; raw body and request identity available | `RESPONSE_RECEIVED` in memory, then terminal transaction | Persist raw response/result plus terminal event atomically | Retry for malformed, empty, truncated-at-model-limit, or schema-invalid output |
| `RESPONSE_RECEIVED` | Terminal transaction commits | Result payload/hash and `COMPLETED` event inserted in one DB transaction; commit returns success | `COMPLETED` | Continue to next unattempted evaluation; regenerate JSON export | Provider call for this evaluation again |
| `DISPATCH_INTENT` | Definitive rejection response | Full authenticated response provides authoritative guarantee that inference did not begin; classification rule is explicitly approved | `FAILED` | Record response/error, continue only to untouched plan entries | Automatically retry; classify generic 4xx/5xx as definitive without evidence |
| `DISPATCH_INTENT` | Timeout, transport error, partial body, process loss, ambiguous response | No authoritative evidence establishes non-execution or a durable complete result | `UNKNOWN_OUTCOME` (or unresolved `IN_FLIGHT` if terminal append fails) | Stop this evaluation; reconcile; preserve missing if unresolved | `FAILED` by generic exception catch; replay |
| `UNKNOWN_OUTCOME` | `CONFIRMED_COMPLETED` | Recoverable response/result tied to attempt; evidence hash verified | `COMPLETED` by appended reconciliation/result events | Continue without provider | Reissue request |
| `UNKNOWN_OUTCOME` | `CONFIRMED_FAILED` | Authoritative evidence establishes definitive terminal non-completion | `FAILED` by appended reconciliation event | Continue only with untouched evaluations | Retry under zero-retry protocol |
| `UNKNOWN_OUTCOME` | `ACCEPTED_UNKNOWN_MISSING` | Reviewer, timestamp, evidence examined, and rationale recorded | Remains `UNKNOWN_OUTCOME`, administratively closed as missing | Continue with untouched plan items after startup revalidation | Change unknown to failed/completed; replay same evaluation |
| `COMPLETED` | Same evaluation appears in a later plan | Existing completed event belongs to matching identity/fingerprint | `COMPLETED` | Export/read only | Dispatch again |
| `FAILED` | Same evaluation appears in a later plan | Existing failed event | `FAILED` | Report missing/failed | Automatic/manual retry without a separately approved new protocol |
| Any | Ledger missing, corrupt, replaced, schema/fingerprint mismatch | Startup validation fails | `BLOCKED` | Preserve files, request human review | Create a fresh empty ledger and infer; trust JSON alone |
| Any | Second process starts | Exclusive run lock already held | `BLOCKED` | Exit before provider construction | Proceed concurrently |

Illegal transitions include: `PLANNED → DISPATCH_INTENT`; any provider call before committed `IN_FLIGHT` and `DISPATCH_INTENT`; `DISPATCH_INTENT → PLANNED/READY_TO_DISPATCH`; `UNKNOWN_OUTCOME → FAILED/COMPLETED` without evidence and an appended reconciliation event; any transition that erases history; or a second dispatch intent for one evaluation.

### Critical reconciliation transition

Document 58 currently says an `IN_FLIGHT` record without a dispatch marker may be reconciled as not dispatched and “remain eligible” for its original dispatch, but does not define the exact state, attempt-ID reuse, or uniqueness rule. That is a **BLOCKER** until defined. Minimal clarification:

1. Persist `IN_FLIGHT` with exactly one attempt ID.
2. The only code path to HTTP must first commit one unique `DISPATCH_INTENT` for that same attempt ID.
3. If startup sees `IN_FLIGHT` with no dispatch marker and the invariant is proven, block for review. On approval, append `CONFIRMED_NOT_DISPATCHED`, move that same attempt to `READY_TO_DISPATCH`, and permit one marker/transport call using the **same attempt ID**. Do not create a second attempt.
4. Enforce `UNIQUE(evaluation_id)` on dispatch intent (or an equivalent transactionally checked invariant). Once the marker exists, local evidence cannot establish non-dispatch; only authenticated provider evidence can resolve outcome. Do not replay.
5. Treat marker commit errors as stop conditions. Do not enter transport unless the commit returned success. If the call entered transport and outcome is unclear, it is `UNKNOWN_OUTCOME`.

This still cannot make the remote side exactly-once. The maximum enforceable local property is at-most-one transport entry for an evaluation, assuming every M4B3 call is forced through the guarded path and the local database/lock invariants hold.

## 5. Invariant analysis

| Invariant | Why it matters | Proposed enforcement | Failure mode | Demonstrating test | Status |
|---|---|---|---|---|---|
| **I1 Pre-dispatch durability** — no HTTP request without durable `IN_FLIGHT` and `DISPATCH_INTENT` | Prevents unrecorded inference after crash | Mandatory provider-boundary callback; commit before transport; startup verify | Direct `execute()`/`Provider.structured()` bypass; commit error; another HTTP call path | Kill process after each commit; fake server receipt must imply both durable events | Proposed only; current runner violates |
| **I2 At-most-one dispatch** | Preserves one-request/zero-retry design | One unique dispatch-intent per evaluation and one-use permit consumed in provider; no retrying transport | Repeated call inside callback/wrapper; duplicate runner; SDK retry; replay | Provider receipt log across crash/restart and duplicate-plan attempts | Not established; reconciliation loophole unresolved |
| **I3 Unknown preservation** | Prevents timeout/error being mislabeled as failure or completion | Classify every post-boundary exception conservatively; append unknown; no automatic terminal conversion | Existing broad `except Exception` collapses errors to invalid result without certainty | Inject timeout after fake server receipt; restart must block and retain unknown | Proposed only |
| **I4 Result atomicity** | Avoids claiming completion without the response/result | Store raw response, normalized result, and `COMPLETED` event in one transaction | Separate event/current-state/result representations disagree; commit ack error | Fault between inserts and at commit; reopen and compare event replay/result hash | Proposed, but source-of-truth unresolved |
| **I5 No silent replay** | Avoids duplicate inference after restart | Startup reads ledger and refuses attempted eval; no fresh empty DB on missing/corrupt state | Existing empty JSON template remains after crash before first write; direct execution entry | Crash after server receipt before JSON write; restart call count stays one | Current behavior fails |
| **I6 Budget enforcement** | Keeps maximum 24 evaluations and request budget | Plan is exact 24; DB unique constraints/counts; one dispatch intent per eval; count survives restarts | `execute()` accepts arbitrary/repeated plans; counter only in memory | 25th evaluation, duplicate plan, 24 calls plus restart | Partly planned; not persistent/currently enforced outside `plan()` |
| **I7 Identity integrity** | Prevents attaching response to wrong arm/case/revision/settings | Canonical run/evaluation/request fingerprints and FK-linked result | IDs only case/arm; config/code changes not part of current design fingerprint | Change each fingerprint component independently and assert startup blocks | Incomplete proposal |
| **I8 Audit preservation** | Reconciliation must not erase uncertainty | Canonical append-only event stream; no mutation API; hash/sequence checks | Current-state tables diverge; local owner rewrites DB; unsafe “repair” | Attempt update/delete, rebuild projection from events, tamper-copy test | Proposed only; append-only not tamper-proof |
| **I9 Concurrency exclusion** | Stops two runners from dispatching same evaluation | Process-wide OS lock held from before startup validation through shutdown, plus DB uniqueness | Stale path mistaken for live lock; lock handle inherited; race; unsupported filesystem | Two real child processes race on target Windows filesystem | Concept proposed; platform behavior unverified |
| **I10 Fail-closed startup** | Prevents replay on missing/corrupt/mismatched state | Validate DB existence policy, integrity, fingerprint, outcomes, JSON relation, lock before provider creation | Existing code validates only empty JSON; no ledger; silently initialize empty DB | Missing/corrupt/mismatched DB and nonempty JSON each produce zero provider calls | Not present |

“At-most-once application dispatch” means the local code enters its single HTTP transport path no more than once for an evaluation. “Exactly-once remote inference” would require proving Ollama received and executed the request exactly once and coordinating that remote effect atomically with local storage. The local SQLite transaction and Ollama HTTP request are separate systems; current code supplies no idempotency key or remote deduplication protocol. Do not claim exactly-once model execution.

## 6. SQLite and Windows durability analysis

### 6.1 Canonical data model

Document 58 proposes an append-only event table plus evaluation, attempt, result, and reconciliation tables, but does not say which one is canonical. That is a **MAJOR** design gap. Recommend one authoritative append-only `events` table. Derive current evaluation/attempt state by replaying its small event sequence (only 24 evaluations); either avoid mutable projections or rebuild/check projections transactionally and compare them against replay at startup. Store raw response/result payload in the terminal result event or a content row inserted in the *same transaction* as `COMPLETED`, with a content hash referenced by the event. Database constraints can enforce uniqueness/FKs, but event-sequence semantics still need a single writer API and startup replay validation.

Use WAL and `synchronous=FULL` as a reasonable local prototype configuration, not a magic guarantee. SQLite documents that `FULL` in WAL adds a WAL sync after each commit; durability still relies on the VFS, OS, filesystem, and storage honoring synchronization. [SQLite PRAGMA documentation](https://www.sqlite.org/pragma.html#pragma_synchronous). WAL allows concurrent readers and a single writer, but requires same-host processes and is unsupported over a network filesystem; it uses `-wal` and `-shm` sidecars. [SQLite WAL documentation](https://www.sqlite.org/wal.html).

Specific decisions:

1. **Transaction commits:** if `COMMIT` raises, stop. Do not infer rollback from the exception and do not call the provider. Close/reopen in a fresh connection, run integrity and event-sequence checks, and inspect the transaction's unique event ID/hash. If the outcome remains ambiguous, preserve it as unresolved. A failed `COMPLETED` commit after response receipt is not permission to resend.
2. **Interrupted WAL writes:** SQLite recovery should expose a committed or rolled-back transaction when storage behaves correctly. Startup must validate the DB and replay events. Corruption or I/O errors block; never delete WAL/SHM or create an empty replacement.
3. **State source:** canonical events are recommended; state views are projections. A mismatch blocks and is repaired only by deterministic rebuild from intact events, with an audit note. Do not make both “event history” and “current attempt rows” independently authoritative.
4. **Old JSON results:** if the JSON file is nonempty but the ledger is missing or mismatched, block and preserve both. Do not infer ledger state from JSON, auto-import it, or overwrite it. Any migration requires human review, hashes, and a one-time documented reconciliation. The empty template alone cannot prove no earlier request occurred.
5. **JSON export:** preserve the current envelope (`status`, `revision`, `arms`, `results`, plus existing run configuration fields). Export only from completed DB result rows to a same-directory temporary file, flush, and replace. If replace fails, inference stays complete in the DB; retry export only. Never start a new model request to repair export.
6. **WAL/SHM and backups:** do not copy only the main DB while a live WAL may hold committed data. Use SQLite's backup API or acquire the run lock, checkpoint/close cleanly, then make an immutable backup. Inspect a read-only backup/snapshot, not the active DB. Do not remove sidecars while any process may hold the database.
7. **Corruption:** preserve original DB/WAL/SHM for diagnosis; refuse provider construction. No automatic “repair”, truncation, fresh DB, or results-template reset.

### 6.2 Windows lock critique

The Document 58 phrase “Windows byte-range lock on the lock file” is only a proposal, not verified implementation. A lock file's **existence** does not mean a process owns a lock; stale pathnames can remain after termination. Use a stable, non-deleted lock path and an OS-enforced lock held by an open non-inheritable handle for the entire live run. Acquire it before reading/creating the database or constructing a provider. On failure, exit without inference. Do not rename/delete/recreate the lock file while another process could hold a lock; that can split contenders across different file objects.

Python's Windows `msvcrt.locking` offers byte-range locks and nonblocking `LK_NBLCK` failure; `LK_LOCK` retries at one-second intervals up to ten times. The exact behavior must be tested on the target Windows filesystem and Python version, including whether child handles are inherited. [Python `msvcrt` documentation](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking). A two-process test is required; a single-process unit test proves nothing about mutual exclusion. Process termination should close handles and release OS locks; verify this. A leftover lock *file* is normal and should be reacquired through the OS lock, not removed as “stale.” Lock acquisition failure and SQLite busy timeout both fail closed; DB transaction retry must never repeat an HTTP request.

Use local NTFS (or another tested local filesystem), not a network share, OneDrive sync directory, or cross-host WAL. SQLite itself is independent of WSL2/Docker only if all M4B3 run and inspection processes access the same supported host-local DB. Hardware power-loss behavior cannot be certified by a child-process crash test. These are durability controls, not security certification; a local administrator can still tamper with DB and backups.

## 7. Provider-boundary analysis

The narrow insertion point is after all request validation and canonical payload construction but immediately before transport send at `blackbox/providers.py:81`. The future provider should first build a complete `httpx.Request` (including JSON serialization) locally, then ask the ledger to durably commit `DISPATCH_INTENT`, then call `Client.send(request)` only if that commit returned success. A callback merely placed before the current top-level `httpx.post(..., json=...)` is weaker: HTTPX still builds/encodes the request inside that call after the callback. If the callback raises or its commit is ambiguous, do not call HTTP. Even with a prebuilt request, a crash after committing `DISPATCH_INTENT` but before `send()` is indistinguishable after restart from a request that entered transport; preserve unknown and do not resend.

Current weaknesses:

- `Provider.structured()` accepts no ledger context and can be called by `Provider.analyze()` (`providers.py:50–52`) or application routes. The M4B3 runner's `execute()` also accepts an arbitrary provider object. Thus a callback added only in `evaluate_m4b3.py` can be bypassed by direct/provider APIs.
- A complete `httpx.Request` should be built before writing `DISPATCH_INTENT`. The present code passes a `json=` object to `httpx.post`, so request serialization occurs within the HTTPX call. The exact moment the library begins transport is below the Python call boundary; instrumentation should guarantee only that a committed marker precedes any `send()` call, not that the marker proves bytes were sent.
- `evaluate_m4b3.main()` currently hardcodes Ollama (runner line 125), but Python callers can import `execute()` and pass a live provider. The code currently has no capability/permit that forces the M4B3 route through the ledger.
- Current Ollama transport has redirects disabled and no configured retry transport. Keep an explicit no-retry transport policy and test transport invocation count. Treat future retry adapters, service wrappers, shell commands, and alternate model SDKs as separate dispatch paths that must be disabled or ledger-gated.
- Gemini is an alternate `Provider.structured()` branch (`providers.py:93–108`) with its own SDK retry option. It is not the normal M4B3 CLI path; a future M4B3 runner must reject it rather than assume Ollama semantics.
- HTTPX buffers ordinary non-streaming response bodies before returning. A read failure/partial body after request dispatch is unknown. If a complete body is received but JSON/schema validation fails, store the body and mark a completed invalid response. The current provider may raise before returning `ProviderResult` (e.g. `raise_for_status`, `response.json`, `done_reason == 'length'`), so the future boundary needs a typed outcome carrying dispatch state, response-received/body-complete status, status code, raw body/hash, and usage/error. A complete but token-truncated model response is a consumed evaluation, not retryable.

### Provider failure classification

| Failure/observation | Current boundary status | Safe classification for future ledger |
|---|---|---|
| URL/context/timeout/output-budget validation error before dispatch callback | Before HTTPX POST | `FAILED` or pre-dispatch blocked, with evidence no transport was entered; no retry automatically |
| `IN_FLIGHT` commit fails before provider invocation | Before HTTPX POST | No inference dispatched; stop. Resolve local DB ambiguity before proceeding |
| `DISPATCH_INTENT` callback fails or commit acknowledgment is ambiguous | Callback may or may not have committed; HTTP must not be entered | Stop. If marker exists, conservative unknown until reconciliation; no request may be sent after callback failure |
| Connect error/timeout after `httpx.post` entered | Request may have reached transport/daemon | `UNKNOWN_OUTCOME` unless authoritative evidence proves no request could have reached Ollama |
| Read timeout, connection reset, partial response body | Request dispatched; response incomplete | `UNKNOWN_OUTCOME` |
| Ollama completed but client timed out | Server may have executed fully | `UNKNOWN_OUTCOME`; never retry |
| Full HTTP response, definite server rejection with documented guarantee inference did not start | Response received and authenticated to endpoint | `FAILED`, only if semantics are explicitly verified; otherwise `UNKNOWN_OUTCOME` |
| Generic non-2xx/5xx response | Response received but inference semantics unclear | `UNKNOWN_OUTCOME` unless the exact response class is proven pre-inference rejection |
| Full response body, `done_reason=length`, malformed JSON, empty content, or schema/citation validation failure | A response was returned; current code may raise/mark invalid | `COMPLETED` with raw response/error and `valid: false`/incomplete; no retry |
| Full valid structured response and result transaction commits | Complete response and durable result | `COMPLETED` |

No generic Python exception handler can classify all these correctly. Preserve exception class and phase, but phase alone is not proof that the server did not execute.

## 8. Exact scenario timelines

| # | Timeline | Durable local evidence after restart | Safe action |
|---|---|---|---|
| 1 | Plan persisted → `IN_FLIGHT` commit returns → process dies immediately | `IN_FLIGHT`, no dispatch marker | Block. Under a proven mandatory-boundary invariant, human may reconcile as not dispatched; same attempt may be authorized for its first HTTP dispatch. |
| 2 | `IN_FLIGHT` → `DISPATCH_INTENT` commit returns → process dies before entering HTTPX | Marker exists, but HTTP may not have run | Indistinguishable locally from subsequent transport entry. Unknown/block; do not call again. This is a real uncertainty window. |
| 3 | HTTPX invoked → no bytes reach Ollama / connection fails | Dispatch marker; local exception | Unknown by default. Only transport-level evidence proving zero possible delivery can resolve non-dispatch; no generic connect error classification. |
| 4 | Ollama receives request → response lost | Dispatch marker, no result | Unknown/block; remote may have executed. Never replay. |
| 5 | Ollama finishes → client times out | Dispatch marker, no result | Unknown/block; timeout reports client observation, not remote cancellation. |
| 6 | Complete response exists in process memory → process dies before SQLite transaction | Dispatch marker, no result payload | Unknown/block; memory is gone. Recover only from a durable response artifact authenticated to attempt; otherwise missing. |
| 7 | SQLite result transaction begins → insert fails | Earlier `IN_FLIGHT` + dispatch marker; transaction rolls back if SQLite recovers atomically | Unknown/block. No next evaluation until reconciliation; no repeat. |
| 8 | Commit returns error; outcome unclear | Either transaction's rows recover or they do not; caller cannot assume either | Stop. Fresh-process integrity/replay inspection; if no provable completed result, retain unknown. Never resend. |
| 9 | SQLite completed transaction returns success → process dies immediately | Result + `COMPLETED` event should both be durable in same transaction | Fresh process accepts completed only after integrity/fingerprint checks; no provider call. |
| 10 | DB completion succeeds → JSON atomic export fails | DB has completed result; JSON may be old/missing | Export-only recovery; never infer again. Existing JSON mismatch must be reconciled before overwrite. |
| 11 | Operator sees unknown; no remote logs exist | Original dispatch marker and unknown preserved | Only `ACCEPTED_UNKNOWN_MISSING` is available; do not label completed/failed or retry. |
| 12 | Two processes start together | One obtains OS lock; other does not | Loser exits before DB mutation/provider construction; verify with real child processes. |
| 13 | Completed evaluation appears in new plan | Completed event plus duplicate evaluation ID | Reject before provider construction; export/read only. |
| 14 | Ledger missing/corrupt/replaced/fingerprint mismatch | File absent or integrity/identity check fails | Block; preserve database artifacts; no automatic initialize/migrate/inference. |
| 15 | Nonempty JSON results file exists without matching ledger | JSON has some prior results but no canonical attempt record | Preserve and block. Do not auto-import, overwrite, or assume result JSON proves all attempts. Human migration review required. |

## 9. Expanded failure-injection test plan

All tests below are proposed; none were executed. Use a fake provider and a separate fake HTTP receiver process whose durable receipt log records request IDs independently from the runner. Use temporary DBs and directories outside the repository, deterministic checkpoints, and kill the runner child with abrupt process termination. Reopen the DB from a fresh Python process and verify event sequence, result hash, and receiver count. These tests demonstrate process-crash recovery on the tested machine/filesystem; they do **not** simulate power loss, lying storage hardware, or prove Ollama's remote execution semantics.

Abbreviations: `I` = `IN_FLIGHT`; `D` = `DISPATCH_INTENT`; `C` = `COMPLETED`; `F` = known `FAILED`; `U` = `UNKNOWN_OUTCOME`; `R` = reconciliation. Result=`none` or a stored result/hash. Provider count is the receiver's durable request count for that evaluation.

| Test | Initial state / injection point | Fake receiver reached? | Expected durable event history | Result payload | Restart behavior | Expected call count | Reconciliation? | Invariant |
|---|---|---:|---|---|---|---:|---|---|
| Crash before `IN_FLIGHT` | `PLANNED`; kill before begin transaction | No | plan only | none | Can begin the first attempt after checks | 0 before restart; 1 after normal continuation | No | I1, I5 |
| Crash after `IN_FLIGHT` | Commit I; kill before callback | No | I only | none | Block; explicit `CONFIRMED_NOT_DISPATCHED`; same attempt ID only | 0 before; at most 1 after approval | Yes | I1, I2, I8 |
| Crash after `DISPATCH_INTENT` | Commit D; kill immediately before HTTPX line | No | I,D | none | Treat as U; no second call, since local state cannot prove handoff did not happen | 0 | Yes, close as missing unless stronger evidence | I2, I3 |
| Dispatch-marker commit error | Inject an error after SQLite may have committed D but before callback returns | No; provider must not call `send()` after callback error | I only, or I,D depending on commit recovery | none | Stop; inspect in a fresh process; if D exists treat conservatively as U; no request on restart | 0 observed; no subsequent call for this eval unless absence of D is verified and reconciled | Yes if D/commit outcome is uncertain | I1, I2, I10 |
| Crash after fake receiver receipt | Receiver durably logs request, then kill runner before response persistence | Yes | I,D | none | U/block; request ID/count preserved outside runner DB | 1 | Yes | I3, I5 |
| Request handed to fake transport but receiver records no bytes | Kill/fault transport after `httpx.post` entered but before fake server receipt | No | I,D | none | U/block; absence of receiver log is not proof transport could not deliver | 0 observed; no further calls | Yes | I2, I3 |
| Timeout after possible dispatch | Receiver records request, then transport raises read timeout | Yes | I,D,U if append succeeds | none | Block; never reissue | 1 | Yes | I3, I5 |
| Known local provider failure | Invalid request detected before callback/HTTP | No | I,F (or explicit predispatch rejection event) | error metadata | Continue only with untouched evaluations | 0 for failed eval | No if terminal evidence is complete | I1, I3 |
| Definitive remote rejection | Fake receiver sends response explicitly designated by test contract as pre-inference reject | Yes | I,D,F with response body/hash | rejection record | No retry; continue other untouched evals | 1 | No | I2, I3 |
| Result insert failure | Receiver returns full response; fail DB insert after receipt | Yes | I,D; transaction rollback | none | U/block; no repeat | 1 | Yes | I3, I4 |
| Commit ambiguity after response | Inject commit exception after SQLite commit has possibly completed | Yes | Fresh DB shows either I,D or complete result+C; otherwise integrity failure | present only if recovered complete tx | Stop current process; fresh-process check; no provider repeat | 1 | Yes unless exact committed C recovered | I3, I4, I5 |
| Crash at result/terminal write boundary | Crash inside transaction between payload insert and C event | Yes | Either prior I,D only or transaction containing both payload+C | none or complete, never half-completion | U/block if rollback; accept C if full transaction recovered | 1 | Only rollback/unknown case | I4 |
| Crash after successful C commit | Commit C, then terminate before next item/export | Yes | I,D,C | present/hash-valid | Continue at next planned eval; export if needed | 1 | No | I4, I5 |
| JSON export failure | Seed committed C; inject replace/access-denied failure | Prior request already reached | I,D,C | present in DB; JSON stale/missing | Retry export only; no provider construction for completed eval | 1 total | No | I4, I5 |
| Corrupt/truncated DB or WAL | Copy valid DB then truncate/corrupt test copy | No new call | Read/integrity failure; retain artifact | not trusted | Fail closed; no auto-repair or new DB | 0 | Human review | I10 |
| Duplicate evaluation ID | Duplicate `(revision, case, arm)` in plan/insert | No | Prior history unchanged; unique check fails | unchanged | Abort before provider construction | 0 new calls | No | I6, I7 |
| Duplicate attempt ID | Reuse UUID for a second attempt record | No | Prior event unchanged; unique check fails | unchanged | Fail closed | 0 | No | I7, I8 |
| Two-process startup | Start two child runners with a barrier at lock acquisition | Only lock owner can reach receiver | One run-owner event/lock holder | One writer only | Loser exits; after winner death OS releases lock and path remains reusable | At most 1 request per eval | No | I9 |
| 25th planned evaluation | Supply 25 IDs before provider creation | No | Plan rejected; no dispatch event 25 | none for extra | Fail before provider | 0 for invalid plan | No | I6 |
| Replay completed evaluation | Seed I,D,C; request same evaluation again | No | History unchanged | prior result retained | Reject duplicate, export/read only | Prior count stays 1 | No | I2, I5 |
| Replay failed evaluation | Seed I,F; request same evaluation again | No | History unchanged | failure retained | Reject under zero retries | Prior count unchanged (0 or 1 per failure type) | No | I2, I5 |
| Replay unknown evaluation | Seed I,D,U; request same evaluation again | No | Unknown history unchanged | missing | Block until reconciliation; never replay even after accepting missing | Prior count unchanged | Yes | I3, I5, I8 |
| Reconcile confirmed non-dispatch | Seed I without D; invariant verified; append reviewer decision | No before authorized send | I,R(`CONFIRMED_NOT_DISPATCHED`), then same attempt may add exactly one D | none before send | Allow one first dispatch with same attempt ID after approval; forbid new attempt ID | 0 then at most 1 | Yes | I1, I2, I8 |
| Attempt to confirm non-dispatch after D | Seed I,D; operator requests `CONFIRMED_NOT_DISPATCHED` without authoritative remote evidence | No new call | I,D,U/R rejected or U accepted-missing | none | Reject requested disposition; unknown remains | Prior count unchanged | Yes | I3, I8 |
| Reconcile unresolved as missing | Seed I,D,U; append reviewer/evidence/reason | No | Original events + R(`ACCEPTED_UNKNOWN_MISSING`) | none | May continue other planned evaluations only | No repeat | Yes | I3, I5, I8 |
| Returned schema-invalid response | Receiver returns a full body that fails parser/schema | Yes | I,D,C with validation error and raw-body hash | present, `valid:false` | Continue; never retry | 1 | No | I2, I4 |
| Nonempty JSON without ledger | Seed nonempty legacy results, DB absent | No | No ledger created | JSON preserved | Block; no auto-import/overwrite | 0 | Human migration review | I10 |
| Missing/mismatched run fingerprint | Seed DB with other revision/config/code hash | No | Existing ledger unchanged | unchanged | Block before provider construction | 0 | Human review | I7, I10 |
| Disk full / ledger commit failure before dispatch | Inject write/sync error at I or D commit | No | Either no I or unresolved I; never call transport | none | Stop; preserve/review DB; do not create fresh DB | 0 | Yes if commit uncertain | I1, I10 |

For cross-process tests, use an independent fake receiver to distinguish “runner called its fake object” from “request reached the server.” A normal unit test that raises an exception in the same process cannot establish that receiver-side effects survive the caller crash. Hard process termination is stronger for process-level recovery, but cannot simulate hardware cache loss or power failure; `synchronous=FULL` behavior still requires filesystem/VM fault testing and careful limits on claims.

## 10. Experiment identity and protocol approval

The ledger's immutable run fingerprint should include the parameters that define which evaluation was performed and what request was sent:

- Original commit ID and hashes of frozen registry, source/docs blobs, labels identity (hash only; never investigator context), and each evidence package.
- Six case IDs, arm definitions, per-case arm execution order, and plan serialization.
- Exact current/layered prompt content hashes; canonical serialized schema hashes; response validator and scorer-independent runner code hashes.
- Model tag and full installed model digest; Ollama version; provider name and provider implementation hash.
- Request options: context, temperature, thinking, requested max output, *effective* `num_predict` after `output_budget()`, timeout, redirects, retry policy, endpoint class (local Ollama), and canonical request payload hash. Do not store secrets.
- Runner/provider implementation identity (file hashes or a clean commit plus verified clean-tree status), Python version, SQLite library version, and exact installed versions of HTTPX, Pydantic, and other request/schema libraries. `requirements.txt` ranges are insufficient for exact environment identity.

Operational audit metadata should separately record start/end times, host OS, Python executable, process ID, local filesystem/database path, measured latency/token usage, lock acquisition, and whether hardware metadata was available. Capture hardware if relevant to latency, but do not silently turn it into a new success condition. Model digest and effective generation options are experiment-defining; timestamps and host diagnostics are provenance/audit fields.

At startup, recompute the fingerprint and compare byte-for-byte/hash against the ledger run record before constructing the provider. Any mismatch (including modified untracked runner/provider files, prompt/schema/code hashes, model digest, or effective options) blocks. Do not “resume” under a new fingerprint, silently update the ledger, or treat a new run as the same experiment.

Protocol items still needing explicit prospective approval include Document 56's A/B raw-output estimand, cross-pair interpretation, five-category scoring vocabulary and operational rubric, fixed full model digest/version, numerical output cap and timeout, immutable source identity clarification, interpretation limits, evaluator priming disclosure/case-specific cues, and the new attempt-ledger/crash policy. Document 57 must remain evaluator-only. No threshold or winner rule may be added. Do not alter the pinned original preregistration.

## 11. Classified findings and minimal corrections

### BLOCKER findings

| ID | Finding and failure timeline | Affected locations | Smallest safe correction | Proof test |
|---|---|---|---|---|
| B1 | **No ledger exists in current code.** `execute()` dispatches, then process dies before JSON write; empty template remains and a later `main()` accepts it and resends the evaluation. | `scripts/evaluate_m4b3.py:89–109`, `110–128`; Document 58 §§1,3 | Implement durable attempt events and startup gating before any provider construction; do not rely on results JSON to infer attempts. | Child process killed after fake receiver receipt; fresh run must block/reconcile with receiver count one. |
| B2 | **M4B3 execution can bypass `main()`.** Import `execute(plans, provider)` and invoke with live `Provider`; no template/model/ledger gate is enforced. | `scripts/evaluate_m4b3.py:89–109`; `tests/test_m4b3_harness.py:5–6,84–92` | Make live execution require a ledger-owned single-use dispatch capability and validated run session; remove arbitrary live provider/plan injection from execution API, retaining test seams that cannot reach network. | Direct API invocation with real/transport-spy provider must be rejected without ledger permit; instrument all POST paths. |
| B3 | **`CONFIRMED_NOT_DISPATCHED` transition is underspecified.** After I commits and before POST, recovery has an attempt ID but no exact rules for resuming/reusing it. After D commits but before POST, local evidence cannot distinguish no POST from an actual request. | Document 58 §§2,5; prospective amendment 56 §3.8 | Add explicit `READY_TO_DISPATCH` state for I-without-D only; same attempt ID; one unique D marker; prohibit confirmed-not-dispatched after D absent authenticated evidence. | Crash after I and after D separately; assert same-ID first dispatch only in first case, zero replay in second. |
| B4 | **No single source of truth/ambiguous commit policy.** Multiple event/state/result tables can diverge; commit can raise after remote inference and may have committed. | Document 58 §§3–5; future DB writer | Make append-only event log canonical; store result and C event in one transaction; on commit error stop/reopen/reconcile; never dispatch or replay based on caller exception alone. | Fault after commit syscall, reopen in fresh process; verify log replay and no second provider receipt. |
| B5 | **Provider callback is not mandatory.** General `Provider.structured()` and imported `execute()` can call transport without it; future callback in only the runner would be bypassable. | `blackbox/providers.py:50–59,61–109`; runner 89–105 | Route all M4B3 live requests through a ledger-bound provider method that requires one-use permit; keep current generic app routes separate; make actual transport invocation singular and instrumentable. | Enumerate/spy all M4B3 call paths; direct Ollama/Gemini/provider paths reject M4B3 context without permit. |
| B6 | **Startup accepts no-ledger histories.** Existing empty JSON template can survive an unrecorded first request; an old nonempty JSON file may not have matching ledger. | runner 66–70, 110–128; Document 58 §§4,7 | Require an existing valid run ledger after the first begin; absence/corruption/mismatch/nonempty legacy JSON blocks. Never auto-create empty DB or import/overwrite result JSON. | Missing DB + empty template after simulated prior call; nonempty JSON + missing DB; both yield zero provider calls. |

### MAJOR findings

| ID | Finding | Smallest safe correction | Test |
|---|---|---|---|
| M1 | Provider exceptions and validation errors are caught together at `execute:103–106`. `done_reason=length`, HTTP status, malformed body, and post-send timeouts are not distinguished. | Introduce typed transport outcomes with dispatch phase and complete-response evidence; default all post-dispatch ambiguous failures to unknown; preserve full response body. | Failure-class table cases, including invalid but fully returned response must complete without retry. |
| M2 | Run fingerprint omits runner/provider bytes, exact dependency versions, effective dynamic output budget, and canonical request hash; broad requirements ranges do not pin the environment. | Store run fingerprint plus per-request payload hash and effective `num_predict`; block on mismatch. Keep operational metadata separate. | Change each input independently; startup must reject changed fingerprint. |
| M3 | Proposed Windows lock not specified/tested for stale lock path, handle inheritance, replacement race, process death, or target filesystem. | Hold a stable OS byte-range/file lock with non-inheritable handle for full run; never delete lock pathname; test actual Windows two-process behavior. | Contending child processes; kill owner; verify loser/next process behavior and handle closure. |
| M4 | Commit-ack error after result write can be mistaken for failure and replayed; SQLite's local transaction cannot know remote completion. | Any post-dispatch persistence/commit ambiguity blocks; inspect DB in fresh process; absent conclusive durable response, keep unknown. | Inject commit-after-write acknowledgment error and count remote receipts. |
| M5 | Current JSON output uses non-atomic `write_text`; derived export/legacy compatibility is not fully specified. | Keep DB canonical; export to same-directory temp + flush + replace; preserve envelope; never overwrite non-template JSON without matching ledger identity. | Fail export at each step; DB remains complete; exporter retries without provider call. |
| M6 | 24 limit validated only by `plan()`; `execute()` accepts arbitrary/repeated plans. | Persist exact 24 planned IDs and unique constraints/count; reject additional or repeated IDs before provider construction. | 25th item and duplicate case/arm plan tests. |
| M7 | Current M4B3 script, tests, and documents are untracked; dependency versions are ranges. The working tree itself is not a reproducible implementation identity. | Fingerprint the exact working file bytes and resolved runtime versions, or require reviewed clean commit before inference. | Modify an untracked runner byte or installed package version; fingerprint mismatch blocks. |

### MINOR findings

- JSONL remains a possible simpler format, but partial trailing records and explicit multi-record transition recovery are more error-prone here than one small SQLite DB.
- A hash chain without a trusted external chain head is not meaningful protection against the local operator who controls the database; invariant checks and backups are more useful for this prototype.
- “Append-only” should describe application/database behavior, not imply protection from a local administrator who can replace the file.

### ACCEPTABLE elements

- The proposed local SQLite approach is proportionate for 24 evaluations if same-host filesystem and locking assumptions are tested.
- Storing result and completion in one SQLite transaction is the right direction and avoids an atomic multi-file commit with JSON.
- Keeping the existing results JSON as a derived export can preserve existing envelope shape while making recovery independent of that file.
- No automatic retry and no claim of exactly-once remote execution are appropriate constraints.

## 12. Recommended minimal architecture

1. One M4B3 CLI orchestrator acquires a stable OS lock before touching provider/database state, computes and validates the exact run fingerprint, opens the existing ledger (or creates one only for a clearly initialized, never-started approved run), validates integrity, replays the canonical event log, and rejects unresolved/mismatched histories.
2. Persist `PLAN_REGISTERED` for the exact 24 eval IDs and arms/order. Unique index on `(run_id, evaluation_id)`; unique attempt ID; unique dispatch-intent per evaluation/attempt; maximum 24 dispatch intents. A completed/failed/unknown evaluation cannot be re-planned as new.
3. For an evaluation, insert and commit `IN_FLIGHT`. Provider constructs the complete request locally. At the only Ollama transport boundary, it asks the ledger to commit one `DISPATCH_INTENT` for the same attempt ID. It calls `httpx.post` only after commit returns success. No other M4B3 network call path is allowed.
4. One outbound HTTP invocation, no redirects, no client retry transport, no app retry, no fallback. Note lower-level TCP can retransmit packets; the property is one HTTP request invocation, not proof of one model execution.
5. Preserve full response body/status/usage. A complete returned response (even invalid/truncated-at-generation) is an evaluation result with validation metadata. Post-dispatch I/O errors without a complete response become unknown.
6. Insert raw response/result and terminal event into the canonical event log in one transaction. If that commit errors, stop. Restart/reconcile. Never issue another provider call to “repair” persistence.
7. Export the legacy JSON envelope only from committed ledger records using temp+replace. A stale/nonempty file with no matching ledger blocks and is preserved for manual reconciliation.
8. Human reconciliation appends reviewer/evidence/disposition. Only I-without-D may become same-attempt `READY_TO_DISPATCH` after proof and explicit authorization; D-present ambiguity can only be resolved by authenticated evidence or accepted as missing. Never erase events or permit a second D.

## 13. Exact file-by-file later implementation plan

No implementation edits are authorized by this review.

| File | Later change |
|---|---|
| `scripts/evaluate_m4b3.py::plan` | Canonical plan IDs, exact run fingerprint inputs, validate exactly six × four in registered order. |
| `scripts/evaluate_m4b3.py::main` | Acquire process lock first; validate existing ledger/result pair and fingerprint before provider construction; block missing/corrupt/unresolved/mismatched state; no silent initialization. |
| `scripts/evaluate_m4b3.py::execute` | Require ledger session/one-use permit, create attempt, handle typed provider outcomes, persist event/result transactionally, count budget, no catch-all retry/replay. |
| `blackbox/providers.py::Provider.structured` around lines 54–109 | Introduce M4B3-specific mandatory dispatch hook/typed outcomes at line 81; preserve full response/error details; ensure retry/redirect/fallback policy explicit for each branch. |
| `tests/test_m4b3_harness.py` | Extend fake provider and add temp-DB, crash subprocess, independent receiver, lock contention, corruption, commit ambiguity, fingerprint, and no-replay tests. |
| Future SQLite schema/module | Implement canonical append-only event log, event replay validator, unique constraints, result payload hashes, backup/read-only inspection; not present today. |
| `data/m4b3-results.json` | Keep current envelope as derived export; do not change labels/template during ledger implementation without review. |
| `requirements.txt` / lock data | Decide whether an exact dependency lock is needed for reproducibility; any dependency changes require separate approval. |

## 14. Document 56/57 review and approval checklist

Document 56 §3.8 currently handles the broad crash risk, but the wording should be tightened to distinguish a definitively known failure from a possible dispatch. Recommended addition (not applied):

> A timeout, connection loss, partial response, or persistence error after transport may have been entered is `UNKNOWN_OUTCOME`, not `FAILED`, unless authenticated evidence proves a definitive terminal non-completion. `FAILED` is reserved for a known terminal failure. Reconciliation may authorize the original planned dispatch only when the ledger proves no `DISPATCH_INTENT` was committed and the mandatory-boundary invariant establishes that HTTP transport was never entered; it must reuse the same attempt ID and may create only one dispatch intent. Once `DISPATCH_INTENT` exists, human reconciliation must not authorize another request under the current zero-retry protocol. If remote outcome remains uncertain, preserve the evaluation as missing/unknown.

Document 56 and 57 are unapproved. Before implementation or inference, a human must approve the amendment's methodological changes, evaluator disclosure, this attempt policy, SQLite/locking choices, run fingerprint definition, and stop/reconciliation rules. The evaluator rubric remains evaluator-only. No result threshold or winner rule is authorized.

## 15. Approval checklist

- [ ] Resolve BLOCKERS B1–B6 in a reviewed design.
- [ ] Approve exact state transitions, especially `IN_FLIGHT` without dispatch marker vs `DISPATCH_INTENT` committed.
- [ ] Approve one canonical event source of truth and commit-ambiguity policy.
- [ ] Approve provider boundary and prove every M4B3 request path uses it.
- [ ] Approve Windows lock mechanism only after two-process tests on the target local filesystem.
- [ ] Approve immutable run fingerprint components and resolved dependency-version capture.
- [ ] Approve behavior for old JSON/nonempty output without a ledger; preserve and block by default.
- [ ] Implement the proposed test matrix using only fake providers/receivers; no live Ollama needed.
- [ ] Keep Documents 56/57 as drafts until explicit human approval; no inference before that approval.

## 16. Beginner-friendly explanation

This is a distributed-systems problem because the runner's SQLite file and Ollama are two separate systems. The runner can commit “I am about to send” and then send an HTTP request, but it cannot atomically commit that database row together with Ollama's model execution. If the request reaches Ollama and the response is lost, the local computer cannot tell from a timeout whether the model ran. Retrying could duplicate the evaluation.

SQLite WAL records changes in a write-ahead log before merging them into the main database. `synchronous=FULL` asks SQLite to sync that log at commit, which makes the commit more durable when the OS and storage honor the sync. It still cannot include the remote inference in the same transaction. (SQLite explains the extra WAL sync for `FULL` in its [PRAGMA documentation](https://www.sqlite.org/pragma.html#pragma_synchronous).)

Saving a result and marking it complete are separate *logical facts*. The database should put the response/result and `COMPLETED` event in one transaction so neither is committed alone. The existing JSON file is a separate file, so it should be an export that can be regenerated without another inference.

An append-only event trail lets a reviewer see the original `IN_FLIGHT`, any dispatch marker, and later reconciliation. It prevents the software's normal path from silently rewriting “unknown” into “failed.” It is not tamper-proof against a local administrator.

A fake-provider crash test is stronger than a normal function test because it can kill the runner process after an independent fake server has durably recorded receipt, then open the database in a fresh process. It tests what survived the crash and whether restart sends again. It cannot prove power-loss behavior or what real Ollama does after a lost connection.

In this repository, the current runner plans 24 items and calls Ollama at `scripts/evaluate_m4b3.py:103–104`; it writes partial results afterward at line 108. The provider sends HTTP at `blackbox/providers.py:81–83`. There is no ledger yet. SQLite, the callback, reconciliation events, and crash tests are all proposals. The hardest remaining engineering problem is enforcing one durable, one-use path from a particular experiment/case/arm to the HTTP transport while preserving uncertainty whenever local and remote outcomes cannot be joined.

## 17. Final Git status comparison and action log

| Snapshot | Modified tracked | Untracked | Notes |
|---|---:|---:|---|
| Before review/report | 18 | 428 | User's reported baseline; requested output absent |
| After report | 18 | 429 | Exactly one additional untracked path: `research/59_M4B3_LEDGER_RED_TEAM_REVIEW.md` |

The only intentional repository write in this task was adding this Markdown report. I did not modify source, existing documents, fixtures, labels, prompts, schemas, registry, or result data. No tests or inference were run. The graphify query used to comply with repository instructions produced no additional Git status entries in the pre-report count. Because the pre-existing tree was already extensively dirty, I cannot certify byte-for-byte that every pre-existing dirty file was untouched from Git status alone; I did not write to those files, and the final status count differs only by this report.

**Final status:** `M4B3_LEDGER_RED_TEAM_REVIEW_COMPLETE — IMPLEMENTATION_NOT_STARTED — LIVE_EXECUTION_NOT_AUTHORIZED`
