"""Durable, event-sourced storage for the offline M4B.3 evaluation harness.

This module does not create or call an inference provider.  Live execution is
deliberately disabled by the runner for this milestone.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import quote


SCHEMA_VERSION = 3
COMPLETION_VALIDATOR_VERSION = 1
ZERO_HASH = "0" * 64
MAX_EVALUATIONS = 24
MAX_RESPONSE_BYTES = 1024 * 1024
EVENT_TYPES = frozenset({
    "RUN_INITIALIZED", "EVALUATION_PLANNED", "IN_FLIGHT", "RECONCILIATION",
    "DISPATCH_INTENT", "COMPLETED", "FAILED", "UNKNOWN_OUTCOME", "EXPORT_WRITTEN",
})


class LedgerError(RuntimeError):
    """Base error for ledger validation or operation failures."""


class LedgerBlocked(LedgerError):
    """The requested operation cannot safely proceed from the durable history."""


class CommitAmbiguous(LedgerError):
    """SQLite did not acknowledge a commit; its outcome must be checked afresh."""

    def __init__(self, message: str, event_id: str | None = None):
        super().__init__(message)
        self.event_id = event_id


class LockUnavailable(LedgerBlocked):
    """Another process currently owns the stable experiment lock."""


_RUN_LOCK_REGISTRY_GUARD = threading.Lock()
_ACTIVE_RUN_LOCKS: dict[int, tuple[int, Path, int, tuple[int, int]]] = {}


def _absolute_path(path: str | Path) -> Path:
    """Normalize a path lexically without following a replaceable symlink."""
    return Path(os.path.abspath(os.fspath(path)))


def _file_identity_from_stat(value: os.stat_result) -> tuple[int, int]:
    return int(value.st_dev), int(value.st_ino)


def canonical_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes; non-finite numbers are rejected."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def evaluation_id(revision: str, case_id: str, arm: str) -> str:
    """Stable identity for one frozen revision/case/arm tuple."""
    raw = canonical_bytes({"revision": revision, "case_id": case_id, "arm": arm})
    return "eval-" + sha256_hex(raw)


def request_spec_hash(plan: Mapping[str, Any]) -> str:
    fields = {k: plan[k] for k in ("case", "arm", "revision", "evidence_hash", "prompt", "schema", "context")}
    return sha256_hex(canonical_bytes(fields))


def manifest_fingerprint(manifest: Mapping[str, Any]) -> str:
    """Hash execution-defining inputs while keeping audit metadata non-blocking."""
    inputs = manifest.get("fingerprint_inputs")
    return sha256_hex(canonical_bytes(inputs if isinstance(inputs, Mapping) else manifest))


class RunLock:
    """Stable OS-enforced single-runner lock; the lock pathname is never removed."""

    def __init__(self, path: str | Path):
        self.path = _absolute_path(path)
        self.fd: int | None = None
        self._locked = False
        self.owner_pid: int | None = None
        self.file_identity: tuple[int, int] | None = None

    @property
    def identity_text(self) -> str | None:
        if self.file_identity is None:
            return None
        return f"{self.file_identity[0]}:{self.file_identity[1]}"

    def acquire(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        self.fd = os.open(self.path, flags, 0o600)
        os.set_inheritable(self.fd, False)
        self.owner_pid = os.getpid()
        self.file_identity = _file_identity_from_stat(os.fstat(self.fd))
        if os.fstat(self.fd).st_size == 0:
            os.lseek(self.fd, 0, os.SEEK_SET)
            os.write(self.fd, b"\0")
            os.fsync(self.fd)
        os.lseek(self.fd, 0, os.SEEK_SET)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            os.close(self.fd)
            self.fd = None
            raise LockUnavailable(f"M4B.3 run lock is held: {self.path}") from exc
        self._locked = True
        try:
            if _file_identity_from_stat(os.stat(self.path)) != self.file_identity:
                raise LockUnavailable(f"M4B.3 lock pathname changed during acquisition: {self.path}")
        except OSError as exc:
            self.release()
            raise LockUnavailable(f"M4B.3 lock pathname cannot be verified: {self.path}") from exc
        except LockUnavailable:
            self.release()
            raise
        with _RUN_LOCK_REGISTRY_GUARD:
            _ACTIVE_RUN_LOCKS[id(self)] = (self.fd, self.path, self.owner_pid, self.file_identity)
        return self

    def owns(self, path: str | Path) -> bool:
        """Return whether this instance still owns the lock for exactly this path."""
        if (self.fd is None or not self._locked or self.owner_pid != os.getpid()
                or self.file_identity is None or self.path != _absolute_path(path)):
            return False
        with _RUN_LOCK_REGISTRY_GUARD:
            if _ACTIVE_RUN_LOCKS.get(id(self)) != (
                    self.fd, self.path, self.owner_pid, self.file_identity):
                return False
        try:
            descriptor_identity = _file_identity_from_stat(os.fstat(self.fd))
            pathname_identity = _file_identity_from_stat(os.stat(self.path))
        except OSError:
            return False
        return descriptor_identity == self.file_identity and pathname_identity == self.file_identity

    def release(self) -> None:
        if self.fd is None:
            return
        with _RUN_LOCK_REGISTRY_GUARD:
            _ACTIVE_RUN_LOCKS.pop(id(self), None)
        try:
            # flock state is associated with the inherited open-file description on
            # POSIX. A forked child must close only its descriptor copy, never unlock it.
            if self._locked and self.owner_pid == os.getpid():
                os.lseek(self.fd, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None
            self._locked = False
            self.owner_pid = None
            self.file_identity = None

    def __enter__(self) -> "RunLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


@dataclass
class EvaluationState:
    evaluation_id: str
    case_id: str
    arm: str
    ordinal: int
    state: str = "PLANNED"
    attempt_id: str | None = None
    request_hash: str | None = None
    request_payload_sha256: str | None = None
    config_sha256: str | None = None
    dispatch_event_id: str | None = None
    result: dict[str, Any] | None = None
    terminal_event_id: str | None = None
    missing_closed: bool = False
    pending_reconciliation: str | None = None
    pending_reconciliation_event_id: str | None = None


@dataclass(frozen=True)
class Replay:
    states: Mapping[str, EvaluationState]
    events: tuple[Mapping[str, Any], ...]
    last_seq: int
    last_hash: str


class _PermitUse:
    def __init__(self):
        self.lock = threading.Lock()
        self.consumed = False


@dataclass(frozen=True, init=False)
class DispatchPermit:
    """Ledger-session capability, bound to one committed dispatch and request."""

    run_id: str
    evaluation_id: str
    attempt_id: str
    request_hash: str
    dispatch_event_id: str
    _ledger: Any = field(compare=False, repr=False)
    _use: _PermitUse = field(compare=False, repr=False)

    def __init__(self, *args, **kwargs):
        raise LedgerBlocked("dispatch permits are issued only by an open ledger session")

    @classmethod
    def _issue(cls, ledger: Any, run_id: str, evaluation_id: str, attempt_id: str,
               request_hash: str, dispatch_event_id: str) -> "DispatchPermit":
        permit = object.__new__(cls)
        for name, value in {
            "run_id": run_id, "evaluation_id": evaluation_id, "attempt_id": attempt_id,
            "request_hash": request_hash, "dispatch_event_id": dispatch_event_id,
            "_ledger": ledger, "_use": _PermitUse(),
        }.items():
            object.__setattr__(permit, name, value)
        return permit

    def _consume_once(self) -> None:
        with self._use.lock:
            if self._use.consumed:
                raise LedgerBlocked("dispatch permit has already been consumed")
            self._use.consumed = True

    @property
    def consumed(self) -> bool:
        with self._use.lock:
            return self._use.consumed


@dataclass(frozen=True, init=False)
class DispatchResponseReceipt:
    """Opaque evidence that this ledger's dispatcher read one complete response."""

    receipt_id: str
    run_id: str
    evaluation_id: str
    attempt_id: str
    dispatch_event_id: str
    request_hash: str
    status_code: int
    raw_body: bytes
    raw_body_sha256: str
    safe_headers: Mapping[str, str]
    _ledger: Any = field(compare=False, repr=False)

    def __init__(self, *args, **kwargs):
        raise LedgerBlocked("response receipts are issued only by the ledger dispatcher boundary")

    @classmethod
    def _issue(cls, ledger: Any, permit: DispatchPermit, status_code: int,
               raw_body: bytes, safe_headers: Mapping[str, str]) -> "DispatchResponseReceipt":
        receipt = object.__new__(cls)
        values = {
            "receipt_id": str(uuid.uuid4()), "run_id": permit.run_id,
            "evaluation_id": permit.evaluation_id, "attempt_id": permit.attempt_id,
            "dispatch_event_id": permit.dispatch_event_id, "request_hash": permit.request_hash,
            "status_code": int(status_code), "raw_body": bytes(raw_body),
            "raw_body_sha256": sha256_hex(raw_body), "safe_headers": MappingProxyType(dict(safe_headers)),
            "_ledger": ledger,
        }
        for name, value in values.items():
            object.__setattr__(receipt, name, value)
        return receipt


@dataclass(frozen=True, init=False)
class ValidatedCompletion:
    """Opaque normalized completion derived from one registered response receipt."""

    response_receipt: DispatchResponseReceipt
    result_record: Mapping[str, Any]
    valid: bool
    validation: Mapping[str, Any]
    response_metadata: Mapping[str, Any]
    result_derivation_sha256: str
    _ledger: Any = field(compare=False, repr=False)

    def __init__(self, *args, **kwargs):
        raise LedgerBlocked("completion records are created by the trusted response-processing path")

    @classmethod
    def _issue(cls, ledger: Any, receipt: DispatchResponseReceipt,
               result_record: Mapping[str, Any], valid: bool,
               validation: Mapping[str, Any], response_metadata: Mapping[str, Any],
               derivation_hash: str) -> "ValidatedCompletion":
        completion = object.__new__(cls)
        values = {
            "response_receipt": receipt, "result_record": dict(result_record),
            "valid": bool(valid), "validation": dict(validation),
            "response_metadata": dict(response_metadata),
            "result_derivation_sha256": derivation_hash, "_ledger": ledger,
        }
        for name, value in values.items():
            object.__setattr__(completion, name, value)
        return completion


@dataclass(frozen=True, init=False)
class FailureEvidence:
    """Session-bound proof of a local or explicitly reconciled terminal failure."""

    evaluation_id: str
    attempt_id: str
    error_type: str
    error: str
    failure_kind: str
    reconciliation_event_id: str | None
    _ledger: Any = field(compare=False, repr=False)

    def __init__(self, *args, **kwargs):
        raise LedgerBlocked("failure evidence is issued only by the execution/reconciliation boundary")

    @classmethod
    def _issue(cls, ledger: Any, evaluation: str, attempt: str,
               error_type: str, error: str, *, failure_kind: str = "LOCAL_PRE_DISPATCH",
               reconciliation_event_id: str | None = None) -> "FailureEvidence":
        evidence = object.__new__(cls)
        for name, value in {
            "evaluation_id": evaluation, "attempt_id": attempt,
            "error_type": str(error_type), "error": str(error)[:500],
            "failure_kind": failure_kind, "reconciliation_event_id": reconciliation_event_id,
            "_ledger": ledger,
        }.items():
            object.__setattr__(evidence, name, value)
        return evidence


