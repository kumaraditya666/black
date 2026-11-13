# M4B.3 Follow-up Hardening Report

Date: 2026-11-09

## Outcome

The second hardening pass corrected the supported execution paths for session authorization, completion validation, reconciliation authorization, response retention, and run-lock ownership. The full M4B.3 ledger and harness suite passed on Windows. This report does not claim that BLACKBOX is secure or production-ready.

Only these existing source/test paths were edited:

- `blackbox/m4b3_ledger.py`
- `blackbox/providers.py`
- `scripts/evaluate_m4b3.py`
- `tests/test_m4b3_ledger.py`
- `tests/test_m4b3_harness.py`

This report is the only new path requested for this pass. No live model, Ollama, external AI API, Docker, repair fixture, or dataset was run. Pytest bytecode and cache output was directed outside the repository.

## Residual vulnerabilities reproduced before the fixes

A temporary attack-first test, `test_second_pass_attack_reproductions_before_hardening`, passed against the pre-fix code (`1 passed`). It was then replaced by final rejection tests.

| Area | Reproduced behavior before fix | Correction and final regression evidence |
|---|---|---|
| Session/dispatcher binding | Mutating a live session's dispatcher to a custom permit-ignoring dispatcher still sent one request to the fake loopback receiver. | Frozen `RunSession`, exact session/ledger/dispatcher registration, process/run/config/plan binding digest, evaluation allowlist, and registration check immediately before dispatch. Final test: `test_session_registry_rejects_forgery_substitution_and_closed_sessions`. |
| Completion provenance | A complete receipt containing schema-invalid `{}` was recorded as `valid: true` when the caller supplied `valid=True` and matching validation claims. | The ledger derives parsing, schema result, normalized output, usage, and validation metadata from receipt bytes and the registered immutable plan. Final tests: `test_completion_is_rederived_from_receipt_and_schema`, `test_rehashed_completion_derivation_tampering_blocks_replay`, and `test_complete_invalid_responses_are_consumed_without_retry`. |
| Reconciliation | A caller-provided reviewer string, fabricated evidence reference, and `approval_result=True` appended a reconciliation event and closed an unknown attempt. | `approval_result` was removed. Reconciliation requires an explicitly configured verifier returning the literal Boolean `True`; ordinary ledger opens have no verifier. Final tests: `test_reconciliation_fails_closed_without_verifier_or_exact_true` and `test_test_only_approval_verifier_is_not_exposed_through_real_cli`. |
| Encoded response | A gzip response was accepted as a complete response (then failed JSON parsing). | Requests ask for `Accept-Encoding: identity`; any non-identity response encoding is closed and becomes `UNKNOWN_OUTCOME`. Final test: `test_compressed_response_is_unknown_and_request_requires_identity`. |
| Lock pathname replacement | Not reproduced on this Windows host because the OS refuses replacement of an open locked file. | POSIX-only regression test `test_lock_ownership_detects_path_replacement_and_database_identity` checks pathname and persisted identity; skipped on Windows. |
| Forked ownership | Not reproduced on Windows. | POSIX-only regression test `test_forked_child_cannot_reuse_or_release_parent_run_lock` checks PID ownership and that a child release cannot unlock the parent; skipped on Windows. |

The original HTTP request still requires a durable dispatch marker and a single-use permit. Existing coverage also checks dispatch marker/reconciliation ordering, one-shot permits, response interruption, completion commit ambiguity, and no retry after ambiguous dispatch.

## B1 — Session-to-dispatcher authorization

Changed functions and interfaces:

- `RunSession.close()` now unregisters under the session execution lock before closing resources. Unregistered sessions cannot close another registered session's resources.
- Added `_session_binding_digest()`, `_register_session()`, and `_assert_registered_session()`.
- `execute()` serializes execution against close, validates the exact registered session, and checks the registered evaluation immediately before dispatcher entry.
- `open_fake_session()` no longer accepts transport, checkpoint, ledger fault hook, or approval-verifier injection. `_open_fake_session_for_tests()` is a private test seam.
- `M4B3OllamaDispatcher.__init__()` no longer accepts injected transport/checkpoint arguments. `_for_tests()` holds those test-only facilities.

The registry binds the exact session object, ledger object, dispatcher object, process ID, run ID, plan set, output path, envelope, and model configuration. It rejects constructed sessions, another-ledger sessions, changed plans, changed dispatchers, and closed sessions before any receiver request. The guarantee applies to supported BLACKBOX interfaces. Python objects and underscore-prefixed test seams are not cryptographic boundaries; arbitrary malicious code that can mutate module globals or use `object.__setattr__` inside the interpreter remains outside the guarantee.

Corresponding tests: `test_session_registry_rejects_forgery_substitution_and_closed_sessions`, `test_arbitrary_provider_execution_api_is_rejected`, and `test_test_only_approval_verifier_is_not_exposed_through_real_cli`.

## B2 — Completion derived from the response

Changed functions:

