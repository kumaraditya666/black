# BLACKBOX M4B.3 Implementation Red-Team Audit

**Audit date:** 2026-11-07 (Asia/Calcutta)  
**Repository:** `C:\Users\Adi\Documents\ChatGPT\black`  
**Verdict:** `AUDIT_BLOCKED — CRITICAL_DEFECTS`  
**Scope:** Read-only reliability audit; live inference remains disabled.

## 1. Executive verdict

The current M4B.3 path is **not ready to claim a mandatory durable-dispatch boundary or trustworthy result history**. I reproduced two paths that create ledger-approved activity without the corresponding provider facts:

1. A caller imports `_PERMIT_ISSUER`, constructs `DispatchPermit` directly, and makes the dispatcher send a loopback request although no database or `DISPATCH_INTENT` exists. `send_prepared()` trusts the object and never verifies the event in SQLite.
2. After writing a dispatch marker, a caller invokes `Ledger.record_completed()` with arbitrary bytes and an arbitrary result dictionary. Replay accepts `COMPLETED` without an HTTP receiver or response validation.

I also reproduced an unused permit sending after the evaluation was explicitly reconciled as “unknown, accepted as missing.” Startup accepts a database whose global attempt-ID uniqueness index has been removed. The approval validator accepts a synthetic text string as a “signature.” Response reading buffers the entire body with no size cap.

The CLI still hard-disables live execution before planning or provider construction, and the dedicated M4B.3 dispatcher rejects Ollama port 11434 and non-loopback endpoints. Those guards worked by source inspection and the safe suite. The defects above invalidate protocol guarantees in the fake/test path and must be corrected before any live-enabling change. **This audit did not enable live execution.**

## 2. Scope, files, and versions inspected

Inspected the complete requested ledger and runner source, M4B.3 provider boundary, relevant tests, implementation contract, and approval status headers:

- `blackbox/m4b3_ledger.py`
- `blackbox/providers.py`
- `scripts/evaluate_m4b3.py`
- `tests/test_m4b3_ledger.py`
- `tests/test_m4b3_harness.py`
- `tests/test_engine.py`
- `research/60_M4B3_LEDGER_IMPLEMENTATION_CONTRACT.md`
- `research/56_M4B3_PROSPECTIVE_AMENDMENT_DRAFT.md`
- `research/57_M4B3_EVALUATOR_RUBRIC_DRAFT.md`

Runtime: Python 3.14.7, SQLite 3.50.4, HTTPX 0.28.1, pytest 9.1.1, Windows. The graphify query was attempted first as repository instructions require, but its graph was stale and omitted the new ledger module; it was not used as evidence. No graph rebuild was performed because this is a read-only audit and only this report was authorized.

The runner, ledger, M4B.3 tests, and Documents 56–60 were already untracked or dirty in the initial status. Their pre-task bytes cannot be inferred from Git status. I make no claim that their original contents were preserved. The audit made no source or existing-test edits.

## 3. Source-level architecture verification

| Claim | Assessment | Evidence and limits |
|---|---|---|
| Event history is the attempt/result history; state is replayed | **Verified by source, with API trust limits** | `Ledger.replay_validate()` reconstructs evaluations from events (`blackbox/m4b3_ledger.py:633–731`); there is no mutable current-state projection. Plan rows are immutable manifest inputs. Public writers can append false facts, as B1–B2 show. |
| Hash chain is checked at startup | **Verified by source/tests for ordinary corruption** | Replay checks contiguous sequence, duplicate event IDs, predecessor, payload hash/canonical JSON, event hash, initial hash, and SQLite high-water mark (`:666–727`). `test_hash_chain_tampering_blocks_replay`, `test_request_and_plan_fingerprint_tampering_blocks`, and `test_invalid_attempt_id_attached_to_rehashed_event_blocks_replay` pass. This is tamper-evident, not tamper-proof; §7. |
| Constraints prevent duplicate starts and dispatches | **Partially verified** | Fresh schema has indexes for one start per evaluation, one attempt ID per run, one D per evaluation, and terminal events (`:260–266`). `test_duplicate_evaluation_duplicate_attempt_and_budget_are_rejected` and `test_database_constraints_bound_dispatch_and_response_identity` pass. Startup omits `one_attempt_id_per_run` from its required schema objects (`:1129–1135`); replay lacks a global attempt-ID set. Removing the index was accepted; §7. |
| I precedes D; request is prepared first | **Normal path verified; boundary bypassable** | `execute()` prepares at runner `:323–327`, writes I at `:329–332`, gets D at `:334`, sends at `:336`. `authorize_dispatch()` appends D and returns a permit only after `_run_write()` (`blackbox/m4b3_ledger.py:903–925`). A fabricated permit bypasses it. |
| Result and C are atomic | **Verified for the normal writer transaction** | One C event stores raw response, body hash, normalized record, and validation (`blackbox/m4b3_ledger.py:927–957`). Replay verifies raw bytes against their hash and that result is a dictionary (`:825–844`), but does not bind that result to a parsed/validated response. |
| Unknown is not automatically retried | **Verified on official runner path** | D without terminal event derives to unknown (`:728–731`); runner blocks unresolved attempts (`scripts/evaluate_m4b3.py:240–246`) and continues only PLANNED or reconciled READY states (`:306–347`). Crash/ambiguity tests pass. Stale permits are a bypass; §4. |
| 24-evaluation budget survives restart | **Verified by source; test coverage partial** | Initialization requires exactly 24 rows and the six-by-four order (`blackbox/m4b3_ledger.py:375–410`); replay checks the exact plan (`:649–713`); D count is checked before issuance (`:914–920`). |
| Plan table and plan events agree | **Verified by source/test** | Replay compares each event to row identity/order/hash (`:700–713, 756–767`). `test_plan_table_event_history_disagreement_blocks_replay` passes. |
| Fingerprint changes block resume | **Partially verified** | `open_existing()` checks expected fingerprint before dispatcher creation (`blackbox/m4b3_ledger.py:509–545`; runner `:268–284`). Fingerprint tests pass. Test source is included in blocking inputs and Python/SQLite versions are audit-only (§11). |
| Missing DB is not recreated | **Verified by source/test** | SQLite URI uses `mode=rw`; `open_existing()` checks the path before connect (`blackbox/m4b3_ledger.py:327–330, 509–533`). `test_missing_ledger_and_nonempty_json_are_preserved` passes. |
| Unknown results JSON is preserved | **Verified by source/test** | Startup/export reject unknown hashes (`scripts/evaluate_m4b3.py:248–261`; ledger `:1072–1109`). `test_unknown_results_json_is_preserved_and_blocks` passes. |
| Windows lock excludes another process | **Verified on this Windows run** | `RunLock` opens without truncation, makes the handle non-inheritable, locks a byte with `msvcrt.locking`, and never deletes the stable path (`blackbox/m4b3_ledger.py:86–141`). Both Windows process-lock tests passed; no power-loss or other-filesystem guarantee is claimed. |
| Second runner stops before dispatcher | **Verified by test** | `test_two_runner_processes_contend_before_dispatcher_and_recover_owner_lock` confirms the contender is blocked and its dispatcher marker is absent (`tests/test_m4b3_ledger.py:883–950`). |
| Environment cannot enable live mode | **Verified by source/test** | Constant `LIVE_EXECUTION_ENABLED=False` (`scripts/evaluate_m4b3.py:19`); `main()` exits before planning/provider/network (`:406–423`). `test_live_cli_is_hard_disabled_before_plan_provider_or_network` sets `BLACKBOX_ENABLE_LIVE=true` and still sees the guard. |
## 4. Dispatch-boundary attacks

### Normal sequence

The intended route is `PreparedRequest → IN_FLIGHT → committed DISPATCH_INTENT → permit.consume() → Client.send()`. `M4B3OllamaDispatcher.prepare()` serializes and hashes the exact method, URL, headers, and body before I/D (`blackbox/providers.py:212–272`; hash `:164–172`). `execute()` then writes I, authorizes D, and calls the provider (`scripts/evaluate_m4b3.py:323–336`). The one `.send()` call is at `blackbox/providers.py:302–304`; the before-transport hook is just before it (`:291–304`). In the normal path, an I or D commit error does not return a permit.

### BLOCKER B1 — fabricated permit sends without a durable marker

`DispatchPermit` is a public dataclass (`blackbox/m4b3_ledger.py:179–208`). Its issuer is the importable module attribute `_PERMIT_ISSUER` (`:176`), and `__post_init__()` only checks identity against that accessible object (`:191–193`). `send_prepared()` checks type/request hashes and consumes the permit, then sends; it never queries a ledger or verifies `dispatch_event_id` (`blackbox/providers.py:274–304`).

I ran an isolated inline proof against an ephemeral `127.0.0.1` receiver. I imported `_PERMIT_ISSUER`, constructed a permit with `dispatch_event_id="forged-event-id"`, created no DB, and called `send_prepared()`. The receiver got **one** request and the outcome reported `transport_entered=true`. No model endpoint was contacted.

**Why it matters:** the dispatcher does not independently enforce D-before-send. Direct callers can create an unledgered request, defeating event history and at-most-once evidence.

**Smallest correction:** use an opaque single-use capability that is validated against a committed D by the trusted ledger immediately before transport. Do not use an importable module object as issuer. Keep the dispatcher as the only supported send boundary.

**Proving test:** construct a permit with the exposed issuer and no D; assert rejection and zero receiver requests. Also remove/alter the referenced D and assert rejection.

`RunSession` has the same pattern: `_SESSION_ISSUER` is importable (`scripts/evaluate_m4b3.py:210`), while `execute()` trusts that object identity and dataclass fields (`:212–229, 306–309`). The old arbitrary-provider signature is rejected by `test_arbitrary_provider_execution_api_is_rejected`, but that does not prove a forged session impossible.

