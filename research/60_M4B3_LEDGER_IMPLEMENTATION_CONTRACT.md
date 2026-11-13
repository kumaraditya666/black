# M4B.3 Attempt Ledger: Final Implementation Contract

**Document status:** Technical design for human implementation review  
**Implementation status:** Not implemented  
**Experiment status:** Documents 56 and 57 remain drafts; live inference is not authorized  
**Design verdict:** `DESIGN_CLOSED — READY_FOR_HUMAN_IMPLEMENTATION_REVIEW`

This contract resolves the technical design questions for a future M4B.3 attempt ledger. It does not approve implementation, amend the original preregistration, or authorize inference. The frozen experiment remains six registered cases × four registered arms (A–D), at most 24 evaluations, the original arm order, the local `qwen3.5:4b` model and registered settings, and zero automatic retries. Any approval required by Documents 56/57 remains a separate human decision.

## 1. Executive decision

Use one local SQLite database as the single authoritative history for one initialized M4B.3 run. The append-only event log is the sole source of evaluation state and result content. The frozen plan and run manifest are immutable inputs, not a second state store. Reconstruct every evaluation state by replaying events; do not persist mutable current-state or result projections in separate tables.

Initialize the database through an explicit no-inference command. Normal `--run-live` must refuse to create a missing database. An M4B.3 request is sent only through one ledger-bound Ollama dispatcher, after a complete HTTP request is prepared locally and a unique `DISPATCH_INTENT` event commits successfully. The dispatcher calls the HTTP transport once. A completion event stores the raw complete response and its normalized/validated result in one SQLite transaction. Any ambiguous post-dispatch outcome is unknown and never replayed.

For the one recoverable pre-dispatch case, a reviewer may authorize the original planned request only when an `IN_FLIGHT` event exists, no `DISPATCH_INTENT` exists, and the mandatory-boundary invariant has been proven by implementation tests. Append `CONFIRMED_NOT_DISPATCHED`, resume the **same** attempt ID, and allow the one dispatch marker and one transport entry. A second attempt ID is never allowed for an evaluation. Once `DISPATCH_INTENT` exists, no local reconciliation can authorize another request under this protocol.

This contract chooses a local policy that trades completion rate for no silent replay: if state is uncertain after the dispatch marker, keep that evaluation missing/unknown, require reconciliation, and continue only with untouched planned evaluations after the reviewer explicitly closes the block. Do not claim exactly-once remote inference.

## 2. Scope, existing architecture, and six-blocker resolution

### 2.1 Verified current source behavior

These are static findings from the current working tree, not a tested ledger implementation.

| Location | Current behavior |
|---|---|
| `scripts/evaluate_m4b3.py::plan`, lines 35–61 | Reads registry, labels, source, and documentation from the immutable commit; verifies registered source hashes/order; builds 24 plans. The plan exists only in process memory. |
| `scripts/evaluate_m4b3.py::validate_template`, lines 66–70 | Requires `template_only_no_model_calls`, empty `results`, and matching revision. The empty template cannot establish that an earlier request was never dispatched. |
| `scripts/evaluate_m4b3.py::execute`, lines 89–109 | Accepts arbitrary `plans` and provider; invokes `provider.structured()` at 103–104; catches provider, JSON, and validation exceptions together at 106; writes partial JSON only after each response/error at 107–108. |
| `scripts/evaluate_m4b3.py::main`, lines 110–129 | CLI has `--dry-run` and `--run-live`; normal live path checks the template, verifies local model metadata, hardcodes `Provider('ollama', MODEL)`, calls `execute`, and writes the final JSON. |
| `blackbox/providers.py::Provider.structured`, lines 54–92 | Builds the Ollama payload and invokes top-level `httpx.post` at 81–83, with `follow_redirects=False` and `trust_env=False`. It processes status/JSON/content at 84–91. No ledger hook is present. |
| `blackbox/providers.py`, lines 93–120 | General provider supports Gemini as well as Ollama. This is not the runner's normal M4B.3 path, but `execute()` currently accepts an arbitrary provider object. |
| `tests/test_m4b3_harness.py`, lines 63–92 | In-process mock counts calls and exercises all 24 plans, including one invalid response. It does not test crash recovery, cross-process locking, or a durable ledger. |
| `data/m4b3-results.json` | Empty template with `status`, `revision`, `arms`, and `results`. It is not evidence that no uncheckpointed request occurred. |
| `requirements.txt`, lines 1–6 | Dependency ranges are broad, including `httpx>=0.27,<1`; exact installed dependency versions are not locked here. |

The runner, M4B.3 harness test, results template, and research Documents 50–59 are untracked in the inspected working tree. The provider file is tracked and was not listed as changed in the initial status. Fingerprint exact working-copy bytes; do not represent untracked source as a clean committed implementation.

### 2.2 Blocker resolution table

| Blocker | Contract resolution | Affected future location | Proof test |
|---|---|---|---|
| B1 — No ledger | Add an explicit no-inference `--initialize`; require an existing valid ledger for live mode; event log stores attempts/results. | New `scripts/m4b3_attempt_ledger.py`; runner `main()` | Missing ledger after init blocks before dispatcher construction; crash/reopen tests. |
| B2 — Direct execution bypass | Replace arbitrary live `execute(plans, provider)` with a run-session API requiring a validated approved manifest and ledger-issued single-use dispatch permit. M4B3 uses only the dedicated dispatcher. | Runner `execute`/`main`; provider boundary | Direct call with arbitrary plan/provider rejected; only session-bound dispatcher can reach fake receiver. |
| B3 — Reconciliation ambiguity | `IN_FLIGHT` without `DISPATCH_INTENT` may be explicitly reconciled to `READY_TO_DISPATCH` for the same attempt ID. Any `DISPATCH_INTENT` consumes dispatch eligibility forever. | Ledger event replay and `reconcile()` | Kill after I and after D; only I/no-D can be resumed once using same attempt ID. |
| B4 — Database source of truth | Event log alone determines attempt states and result payloads; no mutable current-state/result tables. Plan tables are immutable manifest inputs. | New ledger module/schema | Rebuild states by replay; malformed ordering or hash disagreement blocks. |
| B5 — Mandatory provider boundary | Construct/serialize request first; commit D through ledger; call the one M4B3 `Client.send()` once only after commit success. No redirects, transport/application retries, or fallback. | `blackbox/providers.py` M4B3-specific dispatcher | Instrument actual fake HTTP receiver; every received request has one prior durable D; direct generic M4B3 call rejected. |
| B6 — Fail-closed startup | Explicit initialization; live mode never auto-creates ledger; check fingerprint, DB integrity, event replay, results/export relation, and lock before provider construction. | Runner `main()` plus ledger startup validation | Missing/corrupt/mismatched/unresolved/nonempty-JSON-without-ledger cases all produce zero receiver calls. |

## 3. Formal state machine

`PLANNED` is an evaluation in the immutable registered plan with no attempt. `BLOCKED` is an admission/run condition, not a persisted evaluation state. The event log stores transitions; current state is computed by replay.