def _completion_derivation_sha256(
    receipt: DispatchResponseReceipt, result_record: Mapping[str, Any], valid: bool,
    validation: Mapping[str, Any], response_metadata: Mapping[str, Any],
) -> str:
    material = {
        "receipt_id": receipt.receipt_id,
        "dispatch_event_id": receipt.dispatch_event_id,
        "evaluation_id": receipt.evaluation_id,
        "attempt_id": receipt.attempt_id,
        "request_hash": receipt.request_hash,
        "raw_body_sha256": receipt.raw_body_sha256,
        "result_record": dict(result_record),
        "valid": bool(valid),
        "validation": dict(validation),
        "response_metadata": dict(response_metadata),
    }
    return sha256_hex(canonical_bytes(material))


_DERIVED_COMPLETION_FIELDS = frozenset({
    "raw_output", "raw_output_text", "validated_output", "valid", "error_type", "error",
    "usage", "done_reason",
})


def _derive_completion_from_response(
    raw_body: bytes, plan: Mapping[str, Any], base_record: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse and validate a complete response against its immutable planned schema."""
    record = {key: value for key, value in base_record.items()
              if key not in _DERIVED_COMPLETION_FIELDS}
    outer: dict[str, Any] = {}
    raw_output: Any = None
    content: Any = None
    usage: dict[str, Any] = {}
    validation: dict[str, Any]
    try:
        decoded_outer = json.loads(raw_body.decode("utf-8"))
        if not isinstance(decoded_outer, dict):
            raise ValueError("provider response envelope must be a JSON object")
        outer = decoded_outer
        message = outer.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        usage = {
            "input_tokens": outer.get("prompt_eval_count"),
            "output_tokens": outer.get("eval_count"),
            "load_duration_ns": outer.get("load_duration"),
            "eval_duration_ns": outer.get("eval_duration"),
            "estimated_cost": None,
        }
        if outer.get("done_reason") == "length":
            raise ValueError("model response reached done_reason=length")
        if not isinstance(content, str) or not content:
            raise ValueError("provider returned empty model content")
        raw_output = json.loads(content)
        if not isinstance(raw_output, dict):
            raise ValueError("model output must be a JSON object")
        snapshot = plan.get("snapshot")
        if not isinstance(snapshot, dict):
            raise LedgerBlocked("immutable evaluation plan has no schema snapshot")
        if plan.get("schema") == "current":
            from blackbox.investigator import validate_model_output
            findings, _dropped = validate_model_output(raw_output, snapshot)
            validated_output = findings.model_dump()
        elif plan.get("schema") == "layered":
            from scripts.m4b3_layered_schema import validate_layered
            validated_output = validate_layered(raw_output, snapshot["evidence"]).model_dump()
        else:
            raise LedgerBlocked("immutable evaluation plan selects an unknown completion schema")
        record.update({"raw_output": raw_output, "validated_output": validated_output,
                       "valid": True})
        validation = {"valid": True}
    except LedgerBlocked:
        raise
    except Exception as exc:
        if raw_output is not None:
            record["raw_output"] = raw_output
        error_type, error = type(exc).__name__, str(exc)[:300]
        record.update({"valid": False, "error_type": error_type, "error": error})
        validation = {"valid": False, "error_type": error_type, "error": error}
    record["raw_output_text"] = (
        content if isinstance(content, str) else raw_body.decode("utf-8", "replace")
    )
    record["usage"] = usage
    record["done_reason"] = outer.get("done_reason") if isinstance(outer, dict) else None
    return record, validation


SCHEMA_STATEMENTS = (
    """CREATE TABLE run_meta (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        run_id TEXT NOT NULL UNIQUE,
        schema_version INTEGER NOT NULL,
        lock_identity TEXT NOT NULL,
        run_fingerprint_sha256 TEXT NOT NULL CHECK (length(run_fingerprint_sha256) = 64),
        approved_protocol_sha256 TEXT NOT NULL CHECK (length(approved_protocol_sha256) = 64),
        manifest_json TEXT NOT NULL,
        initial_results_sha256 TEXT NOT NULL CHECK (length(initial_results_sha256) = 64),
        initialized_utc TEXT NOT NULL,
        initial_event_hash TEXT NOT NULL CHECK (length(initial_event_hash) = 64)
    )""",
    """CREATE TABLE planned_evaluations (
        run_id TEXT NOT NULL REFERENCES run_meta(run_id),
        evaluation_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 24),
        case_id TEXT NOT NULL,
        arm TEXT NOT NULL CHECK (arm IN ('A','B','C','D')),
        prompt_id TEXT NOT NULL,
        schema_id TEXT NOT NULL,
        request_spec_sha256 TEXT NOT NULL CHECK (length(request_spec_sha256) = 64),
        plan_json TEXT NOT NULL,
        PRIMARY KEY (run_id, evaluation_id),
        UNIQUE (run_id, case_id, arm),
        UNIQUE (run_id, ordinal)
    )""",
    """CREATE TABLE events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL UNIQUE,
        run_id TEXT NOT NULL REFERENCES run_meta(run_id),
        evaluation_id TEXT,
        attempt_id TEXT,
        event_type TEXT NOT NULL CHECK (event_type IN (
            'RUN_INITIALIZED','EVALUATION_PLANNED','IN_FLIGHT','RECONCILIATION',
            'DISPATCH_INTENT','COMPLETED','FAILED','UNKNOWN_OUTCOME','EXPORT_WRITTEN'
        )),
        occurred_utc TEXT NOT NULL CHECK (substr(occurred_utc, -1, 1) = 'Z'),
        payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
        prev_event_hash TEXT NOT NULL CHECK (length(prev_event_hash) = 64),
        event_hash TEXT NOT NULL CHECK (length(event_hash) = 64),
        FOREIGN KEY (run_id, evaluation_id) REFERENCES planned_evaluations(run_id, evaluation_id),
        CHECK (
          (event_type IN ('RUN_INITIALIZED','EXPORT_WRITTEN') AND evaluation_id IS NULL AND attempt_id IS NULL)
          OR (event_type = 'EVALUATION_PLANNED' AND evaluation_id IS NOT NULL AND attempt_id IS NULL)
          OR (event_type NOT IN ('RUN_INITIALIZED','EXPORT_WRITTEN','EVALUATION_PLANNED')
              AND evaluation_id IS NOT NULL AND attempt_id IS NOT NULL)
        )
    )""",
    "CREATE UNIQUE INDEX one_attempt_start_per_evaluation ON events(run_id,evaluation_id) WHERE event_type='IN_FLIGHT'",
    "CREATE UNIQUE INDEX one_attempt_id_per_run ON events(run_id,attempt_id) WHERE event_type='IN_FLIGHT'",
    "CREATE UNIQUE INDEX one_dispatch_intent_per_evaluation ON events(run_id,evaluation_id) WHERE event_type='DISPATCH_INTENT'",
    "CREATE UNIQUE INDEX one_completion_per_evaluation ON events(run_id,evaluation_id) WHERE event_type='COMPLETED'",
    "CREATE UNIQUE INDEX one_failure_per_evaluation ON events(run_id,evaluation_id) WHERE event_type='FAILED'",
    "CREATE UNIQUE INDEX one_unknown_marker_per_evaluation ON events(run_id,evaluation_id) WHERE event_type='UNKNOWN_OUTCOME'",
    "CREATE UNIQUE INDEX one_plan_event_per_evaluation ON events(run_id,evaluation_id) WHERE event_type='EVALUATION_PLANNED'",
    "CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END",
    "CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END",
    "CREATE TRIGGER plan_no_update BEFORE UPDATE ON planned_evaluations BEGIN SELECT RAISE(ABORT,'registered plan is immutable'); END",
    "CREATE TRIGGER plan_no_delete BEFORE DELETE ON planned_evaluations BEGIN SELECT RAISE(ABORT,'registered plan is immutable'); END",
    "CREATE TRIGGER run_meta_no_update BEFORE UPDATE ON run_meta BEGIN SELECT RAISE(ABORT,'run manifest is immutable'); END",
    "CREATE TRIGGER run_meta_no_delete BEFORE DELETE ON run_meta BEGIN SELECT RAISE(ABORT,'run manifest is immutable'); END",
)


def _event_hash(row: Mapping[str, Any]) -> str:
    columns = {key: row[key] for key in (
        "seq", "event_id", "run_id", "evaluation_id", "attempt_id", "event_type",
        "occurred_utc", "payload_json", "payload_sha256", "prev_event_hash",
    )}
    return sha256_hex(canonical_bytes(columns))


def _prepare_event(
    *, seq: int, event_id: str, run_id: str, evaluation_id: str | None,
    attempt_id: str | None, event_type: str, occurred_utc: str,
    payload: Mapping[str, Any], prev_event_hash: str,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise LedgerError(f"unsupported event type: {event_type}")
    payload_json = canonical_bytes(dict(payload)).decode("utf-8")
    row = {
        "seq": seq, "event_id": event_id, "run_id": run_id,
        "evaluation_id": evaluation_id, "attempt_id": attempt_id,
        "event_type": event_type, "occurred_utc": occurred_utc,
        "payload_json": payload_json, "payload_sha256": sha256_hex(payload_json),
        "prev_event_hash": prev_event_hash,
    }
    row["event_hash"] = _event_hash(row)
    return row


def _insert_event(conn: sqlite3.Connection, row: Mapping[str, Any]) -> None:
    conn.execute(
        """INSERT INTO events(seq,event_id,run_id,evaluation_id,attempt_id,event_type,
           occurred_utc,payload_json,payload_sha256,prev_event_hash,event_hash)
           VALUES(:seq,:event_id,:run_id,:evaluation_id,:attempt_id,:event_type,
           :occurred_utc,:payload_json,:payload_sha256,:prev_event_hash,:event_hash)""",
        dict(row),
    )


def _configure(conn: sqlite3.Connection, *, set_wal: bool = True) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    if set_wal:
        mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(mode).lower() != "wal":
            raise LedgerBlocked(f"SQLite refused WAL mode (got {mode!r})")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA busy_timeout=5000")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise LedgerBlocked("SQLite foreign keys are not enabled")
    if conn.execute("PRAGMA synchronous").fetchone()[0] != 2:
        raise LedgerBlocked("SQLite synchronous=FULL is not active")


def _sqlite_rw_uri(path: Path) -> str:
    # SQLite URI mode=rw is essential: a missing database must not be recreated.
    normalized = path.resolve().as_posix()
    return "file:" + quote(normalized, safe="/:\\") + "?mode=rw"


def _sqlite_ro_uri(path: Path) -> str:
    normalized = path.resolve().as_posix()
    return "file:" + quote(normalized, safe="/:\\") + "?mode=ro"


def _validate_wal_sidecar(path: Path) -> None:
    wal = Path(str(path) + "-wal")
    if wal.exists() and wal.stat().st_size:
        with wal.open("rb") as stream:
            magic = stream.read(4)
        if magic not in (b"7\x7f\x06\x82", b"7\x7f\x06\x83"):
            raise LedgerBlocked("SQLite WAL sidecar has an invalid header; preserving all database artifacts")


class Ledger:
    """One locked SQLite writer connection and a canonical append-only event stream."""

    def __init__(
        self, conn: sqlite3.Connection, path: Path, lock: RunLock,
        fault_hook: Callable[[str], None] | None = None,
    ):
        self.conn = conn
        self.path = path.resolve()
        self.lock = lock
        self.fault_hook = fault_hook
        self._owner_thread = threading.get_ident()
        self._owner_pid = os.getpid()
        self._closed = False
        self._evaluation_locks: dict[str, threading.RLock] = {}
        self._evaluation_locks_guard = threading.Lock()
        self._capability_guard = threading.Lock()
        self._issued_permits: dict[str, DispatchPermit] = {}
        self._issued_failures: dict[int, FailureEvidence] = {}
        self._response_receipts: dict[str, DispatchResponseReceipt] = {}
        self._consumed_receipts: set[str] = set()
        self._active_dispatches: set[str] = set()
        self._reconciliation_verifier: Callable[[Mapping[str, Any]], Any] | None = None
        self._reconciliation_verifier_id: str | None = None
        self.run_meta = dict(conn.execute("SELECT * FROM run_meta WHERE singleton=1").fetchone())
        self.run_id = self.run_meta["run_id"]

    @classmethod
    def initialize(
        cls,
        path: str | Path,
        *,
        plan_rows: Iterable[Mapping[str, Any]],
        manifest: Mapping[str, Any],
        approved_protocol_sha256: str,
        initial_results_sha256: str,
        run_id: str | None = None,
        lock_path: str | Path | None = None,
        fault_hook: Callable[[str], None] | None = None,
        held_lock: RunLock | None = None,
    ) -> None:
        db_path = Path(path).resolve()
        lock_path = _absolute_path(lock_path) if lock_path else db_path.with_suffix(".lock")
        rows = [dict(row) for row in plan_rows]
        if len(rows) != MAX_EVALUATIONS:
            raise LedgerBlocked(f"the frozen plan must contain exactly {MAX_EVALUATIONS} evaluations")
        if len({r.get("evaluation_id") for r in rows}) != MAX_EVALUATIONS:
            raise LedgerBlocked("duplicate evaluation IDs in plan")
        if len({(r.get("case_id"), r.get("arm")) for r in rows}) != MAX_EVALUATIONS:
            raise LedgerBlocked("duplicate case/arm pair in plan")
        for ordinal, row in enumerate(rows, 1):
            if row.get("ordinal") != ordinal:
                raise LedgerBlocked("plan order/ordinal mismatch")
            if not row.get("evaluation_id") or not row.get("case_id"):
                raise LedgerBlocked("plan row is missing stable identity")
            if row.get("arm") not in {"A", "B", "C", "D"}:
                raise LedgerBlocked("plan contains an unregistered arm")
            for key in ("request_spec_sha256",):
                if not _is_hash(row.get(key)):
                    raise LedgerBlocked(f"plan row has invalid {key}")
        if not _is_hash(approved_protocol_sha256) or not _is_hash(initial_results_sha256):
            raise LedgerBlocked("protocol/template fingerprints must be SHA-256 hex digests")
        manifest_obj = dict(manifest)
        fingerprint_inputs = manifest_obj.get("fingerprint_inputs")
        if not isinstance(fingerprint_inputs, Mapping):
            raise LedgerBlocked("run manifest is missing immutable fingerprint inputs")
        case_ids = fingerprint_inputs.get("case_ids")
        arm_order = fingerprint_inputs.get("arm_order_by_case")
        if (not isinstance(case_ids, list) or len(case_ids) != 6
                or len(set(case_ids)) != 6 or not isinstance(arm_order, Mapping)
                or set(arm_order) != set(case_ids)):
            raise LedgerBlocked("manifest must register exactly six unique cases and their arm order")
        expected_pairs: list[tuple[str, str]] = []
        for case_id in case_ids:
            arms = arm_order[case_id]
            if not isinstance(arms, list) or len(arms) != 4 or set(arms) != {"A", "B", "C", "D"}:
                raise LedgerBlocked("each registered case must contain each of the four arms exactly once")
            expected_pairs.extend((case_id, arm) for arm in arms)
        if [(row["case_id"], row["arm"]) for row in rows] != expected_pairs:
            raise LedgerBlocked("plan rows differ from the manifest's exact ordered six-by-four plan")
        revision = manifest_obj.get("revision", fingerprint_inputs.get("pinned_commit"))
        if not isinstance(revision, str) or not revision:
            raise LedgerBlocked("run manifest is missing its pinned revision")
        for row in rows:
            if row["evaluation_id"] != evaluation_id(revision, row["case_id"], row["arm"]):
                raise LedgerBlocked("plan row evaluation ID is not stable for its revision/case/arm identity")
        if manifest_obj.get("approved_protocol_sha256") != approved_protocol_sha256:
            raise LedgerBlocked("approved protocol fingerprint does not match the immutable manifest")
        manifest_json = canonical_bytes(manifest_obj).decode("utf-8")
        manifest_hash = manifest_fingerprint(manifest_obj)
        run_id = run_id or str(uuid.uuid4())
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if held_lock is not None and (
                type(held_lock) is not RunLock or not RunLock.owns(held_lock, lock_path)):
            raise LedgerBlocked("held_lock must be an acquired lock for the ledger's expected lock path")
        lock_context = contextlib.nullcontext(held_lock) if held_lock is not None else RunLock(lock_path)
        with lock_context as acquired_lock:
            if type(acquired_lock) is not RunLock or not acquired_lock.owns(lock_path):
                raise LedgerBlocked("initialization requires a verifiable owned run lock")
            lock_identity = acquired_lock.identity_text
            if not lock_identity:
                raise LedgerBlocked("run lock file identity is unavailable")
            sidecars = [Path(str(db_path) + suffix) for suffix in ("-wal", "-shm")]
            if db_path.exists() or any(p.exists() for p in sidecars):
                raise LedgerBlocked("ledger path or orphan SQLite sidecar already exists; preserve and inspect it")
            conn = sqlite3.connect(db_path, timeout=5, isolation_level=None, check_same_thread=True)
            conn.row_factory = sqlite3.Row
            try:
                _configure(conn)
                conn.execute("BEGIN IMMEDIATE")
                try:
                    for statement in SCHEMA_STATEMENTS:
                        conn.execute(statement)
                    initialized_utc = utc_now()
                    initialized_event_id = str(uuid.uuid4())
                    initialized_payload = {
                        "run_id": run_id, "schema_version": SCHEMA_VERSION,
                        "lock_identity": lock_identity,
                        "run_fingerprint_sha256": manifest_hash,
                        "approved_protocol_sha256": approved_protocol_sha256,
                        "plan_count": MAX_EVALUATIONS,
                    }
                    first_event = _prepare_event(
                        seq=1, event_id=initialized_event_id, run_id=run_id,
                        evaluation_id=None, attempt_id=None, event_type="RUN_INITIALIZED",
                        occurred_utc=initialized_utc, payload=initialized_payload,
                        prev_event_hash=ZERO_HASH,
                    )
                    conn.execute(
                        """INSERT INTO run_meta(singleton,run_id,schema_version,lock_identity,run_fingerprint_sha256,
                           approved_protocol_sha256,manifest_json,initial_results_sha256,initialized_utc,
                           initial_event_hash) VALUES(1,?,?,?,?,?,?,?,?,?)""",
                        (run_id, SCHEMA_VERSION, lock_identity, manifest_hash, approved_protocol_sha256,
                         manifest_json, initial_results_sha256, initialized_utc, first_event["event_hash"]),
                    )
                    for row in rows:
                        conn.execute(
                            """INSERT INTO planned_evaluations(run_id,evaluation_id,ordinal,case_id,arm,
                               prompt_id,schema_id,request_spec_sha256,plan_json)
                               VALUES(?,?,?,?,?,?,?,?,?)""",
                            (run_id, row["evaluation_id"], row["ordinal"], row["case_id"], row["arm"],
                             row.get("prompt_id", row.get("prompt", "")),
                             row.get("schema_id", row.get("schema", "")), row["request_spec_sha256"],
                             canonical_bytes(row.get("plan", row)).decode("utf-8")),
                        )
                    _insert_event(conn, first_event)
                    prev = first_event["event_hash"]
                    for seq, row in enumerate(rows, 2):
                        event = _prepare_event(
                            seq=seq, event_id=str(uuid.uuid4()), run_id=run_id,
                            evaluation_id=row["evaluation_id"], attempt_id=None,
                            event_type="EVALUATION_PLANNED", occurred_utc=initialized_utc,
                            payload={
                                "ordinal": row["ordinal"], "case_id": row["case_id"],
                                "arm": row["arm"], "request_spec_sha256": row["request_spec_sha256"],
                                "plan_sha256": sha256_hex(canonical_bytes(row.get("plan", row))),
                            }, prev_event_hash=prev,
                        )
                        _insert_event(conn, event)
                        prev = event["event_hash"]
                    if fault_hook:
                        fault_hook("during_initialization")
                    try:
                        conn.execute("COMMIT")
                    except BaseException as exc:
                        raise CommitAmbiguous(
                            "initialization commit was not acknowledged; preserve and replay the ledger in a fresh process"
                        ) from exc
                except CommitAmbiguous:
                    raise
                except BaseException:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    raise
                if fault_hook:
                    try:
                        fault_hook("after_initialization_commit")
                    except BaseException as exc:
                        raise CommitAmbiguous("initialization commit acknowledgment is ambiguous") from exc
                _validate_connection(conn)
            except BaseException:
                with contextlib.suppress(Exception):
                    conn.close()
                raise
            else:
                conn.close()

    @classmethod
    def open_existing(
        cls,
        path: str | Path,
        *,
        expected_fingerprint: str | None = None,
        lock_path: str | Path | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ) -> "Ledger":
        db_path = Path(path).resolve()
        lock_path = _absolute_path(lock_path) if lock_path else db_path.with_suffix(".lock")
        lock = RunLock(lock_path).acquire()
        conn: sqlite3.Connection | None = None
        try:
            if not db_path.is_file():
                raise LedgerBlocked("existing attempt ledger is required; refusing to create one")
            _validate_wal_sidecar(db_path)
            conn = sqlite3.connect(_sqlite_rw_uri(db_path), uri=True, timeout=5,
                                   isolation_level=None, check_same_thread=True)
            conn.row_factory = sqlite3.Row
            _configure(conn)
            _validate_connection(conn, expected_fingerprint=expected_fingerprint)
            if not lock.owns(lock_path):
                raise LedgerBlocked("run lock identity changed while opening the ledger")
            persisted_identity = conn.execute(
                "SELECT lock_identity FROM run_meta WHERE singleton=1").fetchone()[0]
            if persisted_identity != lock.identity_text:
                raise LedgerBlocked("run lock pathname does not identify the ledger's registered lock file")
            ledger = cls(conn, db_path, lock, fault_hook=fault_hook)
            ledger.replay_validate()
            return ledger
        except sqlite3.Error as exc:
            if conn is not None:
                with contextlib.suppress(Exception):
                    conn.close()
            lock.release()
            raise LedgerBlocked(f"SQLite open/integrity validation failed: {exc}") from exc
        except BaseException:
            if conn is not None:
                with contextlib.suppress(Exception):
                    conn.close()
            lock.release()
            raise

    @classmethod
    def _open_existing_for_tests(
        cls, path: str | Path, *, reconciliation_verifier: Callable[[Mapping[str, Any]], Any],
        expected_fingerprint: str | None = None, lock_path: str | Path | None = None,
        fault_hook: Callable[[str], None] | None = None,
    ) -> "Ledger":
        """Private test seam; ordinary opens and the CLI never receive a verifier."""
        if not callable(reconciliation_verifier):
            raise LedgerBlocked("test reconciliation verifier must be callable")
        ledger = cls.open_existing(path, expected_fingerprint=expected_fingerprint,
                                   lock_path=lock_path, fault_hook=fault_hook)
        ledger._reconciliation_verifier = reconciliation_verifier
        ledger._reconciliation_verifier_id = "test-only"
        return ledger

    def _assert_lock_owned(self) -> None:
        if self._closed:
            raise LedgerBlocked("ledger connection is closed after an ambiguous operation")
        if self._owner_pid != os.getpid():
            raise LedgerBlocked("ledger connection belongs to another process")
        if not self.lock.owns(self.lock.path):
            raise LedgerBlocked("ledger run-lock ownership or pathname identity cannot be verified")

    def _assert_open(self) -> None:
        self._assert_lock_owned()
        if threading.get_ident() != self._owner_thread:
            raise LedgerBlocked("ledger writer connection is owned by another thread")

    def _checkpoint(self, name: str) -> None:
        if self.fault_hook:
            self.fault_hook(name)

    def _evaluation_lock(self, evaluation: str) -> threading.RLock:
        with self._evaluation_locks_guard:
            lock = self._evaluation_locks.get(evaluation)
            if lock is None:
                lock = threading.RLock()
                self._evaluation_locks[evaluation] = lock
            return lock

    def _validate_dispatch_snapshot(self, prepared: Any, permit: DispatchPermit) -> None:
        self._assert_lock_owned()
        if self._closed or not self.path.is_file():
            raise LedgerBlocked("dispatch permit has no valid existing ledger")
        if permit._ledger is not self or prepared.run_id != self.run_id or permit.run_id != self.run_id:
            raise LedgerBlocked("dispatch permit belongs to another ledger/run")
        identity = (prepared.evaluation_id, prepared.attempt_id, prepared.request_hash)
        if identity != (permit.evaluation_id, permit.attempt_id, permit.request_hash):
            raise LedgerBlocked("dispatch permit does not match the prepared evaluation, attempt, and request")
        if not _is_hash(prepared.body_sha256) or not _is_hash(prepared.config_sha256):
            raise LedgerBlocked("prepared request body/configuration fingerprint is invalid")
        if sha256_hex(bytes(prepared.request.content)) != prepared.body_sha256:
            raise LedgerBlocked("prepared body hash changed before transport")

        conn = sqlite3.connect(_sqlite_ro_uri(self.path), uri=True, timeout=5,
                               isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            replay = self.replay_validate(conn)
            state = replay.states.get(permit.evaluation_id)
            mismatches=[]
            if state is None: mismatches.append("evaluation")
            else:
                if state.state != "UNKNOWN_OUTCOME" or state.missing_closed: mismatches.append("authorization_state")
                if state.terminal_event_id is not None or state.pending_reconciliation is not None: mismatches.append("closed_attempt")
                if state.attempt_id != permit.attempt_id: mismatches.append("attempt_id")
                if state.request_hash != permit.request_hash: mismatches.append("request_hash")
                if state.dispatch_event_id != permit.dispatch_event_id: mismatches.append("dispatch_event_id")
                if state.request_payload_sha256 != prepared.body_sha256: mismatches.append("body_sha256")
                if state.config_sha256 != prepared.config_sha256: mismatches.append("config_sha256")
            if mismatches:
                raise LedgerBlocked("dispatch permit is stale or differs from durable attempt: " + ",".join(mismatches))
            dispatches = [e for e in replay.events if e["event_id"] == permit.dispatch_event_id]
            if len(dispatches) != 1:
                raise LedgerBlocked("dispatch event ID is absent or ambiguous in committed history")
            event = dispatches[0]
            payload = event["payload"]
            if (event["event_type"] != "DISPATCH_INTENT"
                    or event["run_id"] != permit.run_id
                    or event["evaluation_id"] != permit.evaluation_id
                    or event["attempt_id"] != permit.attempt_id
                    or payload.get("request_hash") != prepared.request_hash
                    or payload.get("request_payload_sha256") != prepared.body_sha256
                    or payload.get("prepared_config_sha256") != prepared.config_sha256):
                raise LedgerBlocked("committed dispatch event does not authorize this exact request")
            for later in replay.events:
                if later["seq"] > event["seq"] and later["evaluation_id"] == permit.evaluation_id and later["event_type"] in {
                    "RECONCILIATION", "COMPLETED", "FAILED", "UNKNOWN_OUTCOME",
                }:
                    raise LedgerBlocked("a later terminal or reconciliation event closed this dispatch")
            conn.execute("ROLLBACK")
        except BaseException:
            if conn.in_transaction:
                with contextlib.suppress(sqlite3.Error):
                    conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    @contextlib.contextmanager
    def dispatch_lease(self, prepared: Any, permit: DispatchPermit):
        """Validate, consume, and hold per-evaluation authority through transport entry."""
        self._assert_lock_owned()
        if not isinstance(permit, DispatchPermit):
            raise LedgerBlocked("dispatch requires a ledger-issued session capability")
        lock = self._evaluation_lock(permit.evaluation_id)
        lock.acquire()
        active = False
        try:
            with self._capability_guard:
                if self._issued_permits.get(permit.dispatch_event_id) is not permit:
                    raise LedgerBlocked("dispatch permit was not issued by this open ledger session")
                if permit.consumed:
                    raise LedgerBlocked("dispatch permit has already been consumed")
            self._validate_dispatch_snapshot(prepared, permit)
            permit._consume_once()
            with self._capability_guard:
                self._active_dispatches.add(permit.dispatch_event_id)
            active = True
            yield
        finally:
            if active:
                with self._capability_guard:
                    self._active_dispatches.discard(permit.dispatch_event_id)
            lock.release()

    def _register_response_receipt(
        self, permit: DispatchPermit, status_code: int, raw_body: bytes,
        safe_headers: Mapping[str, str],
    ) -> DispatchResponseReceipt:
        body = bytes(raw_body)
        if len(body) > MAX_RESPONSE_BYTES:
            raise LedgerBlocked("complete dispatcher receipts may not exceed the response limit")
        with self._capability_guard:
            if (permit._ledger is not self or permit.dispatch_event_id not in self._active_dispatches
                    or self._issued_permits.get(permit.dispatch_event_id) is not permit):
                raise LedgerBlocked("response receipt requires the active validated dispatch lease")
            receipt = DispatchResponseReceipt._issue(self, permit, status_code, body, safe_headers)
            self._response_receipts[receipt.receipt_id] = receipt
            return receipt

    def _local_failure_evidence(
        self, evaluation: str, attempt: str, *, error_type: str, error: str,
    ) -> FailureEvidence:
        """Internal runner hook; only an un-dispatched IN_FLIGHT attempt can be proven failed."""
        with self._evaluation_lock(evaluation):
            replay = self.replay_validate()
            state = replay.states.get(evaluation)
            if not state or state.state != "IN_FLIGHT" or state.attempt_id != attempt or state.dispatch_event_id:
                raise LedgerBlocked("local failure evidence requires the matching IN_FLIGHT state with no dispatch")
            evidence = FailureEvidence._issue(self, evaluation, attempt, error_type, error)
            with self._capability_guard:
                self._issued_failures[id(evidence)] = evidence
            return evidence

    def _confirmed_failure_evidence(
        self, evaluation: str, attempt: str, *, error_type: str, error: str,
    ) -> FailureEvidence:
        """Issue a typed terminal failure only after explicit CONFIRMED_FAILED reconciliation."""
        with self._evaluation_lock(evaluation):
            replay = self.replay_validate()
            state = replay.states.get(evaluation)
            if (not state or state.state != "UNKNOWN_OUTCOME" or state.attempt_id != attempt
                    or state.pending_reconciliation != "CONFIRMED_FAILED"
                    or not state.pending_reconciliation_event_id):
                raise LedgerBlocked("confirmed failure evidence requires an explicit matching reconciliation")
            evidence = FailureEvidence._issue(
                self, evaluation, attempt, error_type, error,
                failure_kind="RECONCILIATION_CONFIRMED",
                reconciliation_event_id=state.pending_reconciliation_event_id,
            )
            with self._capability_guard:
                self._issued_failures[id(evidence)] = evidence
            return evidence

    def _make_completion(
        self, receipt: DispatchResponseReceipt, result_record: Mapping[str, Any], *,
        response_metadata: Mapping[str, Any],
    ) -> ValidatedCompletion:
        with self._capability_guard:
            if self._response_receipts.get(getattr(receipt, "receipt_id", "")) is not receipt:
                raise LedgerBlocked("completion requires an unused complete response receipt from this session")
            if receipt._ledger is not self or receipt.receipt_id in self._consumed_receipts:
                raise LedgerBlocked("response receipt belongs to another session or was already consumed")
        if len(receipt.raw_body) > MAX_RESPONSE_BYTES:
            raise LedgerBlocked("response receipt is incomplete or exceeds the configured limit")
        if not isinstance(result_record, Mapping):
            raise LedgerBlocked("completion base result must be a mapping")
        if not isinstance(response_metadata, Mapping):
            raise LedgerBlocked("completion response metadata must be a mapping")
        if not isinstance(response_metadata.get("safe_headers"), Mapping):
            raise LedgerBlocked("completion response headers must be receipt metadata")
        if (result_record.get("evaluation_id") != receipt.evaluation_id
                or result_record.get("attempt_id") != receipt.attempt_id
                or result_record.get("request_hash") != receipt.request_hash
                or response_metadata.get("dispatch_event_id") != receipt.dispatch_event_id
                or response_metadata.get("request_hash") != receipt.request_hash
                or response_metadata.get("response_body_complete") is not True
                or response_metadata.get("status_code") != receipt.status_code
                or dict(response_metadata.get("safe_headers", {})) != dict(receipt.safe_headers)
                or response_metadata.get("observed_response_bytes") != len(receipt.raw_body)
                or response_metadata.get("retained_prefix_sha256") != sha256_hex(receipt.raw_body)
                or (response_metadata.get("declared_content_length") is not None
                    and response_metadata["declared_content_length"] != len(receipt.raw_body))):
            raise LedgerBlocked("normalized result metadata differs from the dispatcher receipt identity")
        if not 200 <= receipt.status_code < 300:
            raise LedgerBlocked("non-2xx provider responses remain unknown outcomes")
        plan_row = next((row for row in self.plan_rows()
                         if row["evaluation_id"] == receipt.evaluation_id), None)
        if plan_row is None:
            raise LedgerBlocked("response receipt evaluation has no immutable registered plan")
        base = dict(result_record)
        if (base.get("evaluation_id") != receipt.evaluation_id
                or base.get("attempt_id") != receipt.attempt_id
                or base.get("request_hash") != receipt.request_hash):
            raise LedgerBlocked("completion base result identity differs from its response receipt")
        derived_result, validation = _derive_completion_from_response(
            receipt.raw_body, plan_row["plan"], base,
        )
        derived_metadata = dict(response_metadata)
        derived_metadata["usage"] = derived_result["usage"]
        derived_metadata["done_reason"] = derived_result["done_reason"]
        derivation = _completion_derivation_sha256(
            receipt, derived_result, bool(derived_result["valid"]), validation, derived_metadata,
        )
        return ValidatedCompletion._issue(
            self, receipt, derived_result, bool(derived_result["valid"]), validation,
            derived_metadata, derivation,
        )

    def close(self) -> None:
        if self._closed:
            return
        if self._owner_pid != os.getpid():
            # SQLite connections are not safe to operate after fork. The child
            # relinquishes only its descriptor copy; RunLock.release avoids unlock.
            self._closed = True
            self.lock.release()
            return
        try:
            self.conn.close()
        finally:
            self._closed = True
            self.lock.release()

    def __enter__(self) -> "Ledger":
        self._assert_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _run_write(self, event_id: str | None, operation: Callable[[], Any]) -> Any:
        self._assert_open()
        try:
            self.conn.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            raise LedgerBlocked(f"could not acquire SQLite write transaction: {exc}") from exc
        try:
            result = operation()
        except BaseException:
            if self.conn.in_transaction:
                with contextlib.suppress(sqlite3.Error):
                    self.conn.execute("ROLLBACK")
            raise
        try:
            self.conn.execute("COMMIT")
        except BaseException as exc:
            self._abandon()
            raise CommitAmbiguous("SQLite commit was not acknowledged; reopen and replay in a fresh process", event_id) from exc
        try:
            self._checkpoint("after_commit")
        except BaseException as exc:
            self._abandon()
            raise CommitAmbiguous("commit returned but acknowledgment hook failed; reopen and replay", event_id) from exc
        return result

    def _abandon(self) -> None:
        with contextlib.suppress(Exception):
            self.conn.close()
        self._closed = True
        self.lock.release()

    def _append_in_transaction(
        self, event_type: str, payload: Mapping[str, Any],
        evaluation: str | None = None, attempt: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_open()
        if event_type not in EVENT_TYPES:
            raise LedgerError(f"unsupported event type {event_type}")
        last = self.conn.execute("SELECT seq,event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        seq, prev = (int(last[0]) + 1, str(last[1])) if last else (1, ZERO_HASH)
        row = _prepare_event(
            seq=seq, event_id=event_id or str(uuid.uuid4()), run_id=self.run_id,
            evaluation_id=evaluation, attempt_id=attempt, event_type=event_type,
            occurred_utc=utc_now(), payload=payload, prev_event_hash=prev,
        )
        _insert_event(self.conn, row)
        return row

    def plan_rows(self, connection: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
        if connection is None:
            self._assert_open()
            connection = self.conn
        result = []
        for row in connection.execute(
            "SELECT * FROM planned_evaluations WHERE run_id=? ORDER BY ordinal", (self.run_id,),
        ):
            item = dict(row)
            item["plan"] = json.loads(item.pop("plan_json"))
            result.append(item)
        return result

    def replay_validate(self, connection: sqlite3.Connection | None = None) -> Replay:
        if connection is None:
            self._assert_open()
            connection = self.conn
        elif self._closed:
            raise LedgerBlocked("ledger is closed")
        _validate_connection(connection)
        meta = dict(connection.execute("SELECT * FROM run_meta WHERE singleton=1").fetchone())
        if meta["run_id"] != self.run_id or meta["schema_version"] != SCHEMA_VERSION:
            raise LedgerBlocked("run identity or schema version mismatch")
        manifest_json = meta["manifest_json"]
        try:
            manifest = json.loads(manifest_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise LedgerBlocked("run manifest JSON is corrupt") from exc
        if canonical_bytes(manifest).decode("utf-8") != manifest_json:
            raise LedgerBlocked("run manifest is not canonical JSON")
        if manifest_fingerprint(manifest) != meta["run_fingerprint_sha256"]:
            raise LedgerBlocked("run fingerprint does not match manifest bytes")
        fingerprint_inputs = manifest.get("fingerprint_inputs")
        if (not isinstance(fingerprint_inputs, Mapping)
                or fingerprint_inputs.get("completion_validator_version") != COMPLETION_VALIDATOR_VERSION):
            raise LedgerBlocked("run manifest does not bind the active completion validator version")

        planned = self.plan_rows(connection)
        if len(planned) != MAX_EVALUATIONS:
            raise LedgerBlocked("registered plan does not contain exactly 24 evaluations")
        plan_by_id: dict[str, dict[str, Any]] = {}
        states: dict[str, EvaluationState] = {}
        for ordinal, row in enumerate(planned, 1):
            if row["ordinal"] != ordinal:
                raise LedgerBlocked("registered plan ordinals are not contiguous")
            plan = row["plan"]
            if row["evaluation_id"] in plan_by_id:
                raise LedgerBlocked("duplicate evaluation identity in plan table")
            plan_by_id[row["evaluation_id"]] = row
            states[row["evaluation_id"]] = EvaluationState(
                evaluation_id=row["evaluation_id"], case_id=row["case_id"],
                arm=row["arm"], ordinal=ordinal,
            )

        events: list[dict[str, Any]] = []
        previous_hash = ZERO_HASH
        expected_seq = 1
        seen_event_ids: set[str] = set()
        seen_attempt_ids: set[str] = set()
        planned_event_ids: set[str] = set()
        for raw in connection.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq", (self.run_id,)):
            event = dict(raw)
            if event["seq"] != expected_seq:
                raise LedgerBlocked("event sequence is not contiguous")
            expected_seq += 1
            if event["event_id"] in seen_event_ids:
                raise LedgerBlocked("duplicate event ID")
            seen_event_ids.add(event["event_id"])
            if event["event_type"] not in EVENT_TYPES:
                raise LedgerBlocked("unknown event type")
            if event["prev_event_hash"] != previous_hash:
                raise LedgerBlocked("event hash-chain predecessor mismatch")
            if sha256_hex(event["payload_json"]) != event["payload_sha256"]:
                raise LedgerBlocked("event payload hash mismatch")
            try:
                payload = json.loads(event["payload_json"])
                timestamp = datetime.fromisoformat(event["occurred_utc"].replace("Z", "+00:00"))
            except (TypeError, json.JSONDecodeError, ValueError) as exc:
                raise LedgerBlocked("event payload or timestamp is invalid") from exc
            if timestamp.tzinfo is None or not event["occurred_utc"].endswith("Z"):
                raise LedgerBlocked("event timestamp must be UTC RFC3339 with Z suffix")
            if canonical_bytes(payload).decode("utf-8") != event["payload_json"]:
                raise LedgerBlocked("event payload JSON is not canonical")
            if _event_hash(event) != event["event_hash"]:
                raise LedgerBlocked("event hash mismatch")
            event["payload"] = payload
            previous_hash = event["event_hash"]
            if event["event_type"] == "IN_FLIGHT":
                if not event["attempt_id"] or event["attempt_id"] in seen_attempt_ids:
                    raise LedgerBlocked("attempt IDs must be globally unique within the run")
                seen_attempt_ids.add(event["attempt_id"])
            self._replay_one(event, states, plan_by_id, planned_event_ids, expected_seq - 2)
            events.append(event)
        expected_prefix = ["RUN_INITIALIZED"] + ["EVALUATION_PLANNED"] * MAX_EVALUATIONS
        if [event["event_type"] for event in events[:MAX_EVALUATIONS + 1]] != expected_prefix:
            raise LedgerBlocked("run initialization and the complete ordered plan must precede all attempts")
        if any(event["event_type"] in {"RUN_INITIALIZED", "EVALUATION_PLANNED"}
               for event in events[MAX_EVALUATIONS + 1:]):
            raise LedgerBlocked("plan registration event appears after attempt history begins")
        expected_plan_order = [row["evaluation_id"] for row in planned]
        actual_plan_order = [event["evaluation_id"] for event in events[1:MAX_EVALUATIONS + 1]]
        if actual_plan_order != expected_plan_order:
            raise LedgerBlocked("plan events do not match the immutable manifest order")
        if not events or events[0]["event_type"] != "RUN_INITIALIZED":
            raise LedgerBlocked("event history has no leading RUN_INITIALIZED event")
        if len(planned_event_ids) != MAX_EVALUATIONS:
            raise LedgerBlocked("event history does not register exactly the immutable 24-item plan")
        if events[0]["event_hash"] != meta["initial_event_hash"]:
            raise LedgerBlocked("initialization event hash does not match immutable manifest")
        initial_payload = events[0]["payload"]
        if initial_payload.get("run_fingerprint_sha256") != meta["run_fingerprint_sha256"]:
            raise LedgerBlocked("initialization event fingerprint mismatch")
        if initial_payload.get("approved_protocol_sha256") != meta["approved_protocol_sha256"]:
            raise LedgerBlocked("initialization event protocol approval mismatch")
        if initial_payload.get("plan_count") != MAX_EVALUATIONS:
            raise LedgerBlocked("initialization event plan count mismatch")
        # AUTOINCREMENT's high-water mark must agree with the append-only log.
        seq_row = connection.execute("SELECT seq FROM sqlite_sequence WHERE name='events'").fetchone()
        high_water = int(seq_row[0]) if seq_row else 0
        if high_water != len(events):
            raise LedgerBlocked("SQLite event sequence high-water mark disagrees with history")
        for state in states.values():
            if state.state == "DISPATCH_INTENT":
                state.state = "UNKNOWN_OUTCOME"
        return Replay(states=states, events=tuple(events), last_seq=len(events), last_hash=previous_hash)

    def _replay_one(
        self, event: Mapping[str, Any], states: dict[str, EvaluationState],
        plan_by_id: Mapping[str, Mapping[str, Any]], planned_event_ids: set[str],
        prior_seq: int,
    ) -> None:
        kind, eid, aid, payload = event["event_type"], event["evaluation_id"], event["attempt_id"], event["payload"]
        if prior_seq == 0:
            if kind != "RUN_INITIALIZED" or eid is not None or aid is not None:
                raise LedgerBlocked("first event must be RUN_INITIALIZED")
            if payload.get("run_id") != self.run_id or payload.get("schema_version") != SCHEMA_VERSION:
                raise LedgerBlocked("RUN_INITIALIZED identity mismatch")
            if payload.get("lock_identity") != self.run_meta.get("lock_identity"):
                raise LedgerBlocked("RUN_INITIALIZED lock identity mismatch")
            return
        if kind == "RUN_INITIALIZED":
            raise LedgerBlocked("duplicate RUN_INITIALIZED event")
        if kind == "EXPORT_WRITTEN":
            if eid is not None or aid is not None or not _is_hash(payload.get("sha256")):
                raise LedgerBlocked("malformed export event")
            if int(payload.get("source_event_seq", -1)) > prior_seq:
                raise LedgerBlocked("export refers to future event sequence")
            return
        if eid not in states or eid not in plan_by_id:
            raise LedgerBlocked("event refers to an unregistered evaluation")
        state = states[eid]
        if kind == "EVALUATION_PLANNED":
            row = plan_by_id[eid]
            if aid is not None or state.state != "PLANNED" or eid in planned_event_ids:
                raise LedgerBlocked("duplicate or out-of-order EVALUATION_PLANNED")
            if (payload.get("ordinal"), payload.get("case_id"), payload.get("arm"), payload.get("request_spec_sha256")) != (
                row["ordinal"], row["case_id"], row["arm"], row["request_spec_sha256"],
            ):
                raise LedgerBlocked("plan table/event history disagreement")
            if payload.get("plan_sha256") != sha256_hex(canonical_bytes(row["plan"])):
                raise LedgerBlocked("registered plan row hash mismatch")
            planned_event_ids.add(eid)
            return
        if eid not in planned_event_ids:
            raise LedgerBlocked("attempt event precedes its EVALUATION_PLANNED event")
        if not aid:
            raise LedgerBlocked("attempt event has no attempt ID")
        if kind == "IN_FLIGHT":
            if state.state != "PLANNED" or state.attempt_id is not None or not _is_hash(payload.get("request_hash")):
                raise LedgerBlocked("invalid/duplicate IN_FLIGHT event")
            if payload.get("request_spec_sha256") != plan_by_id[eid]["request_spec_sha256"]:
                raise LedgerBlocked("attempt request fingerprint does not match frozen plan")
            if payload.get("request_payload_sha256") is not None and not _is_hash(payload["request_payload_sha256"]):
                raise LedgerBlocked("attempt request payload fingerprint is invalid")
            if not _is_hash(payload.get("config_sha256")):
                raise LedgerBlocked("attempt prepared configuration fingerprint is invalid")
            state.state, state.attempt_id = "IN_FLIGHT", aid
            state.request_hash = payload["request_hash"]
            state.request_payload_sha256 = payload.get("request_payload_sha256")
            state.config_sha256 = payload["config_sha256"]
            return
        if aid != state.attempt_id:
            raise LedgerBlocked("event attempt ID does not match original attempt")
        if kind == "RECONCILIATION":
            if state.state == "DISPATCH_INTENT":
                # With no terminal event, a committed dispatch derives to unknown.
                state.state = "UNKNOWN_OUTCOME"
            disposition = payload.get("disposition")
            if payload.get("run_fingerprint_sha256") != self.run_meta["run_fingerprint_sha256"]:
                raise LedgerBlocked("reconciliation fingerprint mismatch")
            proposal_keys = (
                "reviewer_identity", "timestamp_utc", "evaluation_id", "attempt_id",
                "prior_derived_state", "disposition", "evidence_references", "rationale",
                "run_fingerprint_sha256", "boundary_invariant_verified",
            )
            proposal = {key: payload.get(key) for key in proposal_keys}
            if (not payload.get("reviewer_identity") or not payload.get("rationale")
                    or payload.get("authorization_verified") is not True
                    or payload.get("verifier_id") != "test-only"
                    or payload.get("proposal_sha256") != sha256_hex(canonical_bytes(proposal))):
                raise LedgerBlocked("reconciliation lacks a verified authorization attestation")
            if payload.get("prior_derived_state") != state.state:
                raise LedgerBlocked("reconciliation prior state does not match replay")
            if disposition == "CONFIRMED_NOT_DISPATCHED":
                if state.state != "IN_FLIGHT" or state.dispatch_event_id or not payload.get("boundary_invariant_verified"):
                    raise LedgerBlocked("CONFIRMED_NOT_DISPATCHED is allowed only for I without D and verified boundary")
                state.state = "READY_TO_DISPATCH"
            elif disposition == "ACCEPTED_UNKNOWN_MISSING":
                if state.state != "UNKNOWN_OUTCOME":
                    raise LedgerBlocked("ACCEPTED_UNKNOWN_MISSING requires UNKNOWN_OUTCOME")
                state.missing_closed = True
            elif disposition in {"CONFIRMED_COMPLETED", "CONFIRMED_FAILED"}:
                if state.state != "UNKNOWN_OUTCOME":
                    raise LedgerBlocked(f"{disposition} requires UNKNOWN_OUTCOME")
                state.pending_reconciliation = disposition
                state.pending_reconciliation_event_id = event["event_id"]
            else:
                raise LedgerBlocked("unknown reconciliation disposition")
            return
        if kind == "DISPATCH_INTENT":
            if state.state not in {"IN_FLIGHT", "READY_TO_DISPATCH"} or state.dispatch_event_id:
                raise LedgerBlocked("dispatch is illegal or already consumed")
            if payload.get("request_hash") != state.request_hash:
                raise LedgerBlocked("dispatch request hash differs from original attempt")
            if payload.get("request_payload_sha256") != state.request_payload_sha256:
                raise LedgerBlocked("dispatch body fingerprint differs from prepared request")
            if payload.get("prepared_config_sha256") != state.config_sha256:
                raise LedgerBlocked("dispatch configuration fingerprint differs from prepared request")
            state.state, state.dispatch_event_id = "DISPATCH_INTENT", event["event_id"]
            return
        if kind == "COMPLETED":
            if state.state not in {"DISPATCH_INTENT", "UNKNOWN_OUTCOME"}:
                raise LedgerBlocked("COMPLETED requires a dispatched request")
            if (state.state == "UNKNOWN_OUTCOME" and state.terminal_event_id is not None
                    and state.pending_reconciliation != "CONFIRMED_COMPLETED"):
                raise LedgerBlocked("unknown result requires CONFIRMED_COMPLETED reconciliation")
            if payload.get("request_hash") != state.request_hash:
                raise LedgerBlocked("completion request hash mismatch")
            if payload.get("completion_event_id") != event["event_id"]:
                raise LedgerBlocked("completion payload event identity does not match its ledger event")
            receipt = payload.get("response_receipt")
            if not isinstance(receipt, dict) or receipt.get("complete") is not True:
                raise LedgerBlocked("completion lacks a complete dispatcher response receipt")
            if (receipt.get("run_id") != self.run_id or receipt.get("evaluation_id") != eid
                    or receipt.get("attempt_id") != aid or receipt.get("dispatch_event_id") != state.dispatch_event_id
                    or receipt.get("request_hash") != state.request_hash or not receipt.get("receipt_id")):
                raise LedgerBlocked("completion receipt does not match the original dispatch identity")
            if not isinstance(receipt.get("status_code"), int) or not 200 <= receipt["status_code"] < 300:
                raise LedgerBlocked("only complete 2xx responses may be recorded as COMPLETED")
            try:
                raw_bytes = base64.b64decode(receipt.get("raw_body_b64"), validate=True)
            except (ValueError, TypeError) as exc:
                raise LedgerBlocked("completion raw response is not valid base64") from exc
            if (len(raw_bytes) > MAX_RESPONSE_BYTES or sha256_hex(raw_bytes) != receipt.get("raw_body_sha256")
                    or receipt.get("raw_body_sha256") != payload.get("raw_response_sha256")):
                raise LedgerBlocked("completion raw response hash mismatch")
            result, validation = payload.get("result_record"), payload.get("validation")
            metadata, valid = payload.get("response_metadata"), payload.get("valid")
            if (not isinstance(result, dict) or not isinstance(validation, dict)
                    or not isinstance(metadata, dict) or not isinstance(valid, bool)
                    or valid != result.get("valid") or valid != validation.get("valid")):
                raise LedgerBlocked("completion has no consistent normalized result record")
            if not isinstance(metadata.get("safe_headers"), dict):
                raise LedgerBlocked("completion response headers are malformed")
            if (metadata.get("response_body_complete") is not True
                    or metadata.get("dispatch_event_id") != state.dispatch_event_id
                    or metadata.get("request_hash") != state.request_hash
                    or metadata.get("status_code") != receipt.get("status_code")
                    or dict(metadata.get("safe_headers", {})) != dict(receipt.get("safe_headers", {}))
                    or metadata.get("observed_response_bytes") != len(raw_bytes)
                    or metadata.get("retained_prefix_sha256") != sha256_hex(raw_bytes)
                    or (metadata.get("declared_content_length") is not None
                        and metadata["declared_content_length"] != len(raw_bytes))):
                raise LedgerBlocked("completion metadata does not prove a complete matching response")
            synthetic_receipt = DispatchResponseReceipt._issue(
                self, DispatchPermit._issue(self, self.run_id, eid, aid, state.request_hash,
                                            state.dispatch_event_id),
                int(receipt.get("status_code", -1)), raw_bytes, receipt.get("safe_headers", {}),
            )
            object.__setattr__(synthetic_receipt, "receipt_id", receipt["receipt_id"])
            if payload.get("completion_validation_version") != COMPLETION_VALIDATOR_VERSION:
                raise LedgerBlocked("completion validation version is unsupported")
            derived_result, derived_validation = _derive_completion_from_response(
                raw_bytes, plan_by_id[eid]["plan"], result,
            )
            derived_metadata = dict(metadata)
            derived_metadata["usage"] = derived_result["usage"]
            derived_metadata["done_reason"] = derived_result["done_reason"]
            if (derived_result != result or derived_validation != validation
                    or derived_result["valid"] is not valid or derived_metadata != metadata):
                raise LedgerBlocked("completion output or validation disagrees with exact response bytes")
            if _completion_derivation_sha256(synthetic_receipt, result, valid, validation, metadata) != payload.get("result_derivation_sha256"):
                raise LedgerBlocked("completion derivation metadata does not match its receipt and result")
            state.state, state.result, state.terminal_event_id = "COMPLETED", result, event["event_id"]
            state.pending_reconciliation = None
            state.pending_reconciliation_event_id = None
            return
        if kind == "FAILED":
            if state.state == "IN_FLIGHT":
                if payload.get("failure_kind") != "LOCAL_PRE_DISPATCH" or state.dispatch_event_id:
                    raise LedgerBlocked("FAILED requires trusted local proof before dispatch")
            elif state.state == "UNKNOWN_OUTCOME":
                if (state.pending_reconciliation != "CONFIRMED_FAILED"
                        or payload.get("failure_kind") != "RECONCILIATION_CONFIRMED"
                        or payload.get("reconciliation_event_id") != state.pending_reconciliation_event_id):
                    raise LedgerBlocked("unknown failure requires CONFIRMED_FAILED reconciliation")
            else:
                raise LedgerBlocked("FAILED event is illegal in current state")
            state.state, state.result, state.terminal_event_id = "FAILED", payload.get("result_record", {}), event["event_id"]
            state.pending_reconciliation = None
            state.pending_reconciliation_event_id = None
            return
        if kind == "UNKNOWN_OUTCOME":
            if state.state != "DISPATCH_INTENT":
                raise LedgerBlocked("UNKNOWN_OUTCOME requires an unresolved dispatch intent")
            if payload.get("request_hash") != state.request_hash:
                raise LedgerBlocked("unknown-outcome request hash mismatch")
            receipt = payload.get("response_receipt")
            if receipt is not None:
                if (not isinstance(receipt, dict) or receipt.get("complete") is not True
                        or receipt.get("run_id") != self.run_id or receipt.get("evaluation_id") != eid
                        or receipt.get("attempt_id") != aid or receipt.get("dispatch_event_id") != state.dispatch_event_id
                        or receipt.get("request_hash") != state.request_hash):
                    raise LedgerBlocked("unknown response receipt does not match the consumed dispatch")
                try:
                    raw = base64.b64decode(receipt.get("raw_body_b64"), validate=True)
                except (ValueError, TypeError) as exc:
                    raise LedgerBlocked("unknown response receipt body is invalid base64") from exc
                if len(raw) > MAX_RESPONSE_BYTES or sha256_hex(raw) != receipt.get("raw_body_sha256"):
                    raise LedgerBlocked("unknown response receipt body hash/size is invalid")
            state.state, state.terminal_event_id = "UNKNOWN_OUTCOME", event["event_id"]
            return
        raise LedgerBlocked(f"unexpected event type in evaluation history: {kind}")

    def allocate_attempt_id(self) -> str:
        self._assert_open()
        return str(uuid.uuid4())

    def begin_attempt(
        self, evaluation: str, attempt: str, request_hash: str,
        request_spec_sha256: str, config_sha256: str,
        request_payload_sha256: str | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        def op() -> str:
            replay = self.replay_validate()
            state = replay.states.get(evaluation)
            if not state or state.state != "PLANNED":
                raise LedgerBlocked("evaluation is not untouched and PLANNED")
            row = next(r for r in self.plan_rows() if r["evaluation_id"] == evaluation)
            if request_spec_sha256 != row["request_spec_sha256"]:
                raise LedgerBlocked("request specification differs from immutable plan")
            if not _is_hash(request_hash) or not _is_hash(config_sha256):
                raise LedgerBlocked("prepared request/configuration fingerprints must be SHA-256 hex digests")
            if request_payload_sha256 is not None and not _is_hash(request_payload_sha256):
                raise LedgerBlocked("prepared request body fingerprint must be SHA-256 hex")
            self._checkpoint("before_in_flight_insert")
            self._append_in_transaction("IN_FLIGHT", {
                "request_hash": request_hash, "request_spec_sha256": request_spec_sha256,
                "request_payload_sha256": request_payload_sha256,
                "config_sha256": config_sha256, "started_utc": utc_now(),
            }, evaluation, attempt, event_id)
            self._checkpoint("during_in_flight_transaction")
            return event_id
        result = self._run_write(event_id, op)
        self._checkpoint("after_in_flight_commit")
        return result

    def authorize_dispatch(
        self, evaluation: str, attempt: str, request_hash: str,
    ) -> DispatchPermit:
        event_id = str(uuid.uuid4())
        with self._evaluation_lock(evaluation):
            def op() -> None:
                replay = self.replay_validate()
                state = replay.states.get(evaluation)
                if not state or state.state not in {"IN_FLIGHT", "READY_TO_DISPATCH"}:
                    raise LedgerBlocked("evaluation is not eligible for its first dispatch")
                if state.attempt_id != attempt or state.request_hash != request_hash or state.dispatch_event_id:
                    raise LedgerBlocked("attempt or request identity mismatch/dispatch already consumed")
                if state.missing_closed or state.pending_reconciliation:
                    raise LedgerBlocked("reconciled evaluation cannot receive a new dispatch")
                if sum(1 for e in replay.events if e["event_type"] == "DISPATCH_INTENT") >= MAX_EVALUATIONS:
                    raise LedgerBlocked("24-dispatch budget exhausted")
                self._append_in_transaction("DISPATCH_INTENT", {
                    "request_hash": request_hash,
                    "request_payload_sha256": state.request_payload_sha256,
                    "prepared_config_sha256": state.config_sha256,
                }, evaluation, attempt, event_id)
                self._checkpoint("during_dispatch_transaction")
            self._run_write(event_id, op)
            self._checkpoint("after_dispatch_intent_commit")
            permit = DispatchPermit._issue(self, self.run_id, evaluation, attempt, request_hash, event_id)
            with self._capability_guard:
                self._issued_permits[event_id] = permit
            return permit

    def record_completed(self, completion: ValidatedCompletion) -> str:
        """Persist only a completion derived from this session's exact dispatcher receipt."""
        if not isinstance(completion, ValidatedCompletion) or completion._ledger is not self:
            raise LedgerBlocked("record_completed requires a session-bound validated completion")
        receipt = completion.response_receipt
        if len(receipt.raw_body) > MAX_RESPONSE_BYTES or sha256_hex(receipt.raw_body) != receipt.raw_body_sha256:
            raise LedgerBlocked("validated completion changed after response processing")
        plan_row = next((row for row in self.plan_rows()
                         if row["evaluation_id"] == receipt.evaluation_id), None)
        if plan_row is None:
            raise LedgerBlocked("completion evaluation has no immutable registered plan")
        derived_result, derived_validation = _derive_completion_from_response(
            receipt.raw_body, plan_row["plan"], completion.result_record,
        )
        derived_metadata = dict(completion.response_metadata)
        derived_metadata["usage"] = derived_result["usage"]
        derived_metadata["done_reason"] = derived_result["done_reason"]
        if (derived_result != dict(completion.result_record)
                or derived_validation != dict(completion.validation)
                or derived_result["valid"] is not completion.valid
                or derived_metadata != dict(completion.response_metadata)
                or _completion_derivation_sha256(
                    receipt, derived_result, completion.valid, derived_validation, derived_metadata,
                ) != completion.result_derivation_sha256):
            raise LedgerBlocked("completion derivation differs from exact response bytes")
        evaluation, attempt, request_hash = receipt.evaluation_id, receipt.attempt_id, receipt.request_hash
        event_id = str(uuid.uuid4())
        with self._evaluation_lock(evaluation):
            with self._capability_guard:
                if (self._response_receipts.get(receipt.receipt_id) is not receipt
                        or receipt.receipt_id in self._consumed_receipts):
                    raise LedgerBlocked("response receipt is missing, foreign, or already consumed")
            receipt_record = {
                "receipt_id": receipt.receipt_id, "run_id": receipt.run_id,
                "evaluation_id": receipt.evaluation_id, "attempt_id": receipt.attempt_id,
                "dispatch_event_id": receipt.dispatch_event_id, "request_hash": receipt.request_hash,
                "status_code": receipt.status_code, "safe_headers": dict(receipt.safe_headers),
                "raw_body_b64": base64.b64encode(receipt.raw_body).decode("ascii"),
                "raw_body_sha256": receipt.raw_body_sha256, "complete": True,
            }
            payload = {
                "completion_event_id": event_id, "request_hash": request_hash,
                "response_receipt": receipt_record,
                "raw_response_sha256": receipt.raw_body_sha256,
                "result_record": dict(completion.result_record), "valid": completion.valid,
                "validation": dict(completion.validation),
                "response_metadata": dict(completion.response_metadata),
                "result_derivation_sha256": completion.result_derivation_sha256,
                "completion_validation_version": COMPLETION_VALIDATOR_VERSION,
                "completed_utc": utc_now(),
            }
            def op() -> str:
                replay = self.replay_validate()
                state = replay.states.get(evaluation)
                if (not state or state.attempt_id != attempt or state.request_hash != request_hash
                        or state.dispatch_event_id != receipt.dispatch_event_id
                        or state.state != "UNKNOWN_OUTCOME" or state.terminal_event_id is not None
                        or state.missing_closed or state.pending_reconciliation):
                    raise LedgerBlocked("completion receipt no longer matches the unresolved dispatch")
                self._append_in_transaction("COMPLETED", payload, evaluation, attempt, event_id)
                self._checkpoint("during_completion_transaction")
                return event_id
            result = self._run_write(event_id, op)
            with self._capability_guard:
                self._consumed_receipts.add(receipt.receipt_id)
            self._checkpoint("after_completion_commit")
            return result

    def record_failed(self, evidence: FailureEvidence) -> str:
        """Record only typed pre-dispatch or explicitly reconciled terminal failure evidence."""
        if not isinstance(evidence, FailureEvidence) or evidence._ledger is not self:
            raise LedgerBlocked("record_failed requires session-bound failure evidence")
        evaluation, attempt = evidence.evaluation_id, evidence.attempt_id
        with self._evaluation_lock(evaluation):
            with self._capability_guard:
                if self._issued_failures.get(id(evidence)) is not evidence:
                    raise LedgerBlocked("local failure evidence was not issued by this ledger session")
            event_id = str(uuid.uuid4())
            payload = {
                "failure_kind": evidence.failure_kind,
                "reconciliation_event_id": evidence.reconciliation_event_id,
                "error_type": evidence.error_type, "error": evidence.error,
                "failed_utc": utc_now(), "result_record": {},
            }
            def op() -> str:
                replay = self.replay_validate()
                state = replay.states.get(evaluation)
                if not state or state.attempt_id != attempt:
                    raise LedgerBlocked("failure evidence does not match the original attempt")
                if evidence.failure_kind == "LOCAL_PRE_DISPATCH":
                    if state.state != "IN_FLIGHT" or state.dispatch_event_id:
                        raise LedgerBlocked("local failure requires the original IN_FLIGHT state with no dispatch")
                elif evidence.failure_kind == "RECONCILIATION_CONFIRMED":
                    if (state.state != "UNKNOWN_OUTCOME" or state.pending_reconciliation != "CONFIRMED_FAILED"
                            or state.pending_reconciliation_event_id != evidence.reconciliation_event_id):
                        raise LedgerBlocked("reconciled failure evidence no longer matches its approval event")
                else:
                    raise LedgerBlocked("unknown typed failure kind")
                self._append_in_transaction("FAILED", payload, evaluation, attempt, event_id)
                self._checkpoint("during_failure_transaction")
                return event_id
            result = self._run_write(event_id, op)
            with self._capability_guard:
                self._issued_failures.pop(id(evidence), None)
            return result

    def record_unknown(
        self, evaluation: str, attempt: str, *, reason: str,
        metadata: Mapping[str, Any] | None = None,
        response_receipt: DispatchResponseReceipt | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        with self._evaluation_lock(evaluation):
            receipt_record = None
            if response_receipt is not None:
                with self._capability_guard:
                    if (self._response_receipts.get(response_receipt.receipt_id) is not response_receipt
                            or response_receipt.receipt_id in self._consumed_receipts):
                        raise LedgerBlocked("unknown outcome receipt is missing, foreign, or already consumed")
                if response_receipt.evaluation_id != evaluation or response_receipt.attempt_id != attempt:
                    raise LedgerBlocked("response receipt belongs to another evaluation or attempt")
                receipt_record = {
                    "receipt_id": response_receipt.receipt_id, "run_id": response_receipt.run_id,
                    "evaluation_id": response_receipt.evaluation_id, "attempt_id": response_receipt.attempt_id,
                    "dispatch_event_id": response_receipt.dispatch_event_id,
                    "request_hash": response_receipt.request_hash, "status_code": response_receipt.status_code,
                    "safe_headers": dict(response_receipt.safe_headers),
                    "raw_body_b64": base64.b64encode(response_receipt.raw_body).decode("ascii"),
                    "raw_body_sha256": response_receipt.raw_body_sha256, "complete": True,
                }
            payload = {
                "request_hash": None, "reason": str(reason)[:500],
                "metadata": dict(metadata or {}), "response_receipt": receipt_record,
                "observed_utc": utc_now(),
            }
            def op() -> str:
                replay = self.replay_validate()
                state = replay.states.get(evaluation)
                if (not state or state.attempt_id != attempt or state.state != "UNKNOWN_OUTCOME"
                        or state.terminal_event_id is not None or state.missing_closed
                        or (response_receipt is not None and state.dispatch_event_id != response_receipt.dispatch_event_id)):
                    raise LedgerBlocked("unknown outcome must match an unresolved dispatch")
                payload["request_hash"] = state.request_hash
                self._append_in_transaction("UNKNOWN_OUTCOME", payload, evaluation, attempt, event_id)
                self._checkpoint("during_unknown_transaction")
                return event_id
            result = self._run_write(event_id, op)
            if response_receipt is not None:
                with self._capability_guard:
                    self._consumed_receipts.add(response_receipt.receipt_id)
            return result

    def reconcile(
        self, evaluation: str, attempt: str, *, reviewer_identity: str,
        disposition: str, evidence_references: Iterable[Mapping[str, Any]],
        rationale: str, boundary_invariant_verified: bool = False,
    ) -> str:
        self._assert_open()
        with self._evaluation_lock(evaluation):
            with self._capability_guard:
                pending = any(
                    receipt.evaluation_id == evaluation and receipt.receipt_id not in self._consumed_receipts
                    for receipt in self._response_receipts.values()
                )
            if pending:
                raise LedgerBlocked("a complete provider response is awaiting durable completion recording")
            return self._reconcile_locked(
                evaluation, attempt, reviewer_identity=reviewer_identity,
                disposition=disposition, evidence_references=evidence_references,
                rationale=rationale,
                boundary_invariant_verified=boundary_invariant_verified,
            )

    def _reconcile_locked(
        self, evaluation: str, attempt: str, *, reviewer_identity: str,
        disposition: str, evidence_references: Iterable[Mapping[str, Any]],
        rationale: str, boundary_invariant_verified: bool = False,
    ) -> str:
        event_id = str(uuid.uuid4())
        evidence = [dict(item) for item in evidence_references]
        if self._reconciliation_verifier is None or not self._reconciliation_verifier_id:
            raise LedgerBlocked("no trusted reconciliation verifier is configured")
        replay_before = self.replay_validate()
        state_before = replay_before.states.get(evaluation)
        if not state_before or state_before.attempt_id != attempt:
            raise LedgerBlocked("reconciliation does not match the original attempt")
        if not reviewer_identity.strip() or not rationale.strip() or not evidence:
            raise LedgerBlocked("reconciliation requires reviewer, evidence and rationale")
        proposal = {
            "reviewer_identity": reviewer_identity.strip(), "timestamp_utc": utc_now(),
            "evaluation_id": evaluation, "attempt_id": attempt,
            "prior_derived_state": state_before.state, "disposition": disposition,
            "evidence_references": evidence, "rationale": rationale.strip(),
            "run_fingerprint_sha256": self.run_meta["run_fingerprint_sha256"],
            "boundary_invariant_verified": bool(boundary_invariant_verified),
        }
        proposal_hash = sha256_hex(canonical_bytes(proposal))
        try:
            verifier_input = json.loads(canonical_bytes(proposal).decode("utf-8"))
            verified = self._reconciliation_verifier(verifier_input)
        except Exception as exc:
            raise LedgerBlocked("reconciliation verifier failed closed") from exc
        if verified is not True:
            raise LedgerBlocked("reconciliation verifier did not authenticate the proposal")
        def op() -> str:
            replay = self.replay_validate()
            state = replay.states.get(evaluation)
            if not state or state.attempt_id != attempt:
                raise LedgerBlocked("reconciliation does not match the original attempt")
            if state.state != state_before.state:
                raise LedgerBlocked("reconciliation state changed after authorization verification")
            if disposition == "CONFIRMED_NOT_DISPATCHED" and state.dispatch_event_id:
                raise LedgerBlocked("a dispatch marker permanently consumes the planned dispatch")
            payload = dict(proposal)
            payload.update({"authorization_verified": True,
                            "verifier_id": self._reconciliation_verifier_id,
                            "proposal_sha256": proposal_hash})
            self._append_in_transaction("RECONCILIATION", payload, evaluation, attempt, event_id)
            self._checkpoint("during_reconciliation_transaction")
            return event_id
        return self._run_write(event_id, op)

    def known_export_hashes(self) -> set[str]:
        replay = self.replay_validate()
        hashes = {self.run_meta["initial_results_sha256"]}
        hashes.update(
            event["payload"].get("sha256") for event in replay.events
            if event["event_type"] == "EXPORT_WRITTEN"
        )
        hashes.discard(None)
        return hashes

    def build_export(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        replay = self.replay_validate()
        rows: dict[str, dict[str, Any]] = {}
        for state in replay.states.values():
            if state.state == "COMPLETED" and state.result is not None:
                rows[state.evaluation_id] = dict(state.result)
            elif state.state in {"FAILED", "UNKNOWN_OUTCOME"}:
                rows[state.evaluation_id] = {
                    "case": state.case_id, "arm": state.arm,
                    "revision": json.loads(self.run_meta["manifest_json"]).get("revision"),
                    "valid": False, "outcome_state": state.state.lower(),
                    "attempt_id": state.attempt_id, "missing": state.state == "UNKNOWN_OUTCOME",
                }
        output = dict(envelope)
        output["results"] = [rows[row["evaluation_id"]] for row in self.plan_rows()
                             if row["evaluation_id"] in rows]
        output["status"] = "partial" if len(rows) < MAX_EVALUATIONS else (
            "complete" if all(s.state == "COMPLETED" for s in replay.states.values()) else "complete_with_failures"
        )
        output["revision"] = json.loads(self.run_meta["manifest_json"]).get("revision", output.get("revision"))
        return output

    def export_json(self, path: str | Path, envelope: Mapping[str, Any]) -> str:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        existing_hash: str | None = None
        if target.exists():
            existing_hash = sha256_hex(target.read_bytes())
        payload = canonical_bytes(self.build_export(envelope))
        output_hash = sha256_hex(payload)
        allowed = self.known_export_hashes()
        if existing_hash is not None and existing_hash not in allowed and existing_hash != output_hash:
            raise LedgerBlocked("results JSON has unknown contents; preserving it and blocking export")
        if existing_hash != output_hash:
            temp_path: Path | None = None
            try:
                import tempfile
                fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
                temp_path = Path(temp_name)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_path, target)
                temp_path = None
                self._checkpoint("after_json_replace_before_export_event")
            finally:
                if temp_path is not None:
                    with contextlib.suppress(OSError):
                        temp_path.unlink()
        # A crash between replacement and this append is recovered by the deterministic hash above.
        if output_hash not in self.known_export_hashes():
            event_id = str(uuid.uuid4())
            def op() -> str:
                replay = self.replay_validate()
                return self._append_in_transaction("EXPORT_WRITTEN", {
                    "sha256": output_hash, "source_event_seq": replay.last_seq,
                    "written_utc": utc_now(),
                }, event_id=event_id)["event_id"]
            self._run_write(event_id, op)
        return output_hash


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _validate_connection(conn: sqlite3.Connection, *, expected_fingerprint: str | None = None) -> None:
    try:
        check = conn.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            raise LedgerBlocked(f"SQLite integrity_check failed: {check[0] if check else 'no result'}")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise LedgerBlocked("SQLite foreign_key_check found a violation")
        meta = conn.execute("SELECT * FROM run_meta WHERE singleton=1").fetchone()
        if (meta is None or meta["schema_version"] != SCHEMA_VERSION
                or not isinstance(meta["lock_identity"], str) or ":" not in meta["lock_identity"]):
            raise LedgerBlocked("missing run metadata or unsupported schema version")
        if expected_fingerprint and meta["run_fingerprint_sha256"] != expected_fingerprint:
            raise LedgerBlocked("run fingerprint mismatch; refusing resume")
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        required = {"run_meta", "planned_evaluations", "events", "events_no_update", "events_no_delete",
                    "plan_no_update", "plan_no_delete", "run_meta_no_update", "run_meta_no_delete",
                    "one_attempt_start_per_evaluation", "one_attempt_id_per_run", "one_dispatch_intent_per_evaluation",
                    "one_completion_per_evaluation", "one_failure_per_evaluation"}
        if not required.issubset(names):
            raise LedgerBlocked("ledger schema objects are incomplete")
    except sqlite3.Error as exc:
        if isinstance(exc, LedgerBlocked):
            raise
        raise LedgerBlocked(f"SQLite integrity/schema check failed: {exc}") from exc