### BLOCKER B2 — public ledger API can record false completion

`Ledger.record_completed()` accepts caller-supplied `raw_response`, `result_record`, and `valid` (`blackbox/m4b3_ledger.py:927–957`). Replay verifies the raw bytes against their hash and checks that `result_record` is a dictionary (`:825–844`); it does not parse the raw bytes, run schema validation, or prove they came from the dispatcher.

I created a temporary ledger, wrote I and D, then called `record_completed()` with `b"not a provider response"` and `{"case":"fabricated","valid":true}`. No receiver was started. Replay accepted state `COMPLETED` with that result.

**Why it matters:** C currently means “a caller appended this structure after D,” not “the runner received and validated this complete response.” This is a false-completion path through the public ledger API.

**Smallest correction:** make C creation accept only a typed complete dispatcher outcome after validation, or have the ledger validate raw bytes and bind normalized output to them. Reject mismatched caller-provided results.

**Proving test:** after I+D and with no receiver, attempt arbitrary raw/result data; assert rejection and unresolved replay state. Valid and schema-invalid complete responses should each bind to exact raw bytes and be recorded once.

### MAJOR B3 — stale unused permit sends after accepted-missing reconciliation

Replay turns D without a terminal event into `UNKNOWN_OUTCOME` (`blackbox/m4b3_ledger.py:728–731`). `reconcile()` can record `ACCEPTED_UNKNOWN_MISSING` (`:1010–1038`, replay `:788–813`). `send_prepared()` only consumes its in-memory permit and never rechecks ledger state (`blackbox/providers.py:274–304`).

A temporary proof acquired D and an unused permit, reconciled the evaluation as accepted-missing, observed `missing_closed=true`, then called `send_prepared()` with the stale permit. The receiver accepted one request after closure. This is not a duplicate D, but it violates the explicit decision that the unknown attempt is closed and must not later dispatch.

**Correction/test:** revalidate permit state at transport and revoke it on reconciliation/closure. Prove accepted-missing reconciliation makes the old permit fail and the receiver records zero requests.

### Concurrency, repeated dispatch, and transaction failures

- `test_dispatch_permit_is_atomic_under_two_simultaneous_consumers` passed. Two threads start together with the same permit; exactly one outcome, one `LedgerBlocked`, and one receiver request. `threading.Lock` in `_PermitUse` (`blackbox/m4b3_ledger.py:170–173, 195–208`) avoids relying on the GIL.
- Fresh-schema uniqueness limits D to one per evaluation (`blackbox/m4b3_ledger.py:262`; `test_database_constraints_bound_dispatch_and_response_identity`). `authorize_dispatch()` replays state and rejects consumed D (`:903–925`). Reuse after consumption is covered by the concurrency test.
- Second ledger sessions are excluded by the OS lock and serialized writes. The Windows runner-contention test passed.
- `test_dispatch_marker_commit_ambiguity_never_enters_transport` passed: an after-commit hook raises after D, but no permit returns and the receiver sees zero requests. Child crashes after D and before transport recover as unknown without receipt.
- No test kills the child exactly after `.send()` entry but before a receiver can record receipt. The after-receiver checkpoint is later.

## 5. Marker-before-transport proof

`test_fake_receiver_sees_committed_marker_and_completion` checks that an independent receiver can query D after reading the request (`tests/test_m4b3_ledger.py:395–408`; receiver query `:132–143`). That alone does **not** prove ordering: a request could be sent and D committed before the receiver queries SQLite.

I ran a stronger temporary harness using the provider’s `before_transport` hook (`blackbox/providers.py:291–304`). Immediately before `.send()`, it opened SQLite with a separate connection and asserted the committed D event ID, evaluation ID, attempt ID, request hash, body hash, and config hash matched the prepared request. It asserted zero receiver requests at hook time, then allowed the single send. The receiver recorded exactly one request. The normal path’s ordering proof passed.

This does not repair B1: the dispatcher still accepts a forged permit with no D.

## 6. Ambiguous SQLite commits: cases A–E

| Case | Evidence | Result / gap |
|---|---|---|
| A. COMMIT fails before durable completion | `test_result_insert_failure_rolls_back_and_never_retries` injects `sqlite3.OperationalError` at `during_completion_transaction` (`tests/test_m4b3_ledger.py:539–550`), before COMMIT. I failure similarly is injected before I insert (`:553–563`). | Rollback is covered, but this is **not** a failure raised while SQLite executes COMMIT. No disk-full/VFS pre-durable COMMIT failure reproduced. Source abandons on COMMIT exception (`blackbox/m4b3_ledger.py:587–595`); this branch remains unproven. |
| B. Commit succeeds, caller gets artificial exception afterward | `test_completion_commit_ack_ambiguity_recovers_completed` raises at `after_commit`, then a fresh process recognizes C (`tests/test_m4b3_ledger.py:566–580`). D acknowledgment ambiguity also tested (`:779–790`). | **Verified for post-commit acknowledgment-loss simulation.** |
| C. Process terminates after commit | `test_child_process_termination_and_fresh_process_recovery` kills after I, D, before transport, after receiver receipt, during C, after C, and after JSON replacement (`:484–524`). | **Verified at those checkpoints and on fresh-process replay.** Not power loss; no immediate post-send-entry checkpoint. |
| D. Result append succeeds but C cannot commit | Raw response and normalized result are one C event (`blackbox/m4b3_ledger.py:927–957`). The transaction fault test raises after append, before commit. | **Partially verified.** No result row can commit separately; fault rolls back C and D replays as unknown. Actual full-disk COMMIT behavior is not exercised. |
| E. DB cannot reopen/validate | `test_corrupt_database_and_bad_sidecar_fail_closed` corrupts DB bytes and WAL header (`tests/test_m4b3_ledger.py:609–619`); missing WAL recovery is tested at `:621–625`. | **Verified** for corrupt main DB, bad WAL header, and missing WAL. Corrupt SHM and busy/disk reopen failures are not covered. |

No recovery branch automatically calls the provider again. A committed C is replayed complete; D without terminal event derives unknown; invalid DB blocks. The primary evidence gap is a true pre-durable COMMIT failure, not a source-level retry.
## 7. Event history and replay attacks

| Attack | Assessment |
|---|---|
| Bad previous hash, modified payload, modified event hash | Replay rejects by predecessor/payload/event hashes (`blackbox/m4b3_ledger.py:681–695`); ordinary tamper test passes. |
| Sequence gaps, duplicate event IDs | Replay checks contiguous sequence and a `seen_event_ids` set (`:669–678`); no named test was found for every variant. SQLite autoincrement high-water is checked (`:723–727`). |
| Duplicate attempt ID | Fresh schema rejects it; `test_duplicate_evaluation_duplicate_attempt_and_budget_are_rejected` passes. Startup omits the global index from required objects (`:1129–1135`) and replay does not check attempt IDs globally. I dropped `one_attempt_id_per_run` in a temporary DB; `open_existing()` accepted it, and two evaluations then replayed `IN_FLIGHT` with the same attempt ID. **MAJOR schema-validation gap.** |
| D for another attempt ID | `_replay_one()` compares post-I event attempt ID with the original (`:786–787`). `test_invalid_attempt_id_attached_to_rehashed_event_blocks_replay` recomputes hashes and still fails semantically (`tests/test_m4b3_ledger.py:1007–1025`). |
| Completion for unrelated eval / without D; failure after completion; both F and U | Replay requires registered plan, matching attempt, and dispatched/unknown state for C (`:753–770, 825–867`). F/U state rules and terminal indexes reject illegal transitions (`:260–266, 845–867`). Source verified; not every cross-product has a named test. |
| Missing plan event / plan table disagreement | Ordered prefix and row/event hashes are enforced (`:700–713, 756–767`). `test_plan_table_event_history_disagreement_blocks_replay` passes. |
| Different run identity | Foreign keys bind events to run metadata and replay reads the one run ID (`:237–258, 633–647, 671`). Mismatched metadata blocks. |
| Multiple reconciliations / unauthorized reviewer | Reviewer, evidence, rationale, and Boolean approval are caller-supplied (`:1010–1038`); no signature, identity provider, or policy lookup exists. Replay permits a later reconciliation while unresolved (`:788–813`). No test covers contradictory dispositions or a reviewer lacking authority. |
| Validly rehashed but semantically illegal sequence | Replay validates transitions. `test_invalid_attempt_id_attached_to_rehashed_event_blocks_replay` proves one rehashed semantic violation is rejected, but does not authenticate the event author. |

The event hashes are unkeyed SHA-256. They detect accidental edits, truncation, and inconsistent history while validation code and trusted metadata stay intact. They do **not** make the log tamper-proof against a local writer able to drop triggers/indexes and recompute chain and metadata. Append-only triggers are guardrails, not external signatures or immutable storage. Describe the log as tamper-evident under the local trust model.

## 8. Result persistence and export