| Current state | Event | Preconditions | Next state | Database operation | Provider action | Forbidden action |
|---|---|---|---|---|---|---|
| No run | `INITIALIZE_RUN` | Explicit initialization mode; approved protocol evidence supplied; no DB or sidecars; exact frozen plan; exact empty results template | Run initialized; evaluations `PLANNED` | Create schema, manifest, 24 immutable plan rows, run/plan events in one transaction | None | Any model/HTTP call |
| `PLANNED` | `BEGIN_ATTEMPT` | Run lock held; fingerprint matches; plan entry is exact; prepared request bytes/hash/config fixed; no earlier attempt | `IN_FLIGHT` | Insert one UUID attempt event; commit success required | None | Provider construction/dispatch before commit |
| `IN_FLIGHT` | `DISPATCH_INTENT` | Same attempt ID; full HTTP request built and serialized; no previous D; request hash equals attempt snapshot; commit succeeds | `DISPATCH_INTENT` | Append one unique D event; `BEGIN IMMEDIATE`; commit must return success | After commit returns success, call transport once | Call before commit; second D; second HTTP invocation |
| `IN_FLIGHT` on restart, no D | `RECONCILE_NOT_DISPATCHED` | Replay/integrity passes; mandatory no-bypass invariant proven; no D for eval; reviewer explicitly authorizes original dispatch | `READY_TO_DISPATCH` | Append reconciliation event with reviewer/evidence/approval; same attempt ID retained | None during reconciliation | New attempt ID; automatic resume; relying only on no server receipt |
| `READY_TO_DISPATCH` | `DISPATCH_INTENT` | Same original attempt ID; unchanged request/fingerprint; unique D absent | `DISPATCH_INTENT` | Append/commit D; unique index allows at most one | One transport entry after successful commit | New attempt or second request |
| `IN_FLIGHT` | Known local terminal error before transport | Code proves no dispatcher/send call occurred; state still has no D | `FAILED` | Append F event with typed error and no-dispatch proof | None | Retry or continue same evaluation |
| `DISPATCH_INTENT` | Complete HTTP response body | Response body is fully received and retained | In-memory response processing only | No state change until result transaction | No further HTTP call | Retry due to status, JSON, schema, empty response, or length error |
| `DISPATCH_INTENT` | `COMPLETE_RESULT` | Full response retained; validation attempted and represented, successful DB commit | `COMPLETED` | One transaction appends C with raw body/hash, normalized output or validation failure, usage/latency | None | Commit result and completion separately |
| `DISPATCH_INTENT` | `KNOWN_REMOTE_FAILURE` | Full authenticated response and explicitly approved provider semantics prove inference did not execute | `FAILED` | Append F with response bytes/hash and classification evidence | None | Generic HTTP status treated as proof; retry |
| `DISPATCH_INTENT` | Timeout/reset/partial body/process loss/ambiguous response | No complete result or authoritative failure proof | `UNKNOWN_OUTCOME` (explicit event if possible; otherwise derived from D without terminal event) | Append U if DB available; if not, leave D as durable unresolved state | None | Retry or generic `FAILED` classification |
| `UNKNOWN_OUTCOME` | `CONFIRMED_COMPLETED` | Recoverable complete response/result tied to attempt and hash-verified | `COMPLETED` | Append C/reconciliation evidence; no HTTP | None | Reissue request |
| `UNKNOWN_OUTCOME` | `CONFIRMED_FAILED` | Authenticated evidence proves terminal non-completion | `FAILED` | Append reconciliation/F evidence; no HTTP | None | Retry |
| `UNKNOWN_OUTCOME` | `ACCEPTED_UNKNOWN_MISSING` | Reviewer accepts unresolved outcome as missing | Remains `UNKNOWN_OUTCOME`, administratively closed | Append reconciliation only | Continue only with other untouched plan entries | Rewrite U as success/failure; replay eval |
| `COMPLETED` or `FAILED` | Same evaluation appears in later invocation | Existing event history matches identity | Same terminal state | Read/export only | None | Re-plan as new attempt or call provider |
| Any | Missing/corrupt/mismatched DB, result pairing, or lock conflict | Startup validation fails | `BLOCKED` | No writes except read-only diagnostics; preserve files | None | Auto-initialize, repair, import JSON, infer |

### Required case resolutions

- **A — Crash after I, before D:** There was no transport entry if and only if every M4B3 network path is forced through the dispatcher and the dispatcher cannot call `send()` without committed D. Startup blocks. A reviewer records `CONFIRMED_NOT_DISPATCHED`, authorizes the one original dispatch, and transitions the same attempt to `READY_TO_DISPATCH`. The same attempt ID is reused; no second attempt row is created. One D can then be committed. If that invariant has not been implemented and tested, this reconciliation is forbidden.
- **B — Crash after D, before/during HTTP:** D is conservatively consumed. A restart cannot tell “crashed before `send()`” from “request reached server.” Derive U and never permit a second request based only on local records.
- **C — Timeout after remote receipt:** append U if possible. If process dies before U, D without C/F still replays as U. Do not retry; the model may already have completed.
- **D — Response received, result persistence fails:** Response in RAM is not durable evidence. D remains; restart derives U unless the C transaction is recovered intact. Never reissue.
- **E — SQLite commit error:** Never assume rollback. Stop; close/abandon the connection; a fresh process opens without create, checks integrity/schema/fingerprint, replays events, and checks event IDs/payload hashes. If full C and response payload exist and verify, accept C; if only D exists, U; if DB/chain invalid or result is partial, BLOCKED. No commit exception permits another call.
- **F — Completed evaluation appears again:** Unique `(run_id,evaluation_id)` in the plan plus unique attempt/D indexes and replayed C state reject it before dispatcher construction. Export/read only.

## 4. Canonical SQLite schema and constraints

One database represents one approved experiment run. `run_meta` is the immutable run manifest; `planned_evaluations` is immutable plan input; neither stores mutable attempt state. `events` is the only authoritative state/result history. No current-state, attempt-status, or result table is maintained.

Suggested schema (SQLite standard SQL; initialization sets PRAGMAs separately):