- Added `_derive_completion_from_response()` and `COMPLETION_VALIDATOR_VERSION = 1`.
- `Ledger._make_completion()` no longer accepts caller-supplied `valid` or validation arguments. It uses exact receipt bytes and the immutable planned schema to derive raw/normalized output, validity, error metadata, usage, and completion metadata.
- `Ledger.record_completed()` re-derives and compares the completion before append.
- `Ledger._replay_one()` re-runs the same validator from the stored receipt bytes and plan. Rehashing the ledger does not make altered output or validation claims acceptable.
- `build_run_manifest()` fingerprints the completion validator version; the ledger schema was advanced to version 3.

Complete schema-invalid and malformed responses are recorded as `COMPLETED` with `valid: false`, consuming the attempt without retry. Incomplete, interrupted, oversized, and non-2xx responses remain `UNKNOWN_OUTCOME`. Receipt identity remains bound to run, evaluation, attempt, request hash, dispatch event, and the session-issued receipt object.

Corresponding tests: `test_completion_is_rederived_from_receipt_and_schema`, parametrized `test_rehashed_completion_derivation_tampering_blocks_replay`, `test_receipt_identity_completion_derivation_and_single_use_are_enforced`, `test_complete_invalid_responses_are_consumed_without_retry`, and `test_false_completion_without_response_receipt_is_rejected_and_remains_unknown`.

## Reconciliation trust boundary

`Ledger.reconcile()` and `_reconcile_locked()` no longer accept `approval_result`. The ledger builds a canonical proposal and calls its configured verifier before appending anything; missing verifiers, exceptions, `False`, and non-Boolean truthy results fail closed. The event records a verifier ID, verified flag, and proposal digest. Reviewer identity, rationale, and evidence references remain audit inputs rather than identity proof.

Only the private `_open_existing_for_tests()` factory can attach the synthetic test verifier. The real CLI has no verifier option and calls the ordinary open path. No production/human verifier exists, so real reconciliation remains blocked. The test verifier and event digest do not authenticate a real person; replay checks the attestation structure and digest, not an external signature. Documents 56 and 57 remain untouched and their approval gate was not bypassed.

Corresponding tests: `test_reconciliation_fails_closed_without_verifier_or_exact_true`, `test_test_only_approval_verifier_is_not_exposed_through_real_cli`, `test_approval_verification_fails_closed_and_test_verifier_is_isolated`, and existing reconciliation transition/race tests.

## B7 — Response streaming and retained memory

The installed versions inspected were HTTPX 0.28.1 and HTTPCore 1.0.9. `httpx.Response.iter_raw()` accepts an optional `chunk_size`; when supplied, HTTPX's `ByteChunker` buffers until that size is reached. The dispatcher therefore uses raw iteration without `chunk_size`, preserving short prefixes from interrupted responses. The installed HTTP/1 HTTPCore reader requests 65,536 bytes per network read.

BLACKBOX accumulates no more than 1 MiB of response prefix and independently checks declared length and observed bytes. It closes the response on overflow, unexpected encoding, bad length, or interruption. Only identity/no content encoding is accepted, so a compressed expansion is not decompressed by this path. Tests cover exact 1 MiB, declared overflow, missing and misleading lengths, a large yielded chunk, many chunks, interruption, compression, and reopen/no-resend after unknown outcome.

This is a bound on bytes BLACKBOX retains. A custom HTTPX transport can allocate a large chunk before yielding it; the application can retain only its bounded prefix but cannot undo that prior allocation. The installed default HTTP/1 read size is 64 KiB, but this is not a hard end-to-end memory guarantee across custom transports, other transports, or different HTTP versions.

Corresponding tests: `test_response_stream_is_bounded_and_ambiguous_outcomes_are_never_retried`, `test_partial_response_body_bytes_are_retained_for_audit`, and `test_compressed_response_is_unknown_and_request_requires_identity`.

## B9/B3 — Lock identity and process races

`RunLock.acquire()` records the owner PID and `(st_dev, st_ino)` identity. `RunLock.owns()` now checks the current PID, active in-process registration, descriptor identity, and the current path's identity. Release in a forked child closes only the child's descriptor copy and does not unlock the parent's POSIX flock. `Ledger` also records its owner PID and refuses inherited use; its child-process close avoids operating on the inherited SQLite connection.

The schema-v3 `run_meta.lock_identity` and `RUN_INITIALIZED.lock_identity` bind the database to the acquired lock file. `Ledger.open_existing()` rejects a replacement lock path whose identity differs. Writes, reconciliation, and dispatch check lock ownership; the dispatcher checks again immediately before entering its network transport. Existing schema-v2 ledgers are not migrated and fail closed as unsupported schema.

The Windows process exclusion test passed. `test_cross_process_dispatch_and_reconciliation_are_serialized_by_run_lock` held a child process at the pre-transport barrier; a second process could not open the ledger to reconcile while dispatch owned the run lock. After release, exactly one fake receiver request completed and the ledger replayed `COMPLETED`. No two processes could acquire the same run lock. POSIX pathname replacement and fork tests are present but were skipped on this Windows host.