- `send_prepared()` enters `Client.send(..., stream=True)` once and reads raw chunks (`blackbox/providers.py:302–330`). It appends every chunk then joins; there is no content-length or running-byte limit. Oversized bodies can exhaust memory before persistence. **MAJOR; blocker before live execution.**
- For complete 2xx responses, the runner decodes outer UTF-8 JSON, extracts inner model JSON, validates it, and records valid or invalid results (`scripts/evaluate_m4b3.py:357–385`). Complete malformed JSON, schema-invalid data, empty output, or `done_reason=length` becomes COMPLETED with `valid=false`; this is intentional consumption without retry. `test_complete_invalid_responses_are_consumed_without_retry` and `test_done_reason_length_is_stored_as_invalid_completed` pass.
- A read exception returns incomplete body plus bytes read so far; runner appends unknown and never retries (`blackbox/providers.py:315–328`; runner `:338–347`). `test_partial_response_body_bytes_are_retained_for_audit` passes.
- Complete non-2xx responses, including HTTP 500, become unknown, not evidence of non-execution (`scripts/evaluate_m4b3.py:348–356`). `test_http_500_preserves_body_and_is_unknown` passes.
- C retains raw bytes base64/hash and normalized result. Replay checks raw body hash (`blackbox/m4b3_ledger.py:833–844`); export derives from replayed results (`:1050–1070`). Replay does not prove normalized data was parsed from those bytes (B2).
- Export refuses unknown JSON, writes a same-directory temp and replaces (`blackbox/m4b3_ledger.py:1072–1100`). A crash after replace but before `EXPORT_WRITTEN` is repaired by the deterministic hash (`:1093–1109`); `test_export_replace_crash_window_records_hash_without_resend` passes. A process crash may leave a stray temp file; no cleanup test covers it. Replacement permission failure is not tested, but committed C can be exported again without provider activity.
- Unexpected complete UTF-8/JSON data follows the runner’s invalid-completion exception path. No dedicated encoding test exists.

**Response-size correction:** impose a strict streaming limit; stop retaining chunks past it; preserve only bounded diagnostic bytes/hash; record unknown because transport already began. Test oversized data for bounded retention, one receipt, unknown state, and no replay send.

## 9. Windows lock review

`RunLock.acquire()` resolves one path, creates/opens without `O_TRUNC`, makes the handle non-inheritable, writes/fsyncs one byte only if empty, seeks to byte zero, then uses nonblocking `msvcrt.locking(..., LK_NBLCK, 1)` on Windows (`blackbox/m4b3_ledger.py:89–118`). The kernel lock, not stale file contents, identifies an owner. `release()` unlocks/closes but does not delete the pathname (`:120–141`). OS handle closure on process termination released the lock on this tested Windows host.

Both process tests passed: a contender is blocked while the owner lives, the path persists after termination, and a new owner can acquire. The session owns the ledger/lock until close (`scripts/evaluate_m4b3.py:213–229, 451–455`). No power-loss, network-filesystem, antivirus, or storage-durability claim is made.

`Ledger.initialize(held_lock=...)` trusts the supplied lock without checking it is acquired or matches the path (`blackbox/m4b3_ledger.py:358–371, 423–424`). Official `initialize_experiment()` passes an acquired lock (`scripts/evaluate_m4b3.py:389–403`), but direct API callers can bypass that assumption. Require an acquired matching lock or make the argument internal; test unacquired/mismatched input is rejected.
## 10. HTTPX and provider failure behavior

The M4B.3 dispatcher accepts explicit loopback HTTP, blocks port 11434, and configures `HTTPTransport(retries=0)`, `follow_redirects=False`, and `trust_env=False` (`blackbox/providers.py:182–209`). It serializes exact request bytes before I/D (`:212–272`) and has one `.send()` (`:302–304`). `execute()` has no retry/fallback (`scripts/evaluate_m4b3.py:306–387`). Timeout, reset, partial body, and read error after transport entry become unknown; HTTP 500 is unknown as well. This is the correct no-retry treatment for ambiguous remote completion.

The general product `Provider` elsewhere can use Ollama or Gemini (`blackbox/providers.py:50–124`), but the M4B.3 runner does not call `configured_provider()`; its dispatcher and hard live guard isolate the experiment route. The Gemini unit test monkeypatches its client and made no network request. Transport `BaseException` handling (`:295–310, 319–328`) also captures `KeyboardInterrupt`/`SystemExit`; fail-closed but broader than needed.

## 11. Fingerprint and approval gates

`build_run_manifest()` includes pinned commit, frozen registry/label/source hashes, schedule, evidence, prompts, schemas, request payloads/output budget, model config/digest, working-copy code hashes, dependency versions, and approval-manifest hash (`scripts/evaluate_m4b3.py:128–188`). Untracked runtime files are hashed when present (`:143–149`). Git HEAD/status are audit metadata, not blocking inputs (`:179–188`); that is reasonable with exact execution bytes and pinned source hashed. Python and SQLite versions are also audit metadata; include them in blocking inputs if their runtime/storage semantics define reproducibility.

**MINOR reproducibility issue:** `relevant_files` includes `tests/test_m4b3_harness.py` and `tests/test_m4b3_ledger.py` (`scripts/evaluate_m4b3.py:143–149`). Test-only edits thus block resume even if runtime behavior is identical. Separate test provenance from execution code; prove a test-only edit does not alter fingerprint while runtime edits still do.

Documents 56 and 57 explicitly say `DRAFT — NOT APPROVED` (Document 56 lines 3–8; Document 57 lines 3–5). `validate_approval_manifest()` checks status, nonempty reviewer/date/signature, and document hash/status claims (`scripts/evaluate_m4b3.py:98–120`). `test_real_initialization_refuses_unapproved_documents_without_creating_db` checks a missing manifest only (`tests/test_m4b3_ledger.py:980–984`).

**MAJOR approval-gate flaw:** the validator does not verify a signature; any nonempty string passes. I passed the test helper manifest (`reviewer_identity="synthetic test reviewer"`, `signature="synthetic-only-test-approval"`, documents claiming `APPROVED_FOR_IMPLEMENTATION`) directly to the validator. It returned accepted. This was validation-only; I did not call real initialization. The gate accepts an approval claim, not proof of human authority. Verify a signature under a trusted key or use an authenticated approval source. Test that arbitrary strings and the synthetic test signature cannot authorize real initialization; keep any test-only approval path unavailable to production CLI.

`--run-live` still exits regardless of environment variables (`scripts/evaluate_m4b3.py:406–423`). That kill switch is verified, but the approval validator must be corrected before real initialization or future live approval.

## 12. Independent safe test execution and coverage map

Before running tests, I inspected setup. M4B.3 receivers use ephemeral `127.0.0.1` ports (`tests/test_m4b3_ledger.py:236–253`); DB/results/approval artifacts are under pytest temp directories. Subprocesses are local Python children for crash/Windows-lock tests. Engine tests use temp Git repositories and monkeypatched providers; the Ollama test rejects the external hostname before a request, and Gemini’s client is monkeypatched (`tests/test_engine.py:13–27, 343–399`). Harness tests read pinned Git blobs and do not execute those snippets. No Docker or repair workflow is invoked. The engine suite uses local synthetic mocked scenario data; these are not M4B.3 repair fixtures and are never sent to a model.

Exact command:

```text
python -m pytest -q tests/test_m4b3_ledger.py tests/test_m4b3_harness.py tests/test_engine.py
```

Exact result:

```text
============================== warnings summary ===============================
..\..\..\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1
  C:\Users\Adi\AppData\Roaming\Python\Python314\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
133 passed, 1 warning in 141.52s (0:02:21)
```

Critical coverage map:

| Invariant | Passing test evidence | Does not prove |
|---|---|---|
| One permit across two threads | `test_dispatch_permit_is_atomic_under_two_simultaneous_consumers` | Forged issuer rejected or D queried by provider. |
| One D per evaluation | `test_database_constraints_bound_dispatch_and_response_identity` | Required index presence checked on reopen. |
| Crash recovery / no resend | `test_child_process_termination_and_fresh_process_recovery`, `test_ambiguous_transport_outcomes_block_and_never_resend`, `test_attempt_replay_after_failed_terminal_never_dispatches` | Power loss or exact post-send/pre-receipt instant. |
| I/D failure stops send | `test_in_flight_write_failure_sends_nothing_and_leaves_plan_untouched`, `test_dispatch_marker_commit_ambiguity_never_enters_transport` | Actual disk-full/SQLite COMMIT failure. |
| C atomicity/ambiguity | `test_result_insert_failure_rolls_back_and_never_retries`, `test_completion_commit_ack_ambiguity_recovers_completed` | Arbitrary raw/result pairing through public API. |
| Hash and plan checks | `test_hash_chain_tampering_blocks_replay`, `test_request_and_plan_fingerprint_tampering_blocks`, `test_invalid_attempt_id_attached_to_rehashed_event_blocks_replay`, `test_plan_table_event_history_disagreement_blocks_replay` | Keyed authenticity against local writer. |
| Export preservation/recovery | `test_unknown_results_json_is_preserved_and_blocks`, `test_stale_recognized_json_is_rebuilt_from_committed_ledger`, `test_export_replace_crash_window_records_hash_without_resend` | Replacement permission failure or temp cleanup. |
| Windows lock | `test_windows_or_posix_lock_excludes_second_process_and_survives_stale_path`, `test_two_runner_processes_contend_before_dispatcher_and_recover_owner_lock` | Other machines/filesystems. |
| Approval/live guard | `test_real_initialization_refuses_unapproved_documents_without_creating_db`, `test_live_cli_is_hard_disabled_before_plan_provider_or_network` | Cryptographic approval; test only covers missing manifest. |
| Forged permit, false C, stale permit, oversized response | **No existing test**; reproduced in isolated inline harnesses | Requires new rejection/bounded-streaming tests. |
## 13. Uncovered failure scenarios and risk