```sql
CREATE TABLE run_meta (
    singleton              INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id                 TEXT NOT NULL UNIQUE,
    schema_version         INTEGER NOT NULL,
    run_fingerprint_sha256 TEXT NOT NULL CHECK (length(run_fingerprint_sha256) = 64),
    approved_protocol_sha256 TEXT NOT NULL CHECK (length(approved_protocol_sha256) = 64),
    manifest_json          TEXT NOT NULL,
    initial_results_sha256 TEXT NOT NULL CHECK (length(initial_results_sha256) = 64),
    initialized_utc        TEXT NOT NULL,
    initial_event_hash     TEXT NOT NULL CHECK (length(initial_event_hash) = 64)
);

CREATE TABLE planned_evaluations (
    run_id          TEXT NOT NULL REFERENCES run_meta(run_id),
    evaluation_id   TEXT NOT NULL,
    ordinal         INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 24),
    case_id         TEXT NOT NULL,
    arm             TEXT NOT NULL CHECK (arm IN ('A','B','C','D')),
    prompt_id       TEXT NOT NULL,
    schema_id       TEXT NOT NULL,
    request_spec_sha256 TEXT NOT NULL CHECK (length(request_spec_sha256) = 64),
    plan_json       TEXT NOT NULL,
    PRIMARY KEY (run_id, evaluation_id),
    UNIQUE (run_id, case_id, arm),
    UNIQUE (run_id, ordinal)
);

CREATE TABLE events (
    seq              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id         TEXT NOT NULL UNIQUE,
    run_id           TEXT NOT NULL REFERENCES run_meta(run_id),
    evaluation_id    TEXT,
    attempt_id       TEXT,
    event_type       TEXT NOT NULL CHECK (event_type IN (
        'RUN_INITIALIZED','EVALUATION_PLANNED','IN_FLIGHT',
        'RECONCILIATION','DISPATCH_INTENT','COMPLETED','FAILED',
        'UNKNOWN_OUTCOME','EXPORT_WRITTEN'
    )),
    occurred_utc     TEXT NOT NULL CHECK (substr(occurred_utc, -1, 1) = 'Z'),
    payload_json     TEXT NOT NULL,
    payload_sha256   TEXT NOT NULL CHECK (length(payload_sha256) = 64),
    prev_event_hash  TEXT NOT NULL CHECK (length(prev_event_hash) = 64),
    event_hash       TEXT NOT NULL CHECK (length(event_hash) = 64),
    FOREIGN KEY (run_id, evaluation_id)
        REFERENCES planned_evaluations(run_id, evaluation_id),
    CHECK (
      (event_type IN ('RUN_INITIALIZED','EXPORT_WRITTEN') AND evaluation_id IS NULL AND attempt_id IS NULL)
      OR (event_type = 'EVALUATION_PLANNED' AND evaluation_id IS NOT NULL AND attempt_id IS NULL)
      OR (event_type NOT IN ('RUN_INITIALIZED','EXPORT_WRITTEN','EVALUATION_PLANNED')
          AND evaluation_id IS NOT NULL AND attempt_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX one_attempt_start_per_evaluation
    ON events(run_id, evaluation_id) WHERE event_type = 'IN_FLIGHT';
CREATE UNIQUE INDEX one_attempt_id_per_run
    ON events(run_id, attempt_id) WHERE event_type = 'IN_FLIGHT';
CREATE UNIQUE INDEX one_dispatch_intent_per_evaluation
    ON events(run_id, evaluation_id) WHERE event_type = 'DISPATCH_INTENT';
CREATE UNIQUE INDEX one_completion_per_evaluation
    ON events(run_id, evaluation_id) WHERE event_type = 'COMPLETED';
CREATE UNIQUE INDEX one_failure_per_evaluation
    ON events(run_id, evaluation_id) WHERE event_type = 'FAILED';
CREATE UNIQUE INDEX one_unknown_marker_per_evaluation
    ON events(run_id, evaluation_id) WHERE event_type = 'UNKNOWN_OUTCOME';
CREATE UNIQUE INDEX one_plan_event_per_evaluation
    ON events(run_id, evaluation_id) WHERE event_type = 'EVALUATION_PLANNED';

CREATE TRIGGER events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'event history is append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'event history is append-only'); END;
CREATE TRIGGER plan_no_update BEFORE UPDATE ON planned_evaluations
BEGIN SELECT RAISE(ABORT, 'registered plan is immutable'); END;
CREATE TRIGGER plan_no_delete BEFORE DELETE ON planned_evaluations
BEGIN SELECT RAISE(ABORT, 'registered plan is immutable'); END;
CREATE TRIGGER run_meta_no_update BEFORE UPDATE ON run_meta
BEGIN SELECT RAISE(ABORT, 'run manifest is immutable'); END;
CREATE TRIGGER run_meta_no_delete BEFORE DELETE ON run_meta
BEGIN SELECT RAISE(ABORT, 'run manifest is immutable'); END;
```

Application writer validates transition legality before insert; SQLite indexes enforce uniqueness even if application code is wrong. A trigger may additionally reject a D event unless a matching I exists and there is no prior D, but this is defense in depth: transaction code must replay and validate prior state under `BEGIN IMMEDIATE`. The 24 planned rows, unique `(case_id,arm)`, and unique D per evaluation bound D events to 24. Initialization rejects anything other than the exact 24 registered pairs/order.

`evaluation_id` is deterministic: SHA-256 of canonical `(pinned_revision, case_id, arm)` fields. `attempt_id` is UUID4 created once in the I event. Event IDs are UUIDs and unique. Payload JSON is canonical UTF-8 JSON (`sort_keys=True`, compact separators, finite numbers only); timestamp is RFC3339 UTC ending in `Z`. The application computes payload SHA-256 and a chain hash over canonical event columns plus prior event hash. Startup checks payload hashes, previous-hash links, event hash, contiguous `seq` from 1, and `sqlite_sequence` high-water consistency.

The completed event payload contains the full application-level HTTP response body as base64 plus its SHA-256, HTTP status, safe response metadata, normalized result, validation outcome/error, token usage, latency, attempt/request identity, and effective configuration. This small experiment has at most 24 records, so keeping result and completion in one event is reasonable and guarantees they cannot be committed independently. Never store credentials or authorization headers.

Triggers prevent ordinary application update/delete mistakes, not a local administrator from dropping triggers or replacing the DB. Hashes detect accidental alteration when checked; without an independently trusted checkpoint they do not prove local-admin tamper resistance. This is not a security certification.

## 5. SQLite connection and durability contract