Corresponding tests: `test_windows_or_posix_lock_excludes_second_process_and_survives_stale_path`, `test_two_runner_processes_contend_before_dispatcher_and_recover_owner_lock`, `test_cross_process_dispatch_and_reconciliation_are_serialized_by_run_lock`, `test_lock_ownership_detects_path_replacement_and_database_identity`, and `test_forked_child_cannot_reuse_or_release_parent_run_lock`.

The path identity checks do not protect against an unrestricted operating-system administrator or a process that can replace paths and rewrite the database/filesystem. A narrow pathname-swap race by a process with filesystem write access is also outside what an advisory lock alone can prevent.

## Live-safety verification

- `LIVE_EXECUTION_ENABLED` remains the source literal `False`; no environment-variable override exists in the source.
- `main --run-live` exits at its first mode guard, before plan/model preflight, provider construction, or network access. Even the later branch raises a separate reviewed-change error rather than running inference.
- `verify_local_model()` checks the hard-coded flag before importing/calling HTTPX. `initialize_experiment()` always raises `LedgerBlocked`.
- The normal `open_fake_session()` and CLI accept no test-only verifier or test transport/checkpoint injection. The CLI cannot reach the private test factory through an option.
- `M4B3OllamaDispatcher` accepts explicit loopback HTTP only and rejects port 11434. The tests use fake loopback receivers and controlled local transports.
- `test_live_cli_is_hard_disabled_before_plan_provider_or_network`, `test_real_initialization_refuses_unapproved_documents_without_creating_db`, `test_approval_verification_fails_closed_and_test_verifier_is_isolated`, and `test_test_only_approval_verifier_is_not_exposed_through_real_cli` passed.

No claim is made about arbitrary Python code deliberately monkeypatching the module or directly constructing private test facilities in the same process.

## Test commands and results

The final full command was run with bytecode and pytest cache directed outside the repository:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = 'C:\Temp\m4b3-pycache'
python -m pytest -p no:cacheprovider tests/test_m4b3_ledger.py tests/test_m4b3_harness.py -q
```

Result: **112 passed, 2 skipped in 198.69s**. The two skips are the POSIX-only pathname replacement and fork ownership tests on Windows.

Before fixes, the temporary attack-first command was:

```powershell
python -m pytest -p no:cacheprovider tests/test_m4b3_ledger.py::test_second_pass_attack_reproductions_before_hardening -q
```

Result: **1 passed**; that test asserted the vulnerable behaviors and was then replaced with the safe final regression tests named above.

## Exact Git status delta

The captured pre-edit status used `git status --porcelain=v1 -z --untracked-files=all`: **538 entries**, SHA-256 `797ecc5b2fc4b309db555de9de266bb0aa00d2ccef979e62161fd10d1554c012`. At that baseline, the five authorized existing paths had these statuses:

```text
 M  blackbox/providers.py
??  blackbox/m4b3_ledger.py
??  scripts/evaluate_m4b3.py
??  tests/test_m4b3_harness.py
??  tests/test_m4b3_ledger.py
```

Immediately before creating this report, status contained **553 entries**. The five authorized paths retained the same status codes, and no baseline entry was removed. Fifteen additional untracked paths appeared after the captured baseline; their origin cannot be established from Git status, and this pass did not intentionally write them:

```text
?? blackbox/bdb5/__init__.py
?? blackbox/bdb5/cli.py
?? blackbox/bdb5/engine.py
?? blackbox/bdb5/errors.py
?? blackbox/bdb5/models.py
?? blackbox/bdb5/scoring.py
?? blackbox/bdb5/spec.py
?? blackbox/bdb5/synthetic.py
?? blackbox/bdb5/validation.py
?? research (5).zip
?? research/68_BDB5_OFFLINE_HARNESS_REPORT.md
?? scripts/bdb5_dry_run.py
?? tests/test_bdb5/test_cli.py
?? tests/test_bdb5/test_synthetic_scoring.py
?? tests/test_bdb5/test_validation_and_engine.py
```

After creating this report, the final status contained **554 entries**, SHA-256 `0795f81e9ea4e157e0ad3ef2b6672944f60bfcc137c3f666b0f8ab8228c4e800`: the 538 baseline entries, the 15 additional untracked entries above, and `?? research/67_M4B3_FOLLOWUP_HARDENING_REPORT.md`. No per-file content hashes were captured for the already-dirty source/test files before editing, so this report does not claim that their preexisting bytes were preserved unchanged. No graphify operation was run in this pass.

## Remaining limitations

- Real reconciliation remains unavailable until a genuinely trusted verifier is implemented and reviewed.
- POSIX replacement/fork semantics were not executed on this Windows host.
- Response memory is bounded within BLACKBOX, not end-to-end for arbitrary transport implementations.
- Private Python seams do not resist arbitrary malicious code in the same interpreter.
- Schema-v2 databases have no migration path and are refused.
- Advisory file locks and metadata checks are not a defense against unrestricted filesystem or operating-system control.

FOLLOWUP_HARDENING_COMPLETE — REGRESSION_TESTS_PASSED — LIVE_DISABLED