| Scenario | Coverage / risk |
|---|---|
| Disk full during initialization | Initialization crash is tested, not SQLITE_FULL. **Unproven storage-fault branch; preserve and block if ambiguous.** |
| Disk full during I | A pre-insert hook is tested; actual filesystem exhaustion is not. No send should occur because I must commit first. |
| Disk full during D | Post-commit acknowledgment loss is tested; actual COMMIT failure is not. No permit should escape any commit exception. |
| Disk full after receiver receipt | Completion transaction rollback is injected, not actual full disk. D remains; restart should derive unknown and not send. |
| Lock contention at startup | **Covered** by Windows two-process tests; contender stops before dispatcher construction. |
| Process termination during lock acquisition | No dedicated test. Kernel releases a successfully acquired lock on process exit; setup failure before lock acquisition is untested. |
| Corrupt WAL / SHM | Bad WAL header and missing WAL are tested. `_validate_wal_sidecar()` checks WAL magic only (`blackbox/m4b3_ledger.py:333–340`). Corrupt SHM is untested; SQLite fail-closed behavior is an assumption. |
| SQLite busy timeout | `busy_timeout=5000` and `BEGIN IMMEDIATE` are configured (`:313–324, 573–590`); no busy-timeout test. Errors block/ambiguate, with no retry. |
| DB replaced during process | No file-identity pin or test. Windows open-file semantics may prevent replacement on this host; do not generalize to other filesystems. |
| Request body/hash mismatch | Provider recomputes request/body hash (`blackbox/providers.py:279–284`); replay compares I/D identity (`blackbox/m4b3_ledger.py:772–823`); tampered request tests exist. No direct mutated-PreparedRequest send test found. |
| Oversized response | No limit; all chunks retained. **High memory/disk exhaustion risk; MAJOR, blocker before live.** |
| Unexpected response encoding | Complete invalid UTF-8/JSON follows invalid-completion path; no dedicated encoding test. |
| Response body read error | Partial body/reset tests become unknown: `test_partial_response_body_bytes_are_retained_for_audit`, `test_ambiguous_transport_outcomes_block_and_never_resend`. |
| Receiver starts late / terminates early | Reset is tested; no separate late-start case. Connect error after send entry is unknown and not retried by source. |
| Export temp left after crash | No stale-temp cleanup; target JSON recovery is tested. Low integrity risk, disk clutter. |
| Export replacement permission failure | No dedicated test. C is already committed; next startup should export without provider activity. |
| Two fingerprints share DB path | Fingerprint mismatch test changes model config and blocks before dispatcher. |
| Stale permit after reconciliation | Not covered by suite; reproduced. **MAJOR protocol violation.** |
| Unauthorized reconciliation reviewer | No identity/signature check; caller supplies reviewer strings and approval Boolean. **MAJOR audit gap.** |

## 14. Findings, corrections, and proof criteria

### BLOCKER

1. **Forged permit allows unmarked request.** Caller imports module issuer and reaches `Client.send()` without D. Correct with opaque capability plus committed-D validation at transport. Prove no-D/altered-D permit yields zero receiver requests; valid D yields one.
2. **Public completion writer allows false C.** After D, arbitrary bytes/result can be stored without a provider response. Correct by binding C to a typed, validated dispatcher outcome and verifying normalized output against raw bytes. Prove arbitrary data with no receiver cannot commit C; correct valid and invalid-complete responses each commit once.

### MAJOR

1. **Stale permit sends after accepted-missing reconciliation.** Revalidate/revoke at send. Prove a closed attempt’s old permit yields zero requests.
2. **Schema validation misses global attempt-ID index.** `_validate_connection()` omits `one_attempt_id_per_run` (`blackbox/m4b3_ledger.py:1129–1135`); replay has no global duplicate-ID check. Require the index and reject duplicate IDs during replay. Prove index removal blocks startup and a rehashed duplicate-ID history fails replay.
3. **Approval/reconciliation authority is self-asserted.** Nonempty signature/reviewer fields pass; no trusted verifier exists (`scripts/evaluate_m4b3.py:98–120`; ledger `:1010–1038`). Verify a signature or authenticated approval source. Prove fake strings are rejected and unauthorized reconciliation cannot close an attempt.
4. **Response is unbounded.** `blackbox/providers.py:315–330` accumulates every chunk. Cap streaming and mark over-limit responses unknown. Prove bounded retention, one receipt, unknown state, no resend.
5. **Actual pre-durable COMMIT failure lacks test evidence.** Current fault hooks throw before COMMIT or after it returns. Add controlled COMMIT failure (test VFS or precise wrapper) for initialization/I/D/C; reopen fresh process and prove committed C recognized, otherwise D unknown, corrupt DB blocks, and no second request occurs. Assurance gap, not claim that source retries.
6. **FAILED “proof” is caller-supplied flags.** `record_failed()` accepts Boolean `no_dispatch_proof`/`definitive_provider_failure` (`blackbox/m4b3_ledger.py:959–990`), and replay trusts them (`:845–858`). Keep post-D outcomes unknown absent hash-bound approved provider evidence. Prove arbitrary `definitive_provider_failure=True` cannot close D as FAILED.

### MINOR

- Test module hashes are blocking fingerprint inputs (`scripts/evaluate_m4b3.py:143–149`). Move them to audit provenance; prove test-only change does not invalidate while runtime code change still does.
- Hash chain and triggers are not adversarially immutable. Document local-writer trust or anchor head hash externally. Test a recomputed chain against an independent trusted anchor.
- `Ledger.initialize(held_lock=...)` trusts its argument; verify acquired state/path or make it internal.
- Add tests for corrupt SHM, busy timeout, encoding, export replacement failure, stale temp cleanup, and immediate post-send-entry crash.

### ACCEPTABLE for this stage

- Live execution is hard-disabled with no environment override.
- Dedicated M4B.3 dispatcher is loopback-only, blocks 11434, disables redirects/proxy environment/retries, and has one send entry.
- Normal request preparation and D-before-send ordering is source-correct and was independently checked with a separate DB connection.
- Ambiguous timeout/status/partial outcomes are not retried; complete malformed/schema-invalid results are consumed as invalid.
- Windows locking and process termination recovery passed on this host.
- Missing ledger and unknown results JSON fail closed; deterministic export recovered from the tested replace-before-event crash.

## 15. Beginner-friendly explanation

An in-memory permit is like a wristband one process holds. A thread lock prevents two threads spending the same wristband at once, but it cannot prove the wristband came from a real database transaction. Here the issuer is an importable Python value, so a caller can make one. Durable SQLite uniqueness and a validated D event are separate checks the dispatcher must perform.

An independent fake receiver is stronger than a mock counter because it sees bytes that arrived over local HTTP and writes its own receipt. A query only after receipt does not prove D came first. The pre-transport hook plus a separate SQLite connection proves ordering for the normal route.

SQLite and a model server are separate systems. Committing D does not mean the server received a request; receiving it does not mean the caller committed C. A timeout after transport begins cannot safely be retried. C must also be tied to the actual complete response, or a caller can write a false result after D.

A hash chain is a sequence of checksums. It catches an accidental changed link, but a local writer able to rewrite every row can calculate new checksums. A trusted signature or external head is needed for tamper-proof authorship.

Buffering every response chunk lets a server make memory use grow without a bound. Streaming needs a hard cap. If exceeded after send, the safe state is unknown because remote work may already have happened.

The tests prove named paths: thread contention, listed process crashes, replay checks, Windows lock contention, export recovery, and loopback behavior. They do not prove power-loss durability, every SQLite COMMIT failure, real Ollama behavior, human signature authenticity, or immunity to a local writer. No live inference was attempted.

## 16. Final Git status comparison and safety

The complete initial `git status --short` output was captured before source inspection and is reproduced in Appendix A. It contained **451 entries**. Final status contained **452 entries**; the only difference was this authorized new report. No initial entry disappeared. This is an inventory comparison, not proof that already-dirty/untracked files remained byte-for-byte unchanged.

No Python source or existing test was modified by this audit. No commit was made. No live model call, Ollama/11434 connection, Gemini/remote API call, Docker run, repair workflow, M4B.3 repair fixture execution, or real experiment initialization occurred. The requested suite used temporary synthetic ledgers and mocked local scenario data only. Inline proofs used ephemeral loopback receivers and temporary directories.

## Appendix A. Complete initial `git status --short` output
## Initial Git status before source inspection