At open:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;       -- assert returned value is 'wal'
PRAGMA synchronous = FULL;
PRAGMA busy_timeout = 5000;
```

Set/verify WAL and synchronous on each writer connection; `foreign_keys` is per connection. Require a tested SQLite version recorded in the run manifest; reject versions below the implementation's approved minimum. WAL is chosen for local crash recovery and read access, not concurrent writers. Keep the DB on a local supported filesystem, not a network share or cloud-sync directory. Do not delete `-wal` or `-shm` files while any connection may be open. Inspect a closed/checkpointed copy or SQLite backup API snapshot, not the active DB file alone.

Use one writer connection owned by the runner thread (`check_same_thread=True`). No worker thread writes to the same connection. Other processes are excluded by the run lock; read-only tools use a backup/snapshot. Each state-changing operation uses `BEGIN IMMEDIATE` so it obtains the SQLite write reservation before replaying latest state and inserting. Busy/locked timeout before D means no provider call; busy/locked after D prevents terminal persistence and leaves the attempt unknown. A local database retry may repeat only a database transaction, never the provider call.

`synchronous=FULL` requests synchronization of WAL commits, improving durability if the OS and storage honor it. It cannot guarantee power-loss survival on hardware/filesystems that lie or lose acknowledged writes. Process-kill tests are not power-loss tests.

## 6. Transaction algorithms and commit recovery

All pseudocode below uses a short write transaction and checks the derived current state by replaying `events` while holding the write reservation. `append_event()` computes canonical payload/hash and links it to the last committed sequence/hash.

### 6.1 Initialize and register the run

Initialization is a separate command that makes no provider or Ollama call.

```text
acquire OS run lock
require ledger DB path absent AND no orphan WAL/SHM files
require results JSON exactly matches empty template, pinned revision, expected arms
require human-approved amendment/rubric evidence; compute approved_protocol_sha256
compute exact run manifest/fingerprint and all 24 registered evaluations
open DB exclusively for initialization
set/verify PRAGMAs; BEGIN IMMEDIATE
create schema/triggers/indexes
insert immutable run_meta row
insert exactly 24 immutable planned_evaluations rows
append RUN_INITIALIZED and 24 EVALUATION_PLANNED events
validate ordering, hashes, constraints; COMMIT
if commit returns success: close cleanly, verify read-only; report initialized, no inference
if any failure/commit error: stop; never delete/recreate; next process performs ambiguous-commit recovery
```

If the path already exists—even if empty, partial, or corrupt—normal initialization refuses it. Human review must preserve the artifact and decide how to recover; no auto-delete. Initialization is allowed only after the prospective protocol has been approved; an approval flag supplied by the same live command is insufficient.

### 6.2 Register/validate exact plan

The initialization transaction stores the six cases, four arms, exact per-case order, request/prompt/schema hashes, source identity, and 24 stable evaluation IDs. `run-live` recomputes them and compares canonical values before provider construction. It never mutates the plan. A repeated/extra case-arm, changed order, or 25th evaluation fails before any request.

### 6.3 Begin one attempt

First validate and fully build/serialize the HTTP request locally; compute its exact body/request hash and effective settings. Then:

```text
BEGIN IMMEDIATE
replay events; require evaluation == PLANNED and no IN_FLIGHT/D/terminal
require run fingerprint and per-request spec hash unchanged
create one attempt_id UUID4
append IN_FLIGHT(attempt_id, request_hash, config hash, started_utc)
validate constraints/hash chain
COMMIT; require success acknowledgment
only now may the dedicated dispatcher be handed this attempt
```

If request construction fails before I, record an operational run failure outside the attempt log or stop; there was no request. If a known error occurs after I but before transport, append terminal F with typed proof that no transport was entered; do not retry that evaluation. A crash after I and before D requires human reconciliation even though the design invariant says no transport was possible; no automatic continuation.

### 6.4 Authorize the one dispatch

The prepared request is immutable. The ledger returns an in-memory `DispatchPermit` only after this transaction commits:

```text
BEGIN IMMEDIATE
replay; require state == IN_FLIGHT or explicitly reconciled READY_TO_DISPATCH
require attempt_id matches I and request hash matches prepared request
require no D for evaluation; require total D < 24
append DISPATCH_INTENT(attempt_id, request_hash, payload hash, effective options)
validate unique index and chain
COMMIT; require success acknowledgment
return one-use permit bound to run_id/evaluation_id/attempt_id/request_hash
```

If commit raises or acknowledgment is ambiguous, the provider must not call `send()`. A D may nevertheless be present on recovery; in that case the evaluation is conservatively unknown and cannot be replayed. The permit is consumed before entering HTTP transport and cannot be re-used in memory.

### 6.5 Send once and classify the outcome

Only `M4B3OllamaDispatcher.send_prepared(request, permit)` can reach HTTP for the experiment. It verifies permit/session/request hashes, marks the permit consumed, calls `client.send(request)` exactly once, with redirects disabled and a transport configured for zero retries. There is no fallback provider. Generic `Provider.structured()` is not an M4B3 dispatch interface.

Return a typed outcome, not a generic exception:

```text
TransportOutcome {
  phase: PREPARED | SEND_ENTERED | RESPONSE_HEADERS | BODY_COMPLETE
  dispatch_intent_event_id, request_hash
  transport_entered: bool
  response_received: bool
  response_body_complete: bool
  status_code: int | null
  raw_body: bytes | null
  safe_headers: map
  transport_error_type: string | null
  usage: map | null
}
```

Exceptions before `SEND_ENTERED` can be proven no-send only if the single path's control flow guarantees `Client.send` was not called. Any error after entering `send`, timeout, reset, or incomplete body is unknown by default. Generic HTTP errors are not evidence that inference did not happen. Only a complete response class with an explicitly reviewed provider contract may be recorded F.

### 6.6 Persist complete response

Once the full HTTP body is present, parse/validate it without making another request. Parsing/validation errors become data in the completion record; they do not escape as a retry signal.

```text
BEGIN IMMEDIATE
replay; require latest state == DISPATCH_INTENT (or U recoverable with exact result evidence)
insert one COMPLETED event containing raw body/base64+hash, normalized output or validation error,
  status/usage/latency/request identity/config fingerprint
