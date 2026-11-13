# M4B.3 Audit Remediation Report

**Date:** 2026-11-08
**Outcome:** `M4B3_REMEDIATION_COMPLETE — REGRESSION_TESTS_PASSED — LIVE_DISABLED`

## Executive outcome

The M4B.3 dispatch and completion paths now require a committed ledger event and a session-bound capability or response receipt. The dispatcher independently replays the actual SQLite ledger immediately before transport, holds a per-evaluation lock through the request, and sends a snapshot of the validated request. Completion can be recorded only from a complete dispatcher receipt, and replay checks that the stored output is consistent with the exact response bytes.

The new regression cases cover the reproduced permit, stale authorization, false completion, duplicate attempt ID, approval, failure proof, response size, fingerprint, and lock ownership defects. All 24 targeted new cases passed. The full M4B.3 suite passed 104 tests, and the safe engine suite passed 53 tests.

Real experiment initialization and live inference remain disabled. No trusted approval verifier exists, and Documents 56 and 57 still state `DRAFT — NOT APPROVED`.

## Findings and corrections

| Finding | Correction | Verification |
|---|---|---|
| **B1 — Forged dispatch permit** | Removed reliance on an importable issuer. `DispatchPermit` can only be issued by a ledger session after the `DISPATCH_INTENT` commit. `send_prepared()` asks that ledger to validate the committed event, run/evaluation/attempt IDs, request/body/config hashes, current state, and later closure events. It uses an independent read-only SQLite connection. | Tests reject the old issuer/forged object, invalid or mismatched event/attempt/request/body/config, missing dispatch history, and prove the independent receiver sees the committed marker before one valid request. |
| **B1 — Concurrent use and reconciliation race** | A per-evaluation `RLock` coordinates validation, one-time consumption, reconciliation, and transport entry. The run lock still excludes another process. The SQLite read transaction closes before HTTP; no write transaction spans the request. | Two simultaneous consumers produce one request. Dispatch/reconciliation and stale-permit tests show closure prevents later transport. |
| **B2 — False completion** | `record_completed()` accepts one opaque `ValidatedCompletion`, not raw bytes plus a caller dictionary and Boolean. The runner parses and validates the exact dispatcher receipt bytes. Replay checks the receipt’s base64, raw hash, full-body flag, dispatch/evaluation/attempt/request identity, completion event ID, validation metadata, and derivation digest; it also checks parsed output text against the raw body. | The previous fabricated `b"not a provider response"` attack raises before appending `COMPLETED`; the state remains unresolved/unknown. Receipt mismatch, cross-session, reuse, and rehashed output-disagreement tests fail closed. |
| **B3 — Stale permit after accepted-missing** | Dispatch validation rejects missing-closed or terminal states, and reconciliation shares the evaluation lock with transport. A complete response receipt also blocks reconciliation until the terminal event is recorded. | A permit saved before `ACCEPTED_UNKNOWN_MISSING` sends zero requests; a new permit is also refused. |
| **B4 — Duplicate attempt IDs** | Schema validation requires `one_attempt_id_per_run`; replay independently tracks every `IN_FLIGHT` attempt ID. Existing ledgers are never repaired by recreating the index. | Dropping the index blocks startup without changing history. A separate rehashed duplicate-attempt history is rejected by replay. |
| **B5 — Approval authenticity** | Approval validation requires an explicitly supplied verifier that returns the literal Boolean `True`; arbitrary signature text is insufficient. No trusted verifier is configured. `initialize_experiment()` always blocks, the CLI has no test-verifier argument, and `LIVE_EXECUTION_ENABLED` remains a hard-coded `False` with no environment override. | Tests reject missing/false/non-Boolean verifiers and unapproved draft status; isolated fixtures use a verifier defined in test code. CLI initialization and `--run-live` remain blocked, including with an environment variable set. |
| **B6 — Self-asserted failure flags** | Removed `no_dispatch_proof` and `definitive_provider_failure`. `record_failed()` requires session-bound typed evidence. Local failure evidence is available only for matching `IN_FLIGHT` state with no dispatch. A post-dispatch failure requires a typed record tied to an explicit `CONFIRMED_FAILED` reconciliation event. | Boolean-argument attempts fail; a dispatched attempt cannot obtain local failure evidence. Tests cover the explicit reconciliation path and ensure a terminal failure does not cause another send. |
| **B7 — Unbounded response body** | The dispatcher enforces a fixed **1 MiB** response limit. It checks `Content-Length`, then enforces the same cap while streaming. It retains only a bounded prefix, reports observed bytes and the prefix hash, closes the response, and records oversized or interrupted responses as unknown without retry. The cap is transport safety and does not alter generation settings. | Seven stream cases cover exact limit, declared oversize, too-small length, missing length, one large chunk, multiple chunks, and interrupted stream. Each ambiguous case remains unknown and is not resent. |
| **B8 — Test code in runtime fingerprint** | Runtime implementation hashes remain in `fingerprint_inputs`. Test source hashes are retained under `audit_metadata.test_source_sha256`, which does not affect the inference fingerprint. | Changing test provenance metadata leaves the fingerprint unchanged; changing a runtime source hash changes it. |
| **B9 — Unverified held lock** | `RunLock` records active acquired instances and verifies the descriptor, active registration, and resolved expected path. `Ledger.initialize()` requires the exact `RunLock` type and validates ownership before using a supplied lock. | Unacquired, spoofed-subclass, and wrong-path lock cases are rejected before the database is created. |