```text
 M .env.example
 M EVALUATION.md
 M README.md
 M blackbox/investigator.py
 M blackbox/providers.py
 M blackbox/repair/execution.py
 M blackbox/repair/patch.py
 M blackbox/repair/pipeline.py
 M blackbox/repair/schema.py
 M graphify-out/.graphify_build_state.json
 M graphify-out/.graphify_labels.json.sig
 M graphify-out/.graphify_labels.pending.json
 M graphify-out/GRAPH_REPORT.md
 M graphify-out/cache/last_query_stamp
 M graphify-out/cache/stat-index.json
 M graphify-out/graph.html
 M graphify-out/graph.json
 M graphify-out/manifest.json
 M tests/test_repair.py
?? blackbox/agent_retrieval.py
?? blackbox/agent_worker.py
?? blackbox/deadline_worker.py
?? blackbox/m4b3_ledger.py
?? blackbox/repository_intelligence.py
?? blackbox/semantic_verification.py
?? data/codex-fixture-audit.json
?? data/m3b-docker-audit.json
?? data/m3b-docker-proof.json
?? data/m3b1-docker-proof-final.json
?? data/m3b1-docker-proof.json
?? data/m3c-ground-truth-audit.json
?? data/m3c-live-results.json
?? data/m3d-paired-results.json
?? data/m3e-negative-control.json
?? data/m3e-paired-results.json
?? data/m3e-post-prompt-repair.json
?? data/m3e-semantic-recheck.json
?? data/m3f-ambiguous-structure.json
?? data/m3f-final-results.json
?? data/m3f-fixture-audit.json
?? data/m3f-injected-retry.json
?? data/m3f-paired-results.json
?? data/m4b-fixture-audit.json
?? data/m4b-paired-results.json
?? data/m4b-proof.json
?? data/m4b1-fixture-audit.json
?? data/m4b1-injection-probe.json
?? data/m4b1-results.json
?? data/m4b2-compact-probe.json
?? data/m4b2-results.json
?? data/m4b3-results.json
?? data/milestone3a-codex-handoff.json
?? data/repair-container-audit.jsonl
?? fixtures/repair/m3c-ground-truth.json
?? fixtures/repair/m3c-registry.json
?? fixtures/repair/m3c_ambiguous/
?? fixtures/repair/m3c_config/
?? fixtures/repair/m3c_negative/
?? fixtures/repair/m3c_trim_total/
?? fixtures/repair/m3c_window/
?? fixtures/repair/m3f-ground-truth.json
?? fixtures/repair/m3f-registry.json
?? fixtures/repair/m3f_absent/
?? fixtures/repair/m3f_checksum/
?? fixtures/repair/m3f_feed_multi/
?? fixtures/repair/m3f_misleading/
?? fixtures/repair/m3f_origin/
?? fixtures/repair/m4b-ground-truth.json
?? fixtures/repair/m4b-registry.json
?? fixtures/repair/m4b1-ground-truth.json
?? fixtures/repair/m4b1-registry.json
?? fixtures/repair/m4b1_caller/
?? fixtures/repair/m4b1_config/
?? fixtures/repair/m4b1_index/
?? fixtures/repair/m4b1_injected/
?? fixtures/repair/m4b1_negative/
?? fixtures/repair/m4b1_runtime/
?? fixtures/repair/m4b1_scale/
?? fixtures/repair/m4b1_visible/
?? fixtures/repair/m4b3-ground-truth.json
?? fixtures/repair/m4b3-registry.json
?? fixtures/repair/m4b3/
?? fixtures/repair/m4b_average/
?? fixtures/repair/m4b_inventory/
?? fixtures/repair/m4b_negative/
?? fixtures/repair/m4b_origin/
?? graphify-out/.graphify_analysis.json
?? graphify-out/.graphify_build.json
?? graphify-out/cache/.gfy-replace-bak-18f9v81g.tmp
?? graphify-out/cache/.gfy-replace-bak-_ci_h6sw.tmp
?? graphify-out/cache/.gfy-replace-bak-ib1jfr5q.tmp
?? graphify-out/cache/.gfy-replace-bak-la3o13tk.tmp
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0049bf42567360e3b56fa59ec2facf2ad24048251331b520352b9256a891c214.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/009e704ff52bd82e5335a8f7fcb67a3dce2ef45657d41291508a577769740903.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/00a164a3e24bf8cd8a30bf9195c23006a65cd1abe09e22074ce72a45a0b06354.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/01465f566e4ba96e86188061c43ff0ab046786e3095236f6a7db1d2e1574cc71.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/029b758d28dec6dc2303c141a294c3e4392f8b52b0c50ab3ccc4e5dcc69c956f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/02efc20f99183cff2360f525ce7b5bf71cbd68db3e060f96ddf3be504219f2ce.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/036c48b24a869e568128084dac671a86cc298985558b7fe7f585f20884262986.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/047a570e3c7dbf652290adafe84ecc14c666e189d169962e0cf7559f67f9d588.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/058f777e30554d06bede5a5cd4d47c7f8ec27dee8264d5d796613915e640552f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/05ed181d2db18535a0eb6b80a8bf87de53510fc35400c285b80e02527bcbdb65.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/069821c8ccd14e448282cd1e58729e68eec47213639ba21b75b6042692f2ba19.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/07ec46a2e4ac82ff3f0d544371402d9070ff47489898c57e27ee6480a6acfc8b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/083f8b471d252a05f5facd0fce1512bf814e9313ea1fd84fb92da2772e99b868.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/087072998e6c28869d3bbb2440b92c1360b5232c23e96682dd53ee5b7b2601e7.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/094674e3a8793fb2a7976c31e90bcbbadf033b4090881f026b1bdcaad58b4f4e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/09a0b47dd8c8f0ddf3f5377b536e6d352568378a7c092c7f6c1eae50120326d0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0af3ace683c4d221e3e755d014dc89b183c71c18f95930c8ceafe84818fca7ae.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0b22ee495c9ee552db14c9d07f793c6779ad49d3d46cd4e7eab8f00bedb99eb6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0c65551c322f19d40dd8205a75df776a4dd19e56e91c475a00b462c2a3cd86c1.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0cf62a81da68b16ef9a32d7e7fd871492cc6834416017086f1382a67087de8e7.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0df7539748a69843634bada90ea5064ee7decb60f7ec81a02cffa54681b892f2.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0e99f84f6b7e8e2dbd8181aa78ad23c9ac2f29228a5ca51dccbcd55b415d3b63.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0ec7dd9ab62099e563602c7093fece37ccb49c86d66441d9ad259ddbdf725e53.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/0efb33bd98cdd04af327398af8bc4146621b8d76706f7cf85968c7416364e784.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1074283ad37a69214fc9a38a73dbe501af5c7ce5bb24065a712ff5d93a791e8d.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1318896dc2c03b906d0ce6c036e819a6b024d0f7ebae91c245b1620c34677b43.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/135ba8585a06e6df8f86e86a918a0c0ea7ae3318f1139cc45b02f8322cf54d20.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/143ba828d40a25a643f863129203de8d2fab656a16443ff39d04541ab7efe705.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/14ccc001ad29c0628b3f010abd12b90d02f6368dbe6af050a319254f4a8d8a82.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/14e40d73e4a5b7d667230dfb72733e5fb30805478362f00849de686fede7d0c1.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1707e8fa0f3a5c68af2f4c4da7ee6ef5749ca1706a999d40b29ad8a23c6cb710.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/17318bbd43c83eeb64ef75c93d54dc3381714b8f2373cb3f2b9f38e333b7928c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/188df2c36f24e2aee55daff44af4aa4b13984f5a90455593621d367a28600ca3.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/194fc5be1e384674d6c3e8b522166fb7f307b68f7f15af62bd35f391d88dc17b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/19e16d9758a4a64446e9d7fc5c75178d68e3347527feaf355ca7ba84751aefd0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/19e4820b015b23e20fbe7256577caef90ce4b24dac87870a98cbcf67859fd14e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1a449a1478a9d82e2b60c3dd6ea774d496f452468d911e818445da25fd368075.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1a4f20b3b3c1e26ee45ed7691398cf3df80aa3b0821ca5410ca81bf1991e4e6f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1a6247a5ec12458ab3cdd259aebd101dd09daf84a5e4ccbff44b7ced4c4b4ad0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/1deafe8f3b2cb5028a2b702955cca731753a57a2f4046db1d72cd9bbc5621b1c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2194b2ea8ff8863b434955e0c9e51dd7cbf12f42f6c15e297c7ac837bfeb2809.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/21ab3585fe9b451db553dacea28fb9c4bbf4685487adf89b97ae0439c47ed477.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/22d119918d78d1fa34bba2257730f12582b0343daa156ef0ec1cb4ccbaed3418.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/24579dedc67959d1dac9a7dc5706e0767049b1853bfc4064ad6829a044b55126.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/247b1d302d75f9b5d75c4ffc01e096ef826d59f06a3221330f87b49941c99084.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/24905cc4d88ebe3aa9461dccbf5dfb4446e30b894551ef360397414ab9b52412.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/24b7edc7291d932e0d44289e42b66e63ae9fc26fa8618e720cb753a43715b0b3.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2509dba1ed830b2ef8f7c468b782b4d226c0055c8f1485da537f6d4ea218bbe3.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/25657130bd252c9258f107008649d5e473958df0d7ec727f80d58c52b5c8a448.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/26703d33e8fab835157c8045010adc3e53c8cba1ad464f886c088d62bf27a82f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2804981fe1f63f592e29d82af22e68f035046a5df3bde4122f2ab1be1d51e873.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/293e1b0fe835a67796edb452d56e1e558a094d7bd0014cfd7d7e5b969a87e76a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/299bd2013a29f9523dc616ecc44eeb6b9cde24fc8ecee7dfba3b6aeee934f381.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2b76c7d5731f4facc358dc0405393588d9671e494e979a38f4cf6af08fc2ccaf.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2b948a3c22bfc94c918a4450cd6070b2be5e685cfbd78241941f90ab004a887a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2c6d3dd46af04cbc912ff5c30a310928a568051705c5ce0a0b6b72045028fd59.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2c764239022c1b0b88f992a2d2a769786cb5efcb2a2e948a86bdb3ee17b28d50.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2d4d1f4b11fcea9809db55b3667aed0d58773657207b8381d8c417cc06210203.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2ecb2e8f49d67435ffb2b739ed9820bf5691d9308eb70d7e41ab1adb97920e72.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2ee8cdc49315f51db052cb718004b9c44adcdf5089a969cc344bb164987240a0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2f5a1a5b7ee08494a8cc68b1e9f25db797d803156cb7ee235f09b6601c91ea2b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2f836b36a2fb6599b631704aa17e25cfe497ce9a34c528d7fe4f8a54aff1c94b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/2fd0917b5e47ed72358c7c33c4724b38808ec032e01d767e9f1b4a7d46c03601.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/300213f2afcbf69472f095e4210fa7e91d636de9c57aa0396727f35eac16f458.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3081c5ca7eb7238b645f8ff4760ea4e7badac41cbff56c59dcd85fa22fa0c9c4.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3471296acd6631777bb1ce2b83869188626394e9e76270ec89b4e541fc5770db.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/34873399d92fe198acf49459a0d8af87987448da9d7126e52f1e224ac5bb0a86.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/34d40a4a069639bac1d919206a82615b812a5c4bf37ed4e11a03aad9b5f415fc.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/35276e67a8d11e1d242452947f6f9c6ee2eadfdc3191b1cf7791e8b97d6fbe56.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/36559606afcba282f95c01efc9c967448fd92749722a494c6f3bb805d2da90f8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/366950b45073882b9add359f9b63bcf86a9cc4ce215c2ef9cbbc6842a4f34d7e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/377da9d219c9e3d24b68f97fde58a7c870eec2eded0344900a32afef29a1aad5.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/383067100e2e0ea7c5238feb39b4ea3e02ae98be44336b772a93a1f4f5b0135a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/389bfce3c6b6b00476d924a4d09e9ad0f79a50ccbd15e59e5c8e4a2b37a38dad.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/394bedad6279e4f0c0a1f5163b5420ad015679ce36b6f6fdb21133ae3994f9b5.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/39a9028ad59fbf3de843138246bf9f87a462b09b1f74172c591f9c2d636f90a6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/39f4b2995bbdb6f30ef0bc5d31478a624cc3f485e5d6cdef59cc17db799ff493.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3aa4361c6ae503c26ec7529dc0c444530f48e8e3a4ef78657c26f74ea9877249.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3afb7ae20a7958938949a3b7020353280e497eadd26cbffdd7abbe3d45940330.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3b45b21e4748efbc39226f0c0ee5eaad1f37c4794725f9b1cca138ef10d9dc1f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3b4c20d868eb220a071bed92ed5b13a39ffd18485f8f749050e8fb39ef8527fa.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3bf0437b35d9d969f1730ce7ec3db77014d97968fd34438717ad5ccde58a409f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3dcb2b4e1bc4f796310448cddb92cc3fab35d57fac0529eb3795bdbfe5701b5e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3e2a17e14682153539582ca6981e25fa83df2dcb72f2dbd3f8af5f0eb084a8ec.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3e2e11c223a6a8056c56b3fb8f5dfbb33d48437065ba450fcb5033531d2fde2e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3e50a0aa2f0ed40ab98042e8cec47ffa5184b44c4c1f8508857842298cf65f76.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/3f5e4d187696eb740d9d4f9358ed4e3437de75ccfbb0538d056f48dd56d5a3cb.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/43404002c93bb391f94815fe67e4dde416dff310eb6b78e1376f2ffc835bf189.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/44c11223f3aea35b4181b1b488fc36f829ba129b35f12d35bd24b9062e3ade8b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/457fc67fc7bb919de0d06cd7f821b61381c52df3da548ed3e49d32deb9bf4f99.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/462234bb7eb668cb079cc92ad23b3f3930aaa186989390ea04bf623a7fa40c33.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/490a3259c18ef63e57e97d8d39e4a915569dda19c7fa1beb0905cff48f9329f6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/4c60c53403be8652854c6126359d34087bb296f7c5bed57b82edcbf64aaf72e5.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/4d09b1b8555cd497a938c8f5ddce0aa66a62df747796971b3bb5e619ab78be0e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/4f29d06ed9775a13166d9f0ef91ec0a214b639b1b493988485a55d4d877fcd23.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/4f3adc4d8cb7358a439170fd3ac4cc386dbb4f9f908b2ceeaf8cb13a7696e5db.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/4f3d6be3baae5b51b2862071320be5e92bddf218eb240f96b2ce7751aa990381.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/50b45d3337ff4e718fecccc7485056f582aaaa97c3e1afd6d72e8276b32b0272.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/52a20c2875a477fe4ea887892007b38f1a555f44f788c9a63e8959bb674e3846.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/52f448d493c705f56fb27e4b4a4bc3daa6d34f3119b6b077878a5b6d09b0301a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/54690c778ea1751840756fd70ac905f01d6828187b864f2d1e1feabcf6dbf315.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/55b0cb339550884b872ab4ba8489194b8d0a0f58eb1ec70ef85525f6826c9c2f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/55b5e8599a2ab7b9045cef41e71d0dad720f2e70ab09abc5a4b71fc1d932b6bd.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/56e18d4ce68f41ea652d5abc9c729637c1eaa4d939c5a8b8d219a581e71216d2.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5734e8e5208cbf3491934c7452ab103829c798c0310db8d10de5067987d58862.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/573e8041d7a0fc838b94f0eadf6f09dec13ce672305b66e1467bc4247e19cabb.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5741df29dcc069584ee989767cde031acd4b62ec8c3f1a3ea9ad2212aa76b2c6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5797cd61515def437d7df5e89bf8a7973f695c4a8772dbc4566daf2eca8a159b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5851153ee0e597dfb2e8cd6b70887737069eb6c48b5bfe0aa70c36fa43fc7f3f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5993ddbf1c718e1ef3536f16ef8cfb93ce23dd189206a138ccb8649b372c4e6f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5e678853f655c0889dd1befd88d1532660d96bd8f08fed66a5cdc21193295c1b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5ecd21d89959fa881a6d03be121919e52283628a24f8a055a454a69edc2af54e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/5f2d660a86c6fe5f053012de91ae0d11fd516780697edae006c7b07e3506648c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/601e457bf35fa7b02e05c0c95edb5d07b2318bc20080a381c2ed6d490be9df85.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6140116479946a9933b811444b08f5989c45063dbf7fdfaead16f823c1422dab.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/61e311166a120ebfe12b57ecd9bf112ec7c693b8f3bab4133cf91264c1301fea.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/629443d2a885eb65c5615d8dfdaaa2b6cab91b81d97f2a172b7a8884056e87fd.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/629f418e0d694437a0f4911911ce717a6573d30dc79d7c42bb22be0987e13b98.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/631813e8e48ed999fd30a7c111d7dd87c47692fd363f461c5842065d9873d9e1.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/643911a79ff09a54706245b9ba301b670a54e50da3f4b671eff419c04dd67fd9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/64d423e392e47af708f897e4498d180e437ed5f61a24047eeb728800530a3f92.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/661242b4f9f4ba1a0cb4604582c29a922f8b7a05f26999c723bc95d2ada3875e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/667f1b1c3c1ee03c0445bcafbe3c1fa7a3741ab46e97439e3300344bde5b2583.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/66929c19bca142e45491fe9aeadc43fe1c25d2a8d1a956b9ea59681e365d203e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/66b0160500fea780eef7b1efa2abff97a38ff60d12ab4fb19e6d00f6845da393.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/66d7defcc6f761565b4aebe3f388558be4a91d5c256ed742964e48b5b7662c99.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/66deaea778f7f0d9118ebd7c1f22cb1ffc80fa21933b75b866b7fca773fbbf0f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/67f6e8aac48f0de9e98d71739eccc6fe344485844013a5c65d795439273136ad.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/69f7422bd070deae8c59d603ec44b3cfbf6ec736192501a186382446a09f947a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6a8ec80ac047a7c9a6a53a6c8c77e56c612310bfa597f661583163a103a7655c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6b767d5fc2b95c8c001a5ef50d95e9d63558b1cacaf031923f0df47ec2d9786b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6c138d81e6824b88549d6cd1fd43a5ff61d6cb04160e8c19fddad231dfd7845a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6d05d5b1422755983564a535db509aad0f1b92e4990b7c26f65086d1a0da6ddc.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6d40828942c75228113f42ae4e3e52ea9e1ce642e341a3666eb48f718a6af843.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6df6930e6c7107040b1c259927295bf6ceca2abe2919d551dd9875d75d862657.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/6fad61476e81df870acc721085e879b71405e14ef064329b39776faa2896818c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/707596b0088743a0153c2a4976d88a5d02e5718ac0aafc50efa2993f3de29aef.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7262ec451c14ea5b1340015730ecb0091032867509b8650f315ae117b18b04a8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/72cc23221dd1353c246da11015cb27cc5262de55972c075f527e89497df76e73.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/73ac13415584d5b32321a062f04b61f26fcd23e853c86b08d837ed078a271c24.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/73e840356719428780fd5e49e35e85b154b572dd850dd62166214a466c30589d.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/744a850304b5d1528f6a8a017eb30ce66d273205b487b76bbc940833e2b79ada.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/763494aad9d70bf098cd8fdbc8ba4fad3afab113f25cd996ad503e80687014bc.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/764c76d9576d216c0b3f4f717cf3ea8d34a09ed7893520bb9ebd4cb054502fa8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/77602fbe105358065ab1b9b6246c82c180d00902499dd3d6c733907938ec20be.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/77d22e1bcf31ba6028b607f275f412045e582f71f560373ef89ea5f9584511b4.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/79bba66c5de1c0f2501dc302ac46e84e8c7174e8ed02e5e9fbe0e4635c0b3308.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7a33d7ed518b5e67950f563150623044044e10d644a767ba9513c137320d4341.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7a67acd889722c0ce0eb3fcec9757b4ee49a1512e661e03452de9469d8de46a8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7b87514bb367adcf9c2649bdf6f98a0adca85f3e3e274149ecc08556201b10cc.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7cfbc21a47554370123a22a8811a2ad9add1558375977a80ba0a6627f5b1fc2b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7d03f31d5925e65e8672d239cd8618fc23ac2d85b0adfbd78da7bc527618386c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7d1cd1ae7fb23bc7f0ab4d9ff1593fefd7cfd2b6be54284f15545d7a1061da4c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7d84e03bb97008e343feaf2e4e45a5e93ef824903e0a84013a289d09db9b4652.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7d99de8872523055669b20ed314c4c0627a26806d43fb8bbf1c41e50087f4526.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7e82679dec49b99c4eb5a0c2b99dd5fcece2a566ae9f33a9c695411ce825e5e0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/7f9d4368abe1ab2053a5c6823399886d7700f814dd92f3de02a7a58123d5c3ce.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/801c9d8fe22fce0cbc9274080cf940d126ef11f1c9799484cc2e31666d12868c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/80963ec09b45e8c40d26007da869566562dbdc97e2a325db8978c9505cdf20d9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/80994e5f7875a81e42962286dc182dd8359a991187f3fe787b33029319b226b7.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8135ee661e590a09745bed1def6e46c4d54e0f111421f185c7504b8dfb38b466.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/81ce23dd010f3507f529914905b2972f1401598b3b51808c8d9f936f026e7aea.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/82060ee345c276640bfe67f0cd0e9352c536e59a389f64ca1ec37d66c96b4ccb.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/82428f5e8be2168da37cf95160cf7cddcdb9195f7ccef75ca6145b859f00b13f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/82df60144235ea8225344f0d1a36cbcd755eef7e043e522c90e8ccfc1792f2ae.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/833a1d9077a0d597a9a44f9461bcca1f33052f4ba47cbf40c6fb88d5ddc9e500.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/833e7f588c45226d9e750cfbb4256bb1c29f489d4cd73a047a29677e360db155.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/83bd6e3f9d748e93ddc4314de74cfb70999bca44360bab8b9cea84a5363911ef.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/86358cecb563e5869b42cc76e06816f3a56434fe5c27f9395b1489d7e81c0c4a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8709f489dd365795c5653db7a6d221478816730145ff42e1f28d888784455e78.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/88992bf82dfa78f8cc6ab9c3b8fd3248c03b0d578a102b674b358d970c15b58b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/889989d64df0f9a6779f373a3fbad58eb6c84d1435f2c02959ea4dcc6399a0fc.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/88a89ba8d9ec165d354a965447419c8fd81e3ad06e5b4b32d639fa47040db64f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/88f448b7ecbf2e8203a7218433c0277dd65425076f3a2cc28c3e3b619a01257a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/896ba810d860cf6719eacaaccdb858bc7a7d6c4bb5f7f785f7f2f3d714fbeeb9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8b7b917daeafbb43fd488b5448baea976b5c256fb1c9c7738c1e8a95315fe773.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8cd4ea750c2f432baeacc08fd4c3dff49b42b6f088a38fa8bfb4516bc0c26ae4.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8d13b5abc5e44a9a33eb27b109e70dc57fa96c4ab920e12915a315fdea5790c9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8d22d93eb32e66a4bd93cc507136e2d7a905d5ad764e002294713c7dc194de31.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/8f2ef1af25c5334d2f45c682907157a7b3221da4954f3fe71074c951a0ea8707.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/90239552872555617ee1fa0c02d8d020199bf775bc264996803a7ba7eceba594.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/916a0872f3014696b37a8b76196c02a5187e4ead1eed9727734cd3afba7d39d8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/929d04c69c2ad61001068b2aae1b819012a3866112fc5532893522c0185763ba.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/939084d19700f5e88e1b654010ed4c1a7b2b41ed5be68b95dddf6aaff04dcb8e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/941a7e0b2104c1d9b582d47b62bda0d95e82fec694dd2b7319409d814b4da510.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/94b402e86abdb7cb5d7024475492ec031b03a2ae2e2b5ff67109699edec31abe.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/94c8ac05bcfa8b381d0a91ee83b96026a572dcbea6ba685ffe7dcafefeef2301.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9597c89b3e6a6d7e7d04b2fe3ada7c050731fef998fc925051c3ad4cdfbee727.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/960544b842017716326ca417cb2a449c52e6817639e1e62def885102f0aaeea7.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/96157fe8c7a0badca10dd651f7327f65c896dc024ef235a52bbcfb1e57dec98b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9941b96acc31d4ec40758b1413b22031c69cf20941d880f31fad290ba5561421.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/99857521a3e86694ab9193f7aa1142a2e31f5f1fbbc1622b05f416e2331aa805.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9a42a50f05d812ca669834268c53d30dfa18f742216a5076ac3efb3b5e25e891.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9c2b55da4e97e7a4244d1ee91a27fa16a4a2fbc19297cb1b3620fd59bc42136f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9c61c26feead11b000c8f9247fb07f0e6c63d55bd6c366edc11b84dc4561b4ba.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9ee024211ef5dcfbcc38bffdba44c5c1ed0756ef6e736706962dfb4d904ebb49.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9f6a474ac307a8369fef2ac38c34be22f2fd98c7882f8b79b140192875923dc1.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/9fb85e49db733273d1e461f1a17103ead69d1759085ccb08fc3dd8e57cfbf650.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a05002da774d53a2264199425003b1588eb189a6ab7ae31369172dbd042a402e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a2f6cb87d4fed3f929236cca4d3eef715658b6e70cce6332bd4af31ef3d58f00.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a3fc586ed283a9a06c71a8baf916cf14cdb76a8228d136a8989590881c7bc78b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a43a094b700eeb17cb2548914b37e67c2004765f81fb8dc74e934145cc63f8b0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a779be3c7ba80307cb0df0ca6eee0cb4926c8ace77319f8dd730577f11acd293.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a8b9ad74a196adf3f441bc5d62f648aad5abd1c4e345b0f3fc5f54324009adea.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a91cf8a77f49d9e50e805147cd9f949be9157ff90120a8a88b45bd5d83f8c567.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a9853b735782907a20d8f5b4991bbec080138ac34756cf017dd134ecb65cf71a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/a9b108f058fa50e34d0f269a6dd9703cf0501c7332bd23454049d2bb59771b49.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/aa96479563d0640fcef7ebfcd6c2dc9ba9b6188ed4ca5ac1094c815a06cb2b1a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ab16700a6e2c70f01ff5beaca57366edace9cc16e79ea4079849aeae7de7fdcf.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ab391091576133b851e9f8fc3eb8ee297c406897158fff6edd211881f2ad3310.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/abde0b180fa0575509be2b9eb9f2c66ce87fd1636f46ceca69fb0181b277d092.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/aeacf02fb7be3c2c898cdeac92362cf6f0bc97e697274745025eb1b916372b27.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/af74c4e12cb7cb7e8fefd44d1cb37d5089176bc06961f8ad82f3f7d1c37d9794.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/af8da32d0487288dc207652e3f0717e353ad430334857bac7d8c652186f2d595.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b075a122768bd2174cdd78e04af2b5f90649045440f8c6d36fbb908a53c09405.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b08f070648bb10e8f59342cd4ac7b5597aa7a67e6da51d06796392f1165e2e8c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b1f72e394909fc288b84ed82e30a91037cc1ae4609cba410da4f7bcd869bf490.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b31def0b23428296aa4fd69523aab01fd78dd3d005187ced2b37b2d15f7501f1.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b3498412169b7fef54042d07b931899f4e7a242db49441239c1d6f5ed22184f9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b4b6ab3fc428e3c8331aeca240aac070015e2a2f1e2c183a2995e14ceb96581b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b56a4694bdb9828798b8e2a0c8ef71d449f75641af25fd57e30555ccb9d44167.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b61488a7683b1cfe1b69c60ced179b81b495f9db8eedfbab38aaeab58b4ca27c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b63063e17a0984fb4395752bda606a0c18fd0def773ef31e7db3bd4846ac2339.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b7ad049d2f5d2235e1d9d887288d321c93599549683a9125d4354b6107e37b75.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b7f8ce3972e15212050b16f9cac622d097473a519a0c6589566c064491f0235c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/b91b1182b259fa00ad29ddcb5a157b7bc93a36d49e3185b7b9e20a80158e4d63.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ba08642243fb1b5cd37256bdbf07f3c836da64bb5ddf9106b6b14246824b7228.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/bae4a45c1f406c436651a27c50a601be84de20be3ea67a5261636fa29974a6f3.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/bb346318d545bf64268f4dda8db0955e54649816c321515dc02521639a77fb09.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/bc5e9022cac0f3b0886020c211308041ebdc9aada4bd54ac9b3878600f1ee5cf.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/bdc13adb77f12165a70b217ad6182cba6ba38a42be57ab79970ca0a8362a93e9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c004d4d5c9045a5f63d367903213eff9c48ccfdfc012b843a9af0a075ab51c69.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c342c1e14f5f997763211c2c7f84254f01ee08e5775f130861b46e83c082441f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c35781fa16e25f5d26ef3e14a10f8f45e31728881ba2378f7ed0b37cefacb1ef.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c3aef44f08d4ba9b731e03524c5a1976bfd537ae6fda54cd9b6ead5d37051890.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c4c189f6c6eb0b5c6fca322b9f85b122bc675cf72bc20fc9d12b302251cfc9a0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c6b34b2906b45c39c888c188ed46d2b973ffcf37299f90a2e04d6031f4e18ebf.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/c906dd42b949d71eb399ab44c5abcd3a5d4dd9ae073548f48f4b9005e61aec11.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/cbee74e8ef846e3c24582e9db05cc19bf01edf84f436c36edafff90e18083570.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d01295dd30fc5308b1abebb5a0eeb69409a4f0ba111ffdbf25557aa1373bb6e8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d0758dc1663ee4cddee10c89dedf69ba14f46253a0a1738813d9983dbd252d5c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d19a355df2b9682f597f0bc95a8467bc99be4ad0ec9da84f46099779a6e84300.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d1fc08a5bd60241c34a9f3ad9ac81ff9ed0804d16679c99bc21779ecfba8b910.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d260ded348cba608f72faa92165185645127a0a20ec94a613ab2e36ba1cb5734.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d2693f54798e3860db840cd98d935a9b48f667105f3fd9d26186f5ad8d0e2d15.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d29749dbd46a87e8b2c03834f572f8532f2fb826518de607162964214a8b6cbb.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d3c7c318321f3e5cc274e41790ba8b438615163e0411192cedb52ffac7e3789a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d463c2856e683160825123c2f3e1eff568e4bec9c1392bd2a29e00fcb076d10f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d4787726e8c94ccd6dea3fc0ead3fa35bd34cc846cf6bd2b43cf236914fd5b03.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d4ee2600989ed1ec3698ccbbe860e3492db6594a7d3de2e0168e2c737d004a19.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d6828d35e1f52ff939bcac244306367ab71b38a28b8e7b4c7647e391221db030.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d69c4919995ff613d51a6a968bbb5bbc0bc215b6c7b16d2a20280a2ca38af850.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d6ed6f509ce4a2644dfe28051d5ff035a19e5b96b2e2075559d2ac259ce0fef9.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d732b1c197ddcaa9c26444b5922b14348fc2874b57258d968d436d6a4c1efca2.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d7cbf5183d18a9538ba78aecf6de07125c7cfa4ab7ab439ca2d8a74281f0d829.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d80b47e3a26d066c74d1fbabd90067d1b6abfddf0968fae6c98a524e16fc28b3.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/d88d8a19c66a07b7b4cc6d9b2398ade62b7061a46c1c4c5bdfc9263fe344f760.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/db111e2f507cf6fdf00fcac363687e31373e79685ff6e00069e8e123feaa2903.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/db1311ec47d5b04c7f01e7dfac530f1d9313890776e61a5774c4e76bec77e140.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/dbb3a499e79531b5209c72200877c9649f7143ec07835ca7578431aad578127d.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/dcf6e8a32f87bb74f53a3857123e0b18d5a1a6b463f822fc706507398a5fd8b7.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/dd02144c699be734ed7c10d3d33edef75b5d7cd77d689a3cc23ec07776b92051.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/dddfe4038cda003eda5dd9874a7111c25b1af0823f60e4cf413216236f2a64a0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ddecd5c9de73c86b57eba6cd8cca726152a398ea66252b8b51f2adb18c5aa51e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/dfad93afdbbd8d6d54cc63c28d3084e9d725053db3aef71ed815c157d532c73c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e45bb2413998c8c810b055f31cb8989837687af68ee4d77966b19b5f9d9dc396.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e497532667e2b5b9aea0c4f3135aedb4059b4870012e5639285f1e0817645dd6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e5d2b24aa6520cc96af49774af48907a0a2fcc6f96bbefa1bff476730e686851.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e661d06d9b0d78c4802d3ce15ff76389d8e852d2588caea32620e2a283a56122.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e69127fed868c1e665dec224205f193f35589bb1369b70863a3dee9caa344e98.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e6a2a1d2ac0450a169e1ac13693f89ae16f31401666b563a911ff054add332e6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e7c2b289ce287008b1b2ec59c7d136950365975f5e422d3bd9c40c23afb7ac3b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e83f7527d5eb4bc3cc7b9d45d4882ac2dd602257a46bc657ce6d21c85a055dc0.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e844d1fd27b8cd2056e6aa0abfcc82ea39f794cab1a6386a8cfff5ff9ed003e8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/e974691b26a9bb8de174d44c4c331aeb4fbe6750214a94ecd57a302eb9e07e1b.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/eaa8569fec8f1ade0963e1b0be9f411a88e8b96e6f92499bf7c67e437c771b68.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/eb0ede3a8522f5c89dec672d052453c2718b5b45aa58543c84e00782df2b2e10.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ebc64f9857c5c360d4cda714b3bbb5e5f5f961d4d3bd7a4c9aa279c27aec7c29.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ebee7c355dbbd58832b8af8b13374375f27c504a547baffb04023f025c088643.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ec4817abca5994826be266a6cf5769776bfd316c93c2ffdc9f045657326e6f53.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ec7c7f5ab517f419a2406c3ce8db0e15c75cfe9ba3c2f3a36eebe3a85e8a2926.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ed8525e95135cbf8c69a2708531f3be00c14b849267d1b1826a56dfda9eeb590.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ed90dc6db44395db337f0a41a6bd85135305de4ff93444813cf98239e98443b2.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/edff243dadc9054ac76b9109d4346eb1eedfcc50db25ed598411be16ea6bb39c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ee017c85dc920a8617837520ee7b73881494ec533b35b92e63cba0d2aafa5990.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ee14452444d292ea49fc02847597644d273014ba951e1acd522664397ac094ce.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/eeb664963c7817d3b5b9adc6ceee2741a1654b88c45f521b307d66b86d6d1177.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ef634bf441e927399d08a2f688ad5aa31a4abd3c351c41c0c0d331de3899d03a.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f2a3a1d7ad16468edb00f92b0237ed5222d4eaeeb605edba81e9e3c73bc89075.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f342623a58bde7c1aff4c8f7eab9788886aa548d6cbf7c73fd85c23d30046f79.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f4761a0aa750b70e16fc931b0d440944719b761b062719f50946a1c95d10f667.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f628a98bf8ef6764181484d2fbafebed1ddf6cd6a3df1d5b3443c35058d9757c.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f7510cdf9e1428b1129104b8beb29d9adc4a1b5b5f67918f0649f26640591632.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f85dcd461009f062c5a44de9362572b20fa01849d0db144b40b27c57622312e6.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f873da4a390b6a679dea8ef4b2f473e7b5ed6bbebb7dad60bb9ddf79068e0875.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f8a2a91bcd53c97a8264a46191737323232885822e913f91fdd0d2617f378278.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f8e8555763020d1326d98074b2311ac890ac9dbdf6b896d9d7939be48f49795f.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f92ffd30c9cd4abc3f372f9078f6d1b8fb1432344e1da8ca611539f7af0e8612.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/f93aba6d64d054cca15bc39385e179cbfe9c2b616539172a4bb45e372727efd1.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/fa16c731c3a5768c0c877064a14407c12f8d12815e91931bf7dfff4e9013dec2.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/fa23948fcff7d12d7a96ec8166463ea1a4d67823bdf5a46465f7638901c2cfeb.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/fa790860a14cafae1711feeb5e70b037d1ee4b916292aa9a7e29622760329b05.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/fb9a310002e2eed0a3fd24eb8db65c82b39db59c77f67fa4690432b7a0d9d5e8.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/fc573b3a0fc1c5ae52ab8f208dd655a9d004e5109f408dd3cf98713ab5bf4498.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/fe02870f8cbc64cc66fcfcdc32df4448c0b2a0816b76da8898cd5db8b6f98a58.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ff61f3181be3fa6420329cf768874a6f308cea6d62a34ace33a1e2fcf046883e.json
?? graphify-out/cache/ast/v0.9.102-s37-g1339418af9f9/ff8f83f756fc617b04bb33813eb86babbe184c3ab80f2f79cb6ba327d6c8d56f.json
?? research/29_CODEX_HANDOFF_REPAIR_EVALUATION.md
?? research/30_M3B_DOCKER_VALIDATION.md
?? research/31_M3B1_LIFECYCLE_VALIDATION.md
?? research/32_M3C_COMPLEX_DEBUGGING_EVALUATION.md
?? research/36_M3D_PAIRED_PREREGISTRATION.md
?? research/37_M3D_REPOSITORY_INTELLIGENCE.md
?? research/38_M3E_PREREGISTRATION.md
?? research/38_M3E_SEMANTIC_REASONING.md
?? research/39_M3F_CAUSAL_REASONING.md
?? research/39_M3F_PREREGISTRATION.md
?? research/41_M4A_COMPETITOR_ARCHITECTURES.md
?? research/42_M4A_BLACKBOX_GAP_ANALYSIS.md
?? research/43_M4A_EXPERIMENT_DESIGNS.md
?? research/44_M4A_CODEX_IMPLEMENTATION_HANDOFF.md
?? research/45_M4B_AGENT_RETRIEVAL_DESIGN.md
?? research/46_M4B_PAIRED_EVALUATION.md
?? research/47_M4B_FAILURE_ANALYSIS.md
?? research/48_M4B1_TOOL_USE_FEASIBILITY.md
?? research/49_M4B2_ORACLE_CONTEXT_DIAGNOSTIC.md
?? research/50_M4B3_EVIDENCE_LAYERED_REASONING.md
?? research/51_M4B3_FAILURE_CLASSIFICATION.md
?? research/52_M4B3_PROVENANCE_AUDIT.md
?? research/53_M4B3_ARM_ORDER_CORRECTION.md
?? research/54_M4B3_FINAL_LIVE_PREFLIGHT.md
?? research/55_M4B3_PREREGISTRATION_DISCREPANCY_REVIEW.md
?? research/56_M4B3_PROSPECTIVE_AMENDMENT_DRAFT.md
?? research/57_M4B3_EVALUATOR_RUBRIC_DRAFT.md
?? research/58_M4B3_ATTEMPT_LEDGER_IMPLEMENTATION_DESIGN.md
?? research/59_M4B3_LEDGER_RED_TEAM_REVIEW.md
?? research/60_M4B3_LEDGER_IMPLEMENTATION_CONTRACT.md
?? scripts/evaluate_m3c.py
?? scripts/evaluate_m3d.py
?? scripts/evaluate_m3e.py
?? scripts/evaluate_m3f.py
?? scripts/evaluate_m3f_final.py
?? scripts/evaluate_m4b.py
?? scripts/evaluate_m4b1.py
?? scripts/evaluate_m4b2.py
?? scripts/evaluate_m4b3.py
?? scripts/m4b3_layered_schema.py
?? scripts/prepare_m4b1_fixtures.py
?? scripts/prepare_m4b_fixtures.py
?? scripts/probe_m4b1_injection.py
?? scripts/probe_m4b2_compact.py
?? scripts/proof_m4b.py
?? tests/test_agent_deadline.py
?? tests/test_agent_retrieval.py
?? tests/test_docker_lifecycle.py
?? tests/test_m4b3_harness.py
?? tests/test_m4b3_ledger.py
?? tests/test_repository_intelligence.py
?? tests/test_semantic_verification.py
```




M4B3_IMPLEMENTATION_AUDIT_COMPLETE — LIVE_DISABLED — NO_SOURCE_CHANGES