validate event and hash chain
COMMIT; require success acknowledgment
only after successful commit continue to next planned evaluation
```

A complete response with invalid schema, malformed model JSON, empty model content, or `done_reason=length` is a **completed consumed evaluation** with `valid:false`/appropriate error metadata. No retry. If the HTTP body was only partly received, it is not a complete result and is U.

### 6.7 Persist known failure or unknown outcome

- **Known F:** append only when typed evidence proves a terminal failure/no model evaluation (e.g., validated local failure before `send`, or a specifically approved definitive provider rejection). Commit F; never retry. An unrecognized HTTP status is not sufficient.
- **U:** on ambiguous post-send outcome, append U if the database is writable. If that insert fails or the process dies first, replay maps D with no C/F to unresolved U. Stop the run and do not call any provider for that evaluation.

### 6.8 Reconcile

`reconcile(run_id,evaluation_id,attempt_id,reviewer,disposition,evidence,rationale,approval)` runs under the exclusive run lock and `BEGIN IMMEDIATE`. Validate current replay state and evidence hashes, append one `RECONCILIATION` event, commit, then replay again.

- `CONFIRMED_NOT_DISPATCHED`: allowed only for I without D after boundary invariant passes. Requires reviewer approval to complete the original one planned request. Derived state is READY; same attempt ID and same request hash; next allowed transition is the single D.
- `CONFIRMED_COMPLETED`: allowed only if a complete response/result artifact is recovered and hashes match. Append C atomically; no request.
- `CONFIRMED_FAILED`: allowed only with authoritative proof of terminal noncompletion. Append F; no request.
- `ACCEPTED_UNKNOWN_MISSING`: append disposition, retain U, mark evaluation missing, and permit later untouched plan entries after validation. No new attempt/D.

For D-present unknown, `CONFIRMED_NOT_DISPATCHED` is forbidden based on missing server logs or absent fake receipt. Only authenticated evidence from the remote provider can establish a suitable terminal outcome; even proof that no inference ran does not authorize a second D under this zero-retry design.

### 6.9 Export JSON

The event log is canonical; `data/m4b3-results.json` is a derived compatibility view. Preserve the current outer keys (`status`, `revision`, `arms`, `results`) and existing configuration fields; add attempt/outcome identifiers only as a separately reviewed additive schema version. Build deterministic bytes from committed events, including explicit unknown/missing records rather than inventing model output.

Write a same-directory temporary file; flush and `fsync` it; atomically replace only if the existing file hash is the recorded initial template or a previously recorded export hash. Append `EXPORT_WRITTEN` with content hash and source event sequence after replace. If the process dies after replace but before the export event, startup may compare the current file hash with the exact deterministic current export and append an export-confirmation event; no inference. If the JSON hash is not a known prior export/template/current deterministic export, preserve it and block for review. Never overwrite a nonempty unrecognized file.

### 6.10 Validate/resume

```text
acquire exclusive lock before database/provider construction
require explicit run-live mode and existing DB (open mode=rw, not create)
run PRAGMA integrity_check and foreign_key_check; verify schema version
verify exact manifest/fingerprint, registered plan, sequence, payload hashes, event hash chain
replay all events and verify legal state/unique attempt/D/budget invariants
check current JSON against initial/recorded/current deterministic export hashes
if corrupt, missing, mismatch, unresolved U, or I requiring reconciliation: BLOCK before provider construction
export stale-but-recognized JSON from committed events only
construct M4B3 dispatcher; continue only planned untouched evaluations in fixed order
```

## 7. Ambiguous commit recovery algorithm

Any SQLite commit exception terminates the current live loop. Never interpret it as rollback, and never make another provider call in that process.

1. Record the local error out-of-band if possible; do not mutate the suspect connection further. Close it; if close fails, abandon the process. No cleanup may delete DB/WAL/SHM.
2. A fresh process acquires the run lock and opens the existing DB read/write without create (or opens a forensic read-only backup if SQLite cannot open it).
3. Run `integrity_check`, `foreign_key_check`, schema-version and path checks.
4. Replay canonical events from sequence 1; verify contiguous sequence, event IDs, canonical payload hashes, hash chain, planned-evaluation FKs, attempt IDs, unique D, and state transitions.
5. Find the transaction's preallocated event ID and expected event/payload hash. Do not search only by evaluation ID; the unique event ID and hash distinguish the attempted commit.
6. If the full transaction exists, includes the full expected response/result and C event, and all checks pass, classify completed. If D exists without a valid complete C, classify unknown. If an F exists with valid terminal evidence, classify failed. If commit was the D transaction and D is absent, the program invariant says transport was never entered because send follows only a successful D commit; require human reconciliation before any original dispatch.
7. If rows are partial, checks fail, or outcome cannot be established, mark admission `BLOCKED`, preserve artifacts, and require human review. Never reinitialize, overwrite JSON, or repeat inference.

After a process/machine restart, a transaction is expected to recover as committed or rolled back under SQLite/filesystem guarantees. The fresh-process replay—not the exception object from the old process—is the evidence. Hardware/power-loss correctness remains limited by the storage stack.

## 8. Initialization and missing-ledger policy

Add a separate `--initialize` command. It validates the pinned plan, approved amendment/rubric evidence, run fingerprint, and exact empty results template; creates the DB and plan history; exits without model calls. It must refuse if the DB path, orphan sidecar, or incompatible result file already exists. The approval artifact must include a human reviewer/name/signature/date in the approved document record; the command cannot self-approve.

Normal `--run-live` opens an existing ledger only. Missing DB after prior initialization is a hard block. Missing local evidence can never prove that no past run occurred if an operator deliberately deletes both ledger and results; this design does not protect against a local administrator. Reinitializing requires human investigation and a new explicitly approved run identity, not a “fresh start” flag.

For a nonempty results JSON without matching DB/run fingerprint, preserve and block; no automatic import or overwrite. For a valid DB with stale JSON whose hash matches the initial template or a recorded previous export, rebuild JSON without inference. If JSON hash is unknown, block and preserve.

## 9. Provider boundary and failure classification

### 9.1 One-way dispatch gate

1. Validate approved run/evaluation identity, fingerprint, and unchanged case/arm/settings.
2. Construct the complete HTTPX request locally, including canonical JSON body serialization, URL validation, context/output budget, timeout, model/options/schema/messages, and request hash.
3. Commit I (with request hash/config snapshot).
4. Ledger commits one D for same attempt; verify commit success.
5. Consume single-use permit and enter `httpx.Client.send(prepared_request)` once.
6. Receive complete raw body or return typed ambiguous outcome.
7. Parse/validate response as data; schema failure is not dispatch failure.
8. Store body, result/validation, metrics, and C in a single transaction.

HTTPX request construction/JSON serialization must precede D. Current `providers.py:81` uses `httpx.post(json=...)`, which combines request construction and transport; future M4B3 code should build `httpx.Request` first and send it via a single dedicated method after D. Use `follow_redirects=False`, `trust_env=False`, explicit `HTTPTransport(retries=0)`, and no application retry. No alternate provider/fallback. The provider callback is mandatory for the dedicated M4B3 path, not optional.

Python cannot defend against malicious code in the same interpreter directly calling `httpx.post` or Ollama. The guarantee is architectural for the official M4B3 runner path and enforced by its runtime session/permit checks, not a security boundary against a local administrator. Generic product `Provider.analyze/structured` remains separate and must not be used for M4B3 experiment calls.

### 9.2 Typed outcomes

Return a typed outcome with phase enum `PREPARED`, `SEND_ENTERED`, `RESPONSE_HEADERS`, `BODY_COMPLETE`; `transport_entered`; `response_complete`; status; raw body bytes; safe headers; usage; error class; and request/event IDs. Do not have the runner infer dispatch state from arbitrary exception classes or a broad `except Exception`.

| Observation | Classification | Action |
|---|---|---|
| Request construction/serialization fails before I | No attempt/request | Stop before provider; no dispatch |
| I commit fails | No D; no provider call | Stop, fresh-process DB validation |
| D commit fails/ambiguous | No call to `send` in current process; recovered D is consumed conservatively | Stop; if D exists, U/no replay; if absent, reconcile original unused dispatch |
| Pre-send deterministic local failure after I, with proof `send` not entered | `FAILED` | Append F; no retry |
| Error after `Client.send` entered (connect timeout/error included) | `UNKNOWN_OUTCOME` unless strong transport evidence proves no delivery | Append U if possible; no replay |
| HTTP response headers but incomplete body/read reset | `UNKNOWN_OUTCOME` | Preserve partial body only as diagnostics; no completion/no replay |
| Complete body, HTTP error status | U unless explicitly approved exact provider semantics prove inference did not begin | Preserve body/status; no generic F |
| Complete body, invalid JSON/empty output/`done_reason=length`/schema-invalid | `COMPLETED`, `valid:false` | Save raw body and validation error; no retry |
| Complete valid body | `COMPLETED`, `valid:true` | Save raw and normalized output atomically |
| Remote completion with response lost | `UNKNOWN_OUTCOME` | Never retry; missing if unresolved |

## 10. Reconciliation record contract

Every reconciliation event includes `reviewer_identity`, `timestamp_utc`, `evaluation_id`, `attempt_id`, `prior_derived_state`, `disposition`, `evidence_references` with SHA-256/issuer where available, `rationale`, `approval_result`, and the immutable fingerprint. It appends; it never edits the original event or payload.

| Disposition | Allowed only when | Exact transition | Provider action |
|---|---|---|---|
| `CONFIRMED_NOT_DISPATCHED` | State is I with no D; exact boundary invariant proves no transport entry; reviewer approves | Append R; derive `READY_TO_DISPATCH`; retain same attempt/request hash | One original dispatch may proceed; same attempt ID; one D only |
| `CONFIRMED_COMPLETED` | Complete result/response evidence tied to event/request hashes is recovered | Append R + C result if absent; derive C | None |
| `CONFIRMED_FAILED` | Authoritative evidence proves terminal noncompletion | Append R + F; derive F | None; no retry |
| `ACCEPTED_UNKNOWN_MISSING` | Outcome cannot be resolved | Append R; retain U, mark missing/closed | No call for that evaluation; other untouched evaluations may proceed |

`CONFIRMED_NOT_DISPATCHED` after any D is forbidden absent authenticated remote evidence, and even then cannot authorize a second D. No reconciliation changes model/config/plan, increases 24 planned IDs or dispatches, or removes a missing result.

## 11. Canonical run fingerprint

Compute SHA-256 over canonical UTF-8 JSON (sorted keys, compact separators, no NaN) with explicit schema version. The fingerprint includes:

**Experiment-defining and resume-blocking:** original pinned commit; frozen registry blob and source/documentation hashes; case IDs; arm mapping/order; exact evidence package hashes; current/layered prompt bytes/hashes; schema JSON and validator hashes; model tag and full installed digest; Ollama version; temperature/thinking/context; requested and effective `num_predict`; timeout; redirect/retry/provider policy; canonical request payload hash per evaluation; runner and provider source byte hashes; approved Documents 56/57 hashes/approval evidence; Python package versions for HTTPX/Pydantic/provider SDK; and test-approved ledger schema version.

For the working tree, include exact SHA-256 hashes of `scripts/evaluate_m4b3.py`, `blackbox/providers.py`, schema/prompt implementation files, and an inventory/hash of any untracked code that participates in the experiment. Record Git HEAD and `git status --porcelain` as provenance, but do not call a dirty tree a clean commit. Any relevant code-byte difference blocks resume even if HEAD is unchanged. Include lockfile/resolved package versions; current version ranges alone are insufficient.

**Operational audit metadata (record, but not ordinarily fingerprint-blocking):** host OS/build, Python executable/version, SQLite runtime version, UTC start/end, process ID, local filesystem/DB path, lock-acquisition facts, latency, token counts, and available hardware metadata. Enforce a tested SQLite minimum separately. If any operational value affects the model request or its effective generation behavior, promote it to the blocking fingerprint.

At startup recompute the manifest and per-request hash; mismatch blocks before provider construction. Never silently “resume” under edited runner/provider code, a changed digest, a new output budget, an unapproved amendment, or a different arm/case order.

## 12. Windows process lock

Use a stable local path such as `data/m4b3-attempt-ledger.lock`. Open without truncation; set the OS handle non-inheritable; lock a fixed byte range nonblocking (for example, `msvcrt.locking(fd, LK_NBLCK, 1)` after positioning at byte 0). Hold the handle for the entire run, including startup validation, calls, persistence, and export. Acquire before opening/creating SQLite or constructing any provider. Lock acquisition failure exits with zero provider calls.

A leftover pathname is not an active lock. Do not delete/replace it during contention; contenders could lock different file objects. On normal exit release and close; on process death, OS handle closure should release the OS lock, but the implementation must test it on the actual target Windows filesystem. Do not inherit the handle into children. If SQLite reports busy despite the run lock, use a bounded busy timeout and fail closed; no database retry may resend a model request. Use local NTFS or another validated local filesystem; do not use network/cloud-sync storage for WAL.

Two-process test: parent starts runner A and waits for “lock acquired”; starts runner B with same DB; B must fail before DB/provider construction; independently assert only A receives one test permit. Abruptly terminate A; B may acquire the stable lock path, must replay the DB, and must block or resume only according to persisted state. Never infer staleness from pathname timestamps.

## 13. Failure-injection specification

All tests use temporary DBs, fake provider, independent fake HTTP receiver with its own append+flush+fsync receipt log, deterministic hooks, actual child processes, abrupt termination, and fresh-process recovery. No live Ollama. “Durable events” below are expected after reopening; result state is derived by replay.

| Test | Initial state | Fault point | Receiver reached? | Durable events | Result state | Restart action | Expected calls | Invariant |
|---|---|---|---:|---|---|---|---:|---|
| 1 Before attempt | PLANNED | Kill before I transaction | No | plan only | none | Start original attempt after checks | 0 then 1 | I1/I5 |
| 2 After I | I committed | Kill before D | No | I | unresolved | Require CONFIRMED_NOT_DISPATCHED; same attempt only | 0 then ≤1 | I1/I2 |
| 3 After D | I,D committed | Kill immediately after D, before send | No | I,D | U | Block/reconcile missing; never send again | 0 observed | I2/I3 |
| 4 Just before HTTP | I,D committed | Fault immediately before `Client.send` | No | I,D | U after restart | Block; no replay | 0 | I1/I2 |
| 5 After receiver receipt | I,D | Receiver fsync receipt, then kill runner | Yes | I,D | U | Block; preserve receiver count | 1 | I3/I5 |
| 6 Timeout after receipt | I,D | Receiver records then transport times out | Yes | I,D,U if written | U | Reconcile; no send | 1 | I3 |
| 7 Partial body | I,D | Fake server sends prefix then closes | Yes | I,D,U | U | Block/close missing; no replay | 1 | I3 |
| 8 Invalid JSON body | I,D | Return complete non-JSON 200 body | Yes | I,D,C | completed invalid | Continue next evaluation | 1 | I2/I4 |
| 9 Schema-invalid response | I,D | Return complete JSON rejected by schema | Yes | I,D,C | completed invalid | Continue; no retry | 1 | I2/I4 |
| 10 `done_reason=length` | I,D | Return complete Ollama body with length reason | Yes | I,D,C | completed truncated/invalid | Continue; no retry | 1 | I2/I4 |
| 11 Result insert failure | I,D | Raise disk/SQL error after receiver response | Yes | I,D | U | Fresh process blocks/reconciles | 1 | I3/I4 |
| 12 Commit ambiguity after C | I,D | Commit data then inject caller-side commit exception | Yes | full I,D,C or I,D only | C if whole event verifies; else U | Fresh-process replay; never resend | 1 | I4/I5 |
| 13 Crash inside C transaction | I,D | Kill between payload serialization and transaction commit | Yes | I,D or full I,D,C | U or C, never half C | Inspect transaction recovery; no resend | 1 | I4 |
| 14 Export failure | I,D,C | Deny temp write/replace | Yes | I,D,C; prior export history | completed | Retry export only | 1 | I4/I5 |
| 15 Missing ledger | Initialized run then remove DB in temp test | Before run-live open | No | none accessible | BLOCKED | Require human investigation; no auto-create | 0 | I10 |
| 16 Corrupt DB | Valid DB copy then truncate page/WAL | Startup integrity | No | Untrusted/corrupt | BLOCKED | Preserve forensics; no repair/create | 0 | I10 |
| 17 Nonempty JSON without ledger | Nonempty result JSON, DB absent | Startup | No | no ledger | BLOCKED | Preserve JSON; no import/overwrite | 0 | I10 |
| 18 Duplicate evaluation | Plan contains same revision/case/arm twice | Registration | No | original valid events only | BLOCKED | Unique constraint rejects | 0 | I6/I7 |
| 19 Duplicate attempt | Reuse attempt UUID | I insertion | No | prior history | BLOCKED | Unique partial index rejects | 0 | I7/I8 |
| 20 More than 24 | 25th evaluation/dispatch | Plan validation/insert | No for 25th | 24 max | BLOCKED | Reject before provider | ≤24 | I6 |
| 21 Concurrent runners | Empty valid initialized DB | Two processes barrier at lock | Only lock owner | One run history | Loser BLOCKED | Winner continues; loser never initializes provider | At most 1 per eval | I9 |
| 22 Reconcile pre-dispatch | I, no D | Reviewer approves non-dispatch | No before approval | I,R(not dispatched) | READY_TO_DISPATCH | Same attempt may issue one D | 0 then 1 | I1/I2/I8 |
| 23 Reconcile after D as not sent | I,D,U | Operator submits CONFIRMED_NOT_DISPATCHED without remote proof | No new call | Original history + rejected decision/audit | U | Block or accept missing only | unchanged | I3/I8 |
| 24 Reconcile unknown missing | I,D,U | Reviewer accepts missing | No | I,D,U,R(accepted missing) | U/missing closed | Other untouched evals only | unchanged | I3/I5 |
| 25 Replay completed | I,D,C; same eval in plan again | Admission | No new | unchanged | C | Reject duplicate | prior count 1 | I2/I5 |
| 26 Replay failed | I,F; same eval again | Admission | No new | unchanged | F | Reject; no retry | prior count ≤1 | I2/I5 |
| 27 Replay unknown | I,D,U; same eval again | Admission | No new | unchanged | U | Block/reconcile; no replay | prior count 1 | I3/I5 |
| 28 Fingerprint mismatch | DB with different code/config hash | Startup | No | unchanged | BLOCKED | Human review/new approved run only | 0 | I7/I10 |
| 29 Disk full before I/D | Valid plan | Inject write/sync failure | No | no I or prior I only | blocked/unresolved | Stop before send | 0 | I1/I10 |
| 30 D commit returns error | I, inject commit error whose transaction may persist | No; send forbidden on error | I or I,D | U if D present; predispatch reconciled if absent | Fresh-process algorithm | 0 | I1/I2/I10 |
| 31 Full HTTP error status | I,D | Receiver returns complete generic 500 | Yes | I,D,U unless definitive approved semantics | U | Preserve body; no retry | 1 | I3 |
| 32 JSON export crash window | I,D,C committed; replace succeeds; kill before export event | Yes | C and possibly prior export event | completed | Hash JSON against deterministic current export; append recovery export event only | 1 | I4/I5 |
| 33 Stale but recorded JSON | Ledger has C after last recorded export | Startup/export | Prior calls | Event history includes last export hash | completed | Rebuild from DB without provider | no new call | I4/I10 |
| 34 Arbitrarily edited JSON | Valid ledger; JSON hash matches no known/deterministic export | Startup | No | DB unchanged | BLOCKED | Preserve both, human review | 0 | I7/I10 |
| 35 `FAILED` before transport | I, deterministic no-send error | Inject before D/Send | No | I,F | failed terminal | Skip; no retry | 0 | I2/I3 |
| 36 Fresh-init crash | DB path absent | Kill during initialization transaction | No | either complete schema/plan or no committed transaction; path may remain | BLOCKED if incomplete/ambiguous | Preserve; inspect; never auto-delete/reinit | 0 | I10 |

Child-process termination demonstrates what survives process death on that OS/filesystem and whether a fresh process replays without resending. It does not emulate sudden power loss, failing storage firmware, all Windows filesystems, a malicious administrator, or actual Ollama's server-side execution. The independent receiver proves the fake server accepted a request, not that real Ollama executed exactly once.

## 14. Exact future implementation blueprint

No implementation changes are made by this contract.

| File/module | Future functions/classes and changes | Pre-integration tests | Integration tests | Must remain unchanged |
|---|---|---|---|---|
| New `scripts/m4b3_attempt_ledger.py` | `Ledger.open_existing`, `Ledger.initialize`, `register_plan`, `replay_validate`, `begin_attempt`, `authorize_dispatch`, `record_completed`, `record_failed`, `record_unknown`, `reconcile`, `build_export`; DDL, hash/canonicalization, transaction helper, backup/read-only validation | DDL constraint tests; event replay/state transition unit tests; failure injection for every transaction; commit ambiguity recovery | Child-process crash/reopen; concurrent lock; event/result/budget/fingerprint tests | No model invocation inside ledger module; no mutable state projection |
| `scripts/evaluate_m4b3.py::plan` | Return immutable manifest/evaluation IDs and exact order; include prompt/schema/request fingerprints | Existing six×four order and no-label tests | Compare manifest and DB registered plan | Case/arm order, prompts, schemas, 24 cap unchanged |
| `scripts/evaluate_m4b3.py::main` | Add explicit `--initialize`; make `--run-live` require existing approved run session; acquire lock and validate everything before provider construction | Missing/corrupt/mismatch/approval tests | Startup, stale export, two-runner tests | Existing `--dry-run` remains no-call; no inference on initialization |
| `scripts/evaluate_m4b3.py::execute` | Remove arbitrary live plans/provider API; accept `ApprovedRunSession` and fixed dispatcher; replays only untouched entries | Direct-call rejection and fake session test | Full fake receiver run and resume suite | No automatic retry; registered execution order |
| `blackbox/providers.py` | Add M4B3-specific `PreparedRequest`, `DispatchOutcome`, `M4B3OllamaDispatcher.prepare/send_prepared`; construct `httpx.Request` before permit; send exactly once after D | Request canonicalization, redirects/retry disabled, typed outcome tests | Transport spy and receiver receipt test | Generic product provider behavior isolated; no Gemini for M4B3 |
| `tests/test_m4b3_harness.py` | Keep plan/schema tests; add fake receiver process, temporary DB, subprocess checkpoints, Windows lock suite, reconciliation/replay/export tests | Pure ledger and provider tests | 36+ matrix cases, Windows filesystem target, no live Ollama | Never run fixtures/Docker/model for ledger testing |
| Future `data/m4b3-attempt-ledger.sqlite3` | Created only by approved initialization; stored locally; not committed by default | Initialization/recovery tests | Full run simulation | No automatic create on live startup |
| `data/m4b3-results.json` | Derived exporter preserves current envelope; hash-bound initial template/export events | Deterministic export and atomic-replace failure tests | Stale/unknown JSON tests | No label/prompt/schema/protocol changes in export work |
| `requirements.txt` | No new dependency recommended; use stdlib `sqlite3`, `hashlib`, `uuid`, OS lock APIs | Verify supported runtime versions | Installed-version fingerprint tests | No dependency changes without separate approval |

## 15. Six-blocker closure assessment

| Issue | Original blocker | Resolution | Remaining assumption | Implementation proof test | Design status |
|---|---|---|---|---|---|
| B1 | No current ledger | Initialization + canonical event DB + recovery rules defined | SQLite/filesystem behavior meets tested minimum | Init/crash/reopen matrix | `RESOLVED` at design level |
| B2 | Direct execution bypass | Session-bound API and dedicated dispatcher; arbitrary plans/providers rejected | Python code is not a hostile security boundary; official M4B3 paths are controlled | Direct-call rejection + receiver instrumentation | `RESOLVED` at architectural level |
| B3 | Reconciliation ambiguity | Exact I/no-D same-attempt READY transition; D is permanently consumed | Mandatory no-bypass invariant must be implemented and proven | Kill after I/D; same attempt and D uniqueness | `RESOLVED` at design level |
| B4 | Competing DB sources | Event log sole state/result source; manifest tables immutable; replay is authoritative | SQLite integrity and appending code correct | Rebuild/replay/hash/transaction fault tests | `RESOLVED` at design level |
| B5 | Provider boundary optional | Prepared request → D commit → one send in dedicated M4B3 dispatcher | No external/local code bypass outside official runner; no remote idempotency | Test all M4B3 paths plus fake receiver | `RESOLVED` for official route; not a security guarantee |
| B6 | Startup fail-open | Explicit init, existing ledger required, fingerprint/result checks before provider | Deliberate deletion of every local record cannot be detected locally | Missing/corrupt/mismatch/nonempty JSON startup tests | `RESOLVED` with stated local-tampering limit |

Design correctness is not implementation correctness. Implementation tests on the target Windows filesystem are not runtime verification against Ollama. Runtime verification is not experiment approval. A completed local experiment is not evidence of general diagnostic reliability. The original preregistration is authoritative; Documents 56/57 remain unapproved and their changes must be approved before any inference.

## 16. Remaining limitations and approval checklist

The remaining assumptions are environmental, not unresolved protocol choices: OS/filesystem/storage honor SQLite sync requests; the reviewed M4B3 code has no uninstrumented transport path; and the local operator is not maliciously rewriting all evidence. A local ledger cannot prove what Ollama did after losing a response. This contract deliberately records uncertainty rather than filling that gap with a retry.

- [ ] Human approves Documents 56 and 57 and records names/dates/signatures; no experiment approval is inferred from this design.
- [ ] Human approves this implementation contract before implementation begins.
- [ ] Implement exact schema, startup fail-closed checks, run fingerprint, DDL constraints, and event replay.
- [ ] Implement and prove mandatory M4B3 dispatch boundary, no retries/fallback/redirects, one-use permit, and response typing.
- [ ] Pass all 36+ fake-provider tests, including real child-process termination and independent fake receiver.
- [ ] Pass two-process lock test on the target Windows filesystem and document tested SQLite/Python versions.
- [ ] Verify empty results template and existing JSON export behavior; preserve unrecognized JSON.
- [ ] Review implementation diff and confirm no case/arm/order/prompt/schema/model/budget change.
- [ ] Only after separate protocol approval and implementation review may a human authorize live inference.

## 17. Beginner-friendly explanation

The runner and Ollama are two separate systems. `scripts/evaluate_m4b3.py` can save a row in SQLite, but Ollama runs elsewhere and does not join that database transaction. That is why a timeout after `blackbox/providers.py` enters HTTP transport does not tell us whether the model completed. Repeating the request could create a second inference.

An event-sourced database stores a sequence of facts—plan registered, attempt started, dispatch intent recorded, response completed—rather than overwriting one “current status” cell. The current state is calculated by reading the events in order. Here that is small: 24 evaluations, so replay is easy to inspect and test.

`DISPATCH_INTENT` is written just before the request. It must be durable first, or the request could happen with no local evidence. But a crash right after the marker and before the HTTP call looks the same after restart as a crash after Ollama received it. That tiny gap cannot be removed by SQLite. The safe choice is to never send again once the marker exists.

At-most-once application dispatch means our official runner invokes the HTTP send path at most once for one case/arm. It does not prove Ollama executed exactly once: the server may complete a request whose response is lost. SQLite WAL and `synchronous=FULL` help preserve local transactions across process/storage failures when the OS and disk honor sync requests; they cannot add Ollama to the same transaction.

Building the complete `httpx.Request` before the marker matters because JSON serialization or local validation could fail before transport. The marker should sit between “request is fully ready” and “send once.” A fake-provider test that kills a child process after an independent fake receiver records the request proves more than a normal function test: it checks the receiver's record and what a fresh process reads from SQLite. It still cannot simulate every power outage or prove real Ollama behavior.

The hardest remaining engineering trade-off is completeness versus no duplicate: an evaluation can remain missing even if the request never reached Ollama, because the durable marker was committed just before a crash. The protocol chooses no silent duplicate over automatically filling that missing result. Everything in this document is a proposal until the code and tests exist and the human separately approves the experiment.

## 18. Final Git status comparison

| Snapshot | Modified tracked | Untracked | Notes |
|---|---:|---:|---|
| Before this task | 18 | 429 | Requested Document 60 absent |
| After this task | 18 | 430 | One intended addition: `research/60_M4B3_LEDGER_IMPLEMENTATION_CONTRACT.md` |

The Git status inventory increased by exactly this new untracked path. The listed implementation files, Documents 50/55–59, and results template remain at their pre-task status entries. I did not intentionally modify any existing file. Because the repository was already highly dirty and the initial full status output was truncated by the tool, I cannot prove every pre-existing dirty file is byte-for-byte unchanged; I recorded the initial counts and relevant path statuses. No test, inference, fixture, Docker, repair, install, commit, reset, stash, clean, or configuration change occurred.

**Final status:** `DESIGN_CLOSED — READY_FOR_HUMAN_IMPLEMENTATION_REVIEW`

This verdict closes the technical design only. It does not authorize implementation or live execution.

M4B3_FINAL_PROTOCOL_REVIEW_COMPLETE — IMPLEMENTATION_NOT_STARTED — LIVE_EXECUTION_NOT_AUTHORIZED