## Regression and integration tests

The new tests use temporary ledgers/results and an independent HTTP receiver bound only to `127.0.0.1`. The receiver writes and fsyncs its own JSONL request receipt. Before transport, a separate SQLite connection verifies the `IN_FLIGHT` and exact committed `DISPATCH_INTENT`; the checkpoint also confirms the permit is consumed. Valid dispatch produces one receiver entry. Forged, mismatched, removed-history, stale, and reused permits produce zero additional entries.

The 24 targeted new regression cases passed, including the parameterized size cases. Existing complete-invalid-response tests continue to show that a complete schema-invalid response becomes `COMPLETED` with `valid: false`, consumes its evaluation, and is never resent.

## Test results

- **Stage A — new regression cases:** `24 passed, 62 deselected in 38.16s`.
- **Stage B — M4B.3 ledger and harness:** `104 passed in 210.81s`.
- **Stage C — engine suite:** `53 passed, 1 warning in 23.85s`. The warning is Starlette’s deprecation notice for using `httpx` with `TestClient`; tests passed.
- **Stage D — static checks:** Python compilation passed. `git diff --check` reported no whitespace errors; Git printed line-ending conversion warnings for the pre-existing working-copy format. A separate trailing-whitespace scan of all authorized source and test files passed. Searches found only the guarded M4B.3 dispatch call and the existing non-M4B.3 generic provider adapter.

`tests/test_engine.py` was inspected before Stage C. It uses temporary Git repositories and SQLite databases, `TestClient`, and mocked provider behavior. Its Ollama/Gemini adapter cases monkeypatch HTTP calls. No external service, Docker, repair workflow, or repair fixture execution was involved.

## Security and trust-boundary limits

Python private members and opaque objects are API controls, not a cryptographic boundary against hostile code already executing in the same interpreter. Such code can inspect or mutate process memory. The enforcement here is that the official M4B.3 API requires a registered ledger-session capability, verifies durable SQLite history, binds completion to exact dispatcher bytes, and synchronizes dispatch with reconciliation.

The ledger’s event chain and SQLite constraints detect malformed or inconsistent history; they do not make the database tamper-proof against an actor with unrestricted filesystem and database access who can rewrite and rehash the entire store. Human reconciliation records reviewer identity, evidence references, rationale, and approval, but this repository has no independent cryptographic verifier for that human action.

No trusted approval verifier was available or invented. The real experiment therefore remains blocked, as required. Documents 56 and 57 remain drafts, and the original pinned preregistration was not edited. Graphify output was not rebuilt because those files are outside the user-authorized edit list.

## Plain-language explanation

- An importable Python token is just an object in the running program. Anyone who can import it can try to copy or misuse it, so it cannot prove that a database write happened.
- Before sending, the dispatcher reads and validates the actual ledger. That proves the exact attempt and request were durably marked for dispatch.
- Reconciliation can close an uncertain attempt. The same lock makes the choice atomic: either dispatch enters first, or closure happens first and the old permit is rejected.
- A response receipt holds the exact bytes the dispatcher finished reading. The runner derives the result from those bytes, and replay checks that the saved output and validation record still correspond to them.
- A Boolean such as `definitive_provider_failure=True` is only a caller’s claim. Typed evidence must come from the pre-dispatch state or an explicit reconciliation event.
- A streaming byte cap limits how much response data can be retained in memory or in the ledger. An oversized response is uncertain because the request already entered transport, so the runner never retries it.
- A complete but schema-invalid response still came back from the provider. Its evaluation is consumed and recorded as completed with `valid: false`; sending again would spend the attempt twice.
- Real initialization stays blocked because the required documents are not approved and no trusted approval verifier is configured. A typed signature field or environment variable cannot replace that missing approval mechanism.

## Files changed

The only intended workspace edits are the five authorized code/test paths and this report:

- `blackbox/m4b3_ledger.py`
- `blackbox/providers.py`
- `scripts/evaluate_m4b3.py`
- `tests/test_m4b3_ledger.py`
- `tests/test_m4b3_harness.py`
- `research/64_M4B3_AUDIT_REMEDIATION_REPORT.md` (new)

The pre-edit Git snapshot had 452 status entries. Among the authorized targets, `blackbox/providers.py` was already modified, the ledger/runner/two test files were already untracked, and this report did not exist. The final `git status --short` has 457 entries, a net increase of five. The report accounts for one new path. The other four additional status entries are outside the authorized paths; they were left untouched and are not attributed from status output alone. The authorized target categories are unchanged except for this new report. No byte-for-byte preservation claim is made for already-dirty files.

No commit or push was made. No live Ollama/model request, external AI API call, Docker command, repair workflow, M4B.3 fixture execution, or real experiment initialization occurred.
