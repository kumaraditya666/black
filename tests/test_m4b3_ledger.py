"""Fault tests for the M4B.3 ledger; every HTTP request terminates at loopback."""
from __future__ import annotations

import hashlib
import base64
import gzip
import http.server
import json
import os
import queue
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import httpx
import pytest
import blackbox.m4b3_ledger as ledger_module

from blackbox.m4b3_ledger import (
    CommitAmbiguous, DispatchPermit, Ledger, LedgerBlocked, LockUnavailable, RunLock,
    canonical_bytes, evaluation_id, manifest_fingerprint, request_spec_hash,
)
from blackbox.providers import M4B3OllamaDispatcher, M4B3TransportPhase, ProviderError, TransportOutcome
import scripts.evaluate_m4b3 as runner


ROOT = Path(__file__).resolve().parents[1]
TEST_MODEL = {
    "model": runner.MODEL,
    "model_digest": runner.MODEL_DIGEST,
    "ollama_version": runner.PROPOSED_OLLAMA_VERSION,
    "provider": "ollama",
    "temperature": 0,
    "context_tokens": 2048,
    "thinking": False,
    "provider_timeout_seconds": 3,
    "output_limit": 768,
    "retry_policy": "zero retries",
}


def _approval_manifest():
    docs = {}
    for path in (
        "research/56_M4B3_PROSPECTIVE_AMENDMENT_DRAFT.md",
        "research/57_M4B3_EVALUATOR_RUBRIC_DRAFT.md",
    ):
        docs[path] = {"sha256": runner._document_hash(path), "approval": "APPROVED_FOR_IMPLEMENTATION"}
    return {
        "status": "APPROVED",
        "reviewer_identity": "synthetic test reviewer",
        "approved_at": "2026-11-07T00:00:00Z",
        "signature": "synthetic-only-test-approval",
        "documents": docs,
        "test_only": True,
    }


def _test_approval_verifier(approval):
    """Isolated fixture verifier; never wired into the production CLI or initializer."""
    return (
        isinstance(approval, dict)
        and approval.get("test_only") is True
        and approval.get("status") == "APPROVED"
        and approval.get("signature") == "synthetic-only-test-approval"
        and approval.get("reviewer_identity") == "synthetic test reviewer"
        and set(approval.get("documents", {})) == {
            "research/56_M4B3_PROSPECTIVE_AMENDMENT_DRAFT.md",
            "research/57_M4B3_EVALUATOR_RUBRIC_DRAFT.md",
        }
    )


def _test_reconciliation_verifier(proposal):
    """Synthetic fixture verifier used only by private local-test ledger opens."""
    return proposal.get("reviewer_identity") == "test reviewer"


def _build_run_manifest(*args, **kwargs):
    kwargs["approval_verifier"] = _test_approval_verifier
    return runner.build_run_manifest(*args, **kwargs)


def _open_fake_session(*args, **kwargs):
    kwargs["approval_verifier"] = _test_approval_verifier
    return runner._open_fake_session_for_tests(*args, **kwargs)


def _prepare_dispatch(ledger, dispatcher, exp, index=0):
    item=exp["plans"][index]
    evaluation=_eval_id(exp,index)
    attempt=ledger.allocate_attempt_id()
    prompt=(runner.SYSTEM if item["prompt"]=="current" else runner.LAYERED_PROMPT)+"\nUNTRUSTED EVIDENCE JSON:\n"+item["context"]
    schema=runner.Findings.model_json_schema() if item["schema"]=="current" else runner.LayeredFindings.model_json_schema()
    prepared=dispatcher.prepare(evaluation_id=evaluation,attempt_id=attempt,model=runner.MODEL,
                                prompt=prompt,schema=schema,model_digest=exp["config"]["model_digest"])
    ledger.begin_attempt(evaluation,attempt,prepared.request_hash,request_spec_hash(item),
                         prepared.config_sha256,prepared.body_sha256)
    permit=ledger.authorize_dispatch(evaluation,attempt,prepared.request_hash)
    return item,evaluation,attempt,prepared,permit


class _ChunkStream(httpx.SyncByteStream):
    def __init__(self,chunks,*,error_after=None):
        self.chunks=list(chunks); self.error_after=error_after
    def __iter__(self):
        for index,chunk in enumerate(self.chunks):
            yield chunk
            if self.error_after is not None and index==self.error_after:
                raise httpx.ReadError("simulated interrupted response stream")
    def close(self): pass


class _ResponseMutationTransport(httpx.BaseTransport):
    """Send once to the loopback receiver, then return a controlled response stream."""
    def __init__(self,body_chunks,*,content_length=None,include_length=True,error_after=None,
                 content_encoding=None):
        self.inner=httpx.HTTPTransport(retries=0)
        self.body_chunks=body_chunks; self.content_length=content_length
        self.include_length=include_length; self.error_after=error_after
        self.content_encoding=content_encoding
    def handle_request(self,request):
        real=self.inner.handle_request(request)
        real.read(); real.close()
        headers={"content-type":"application/json"}
        if self.content_encoding:
            headers["content-encoding"]=self.content_encoding
        if self.include_length:
            headers["content-length"]=str(self.content_length if self.content_length is not None
                                            else sum(map(len,self.body_chunks)))
        return httpx.Response(200,headers=headers,stream=_ChunkStream(self.body_chunks,error_after=self.error_after),request=request)
    def close(self): self.inner.close()


def _template_bytes():
    return json.dumps({
        "status": "template_only_no_model_calls",
        "revision": runner.PINNED_REV,
        "arms": runner.ARMS_ENVELOPE,
        "results": [],
    }, indent=2, ensure_ascii=False).encode("utf-8")


def _make_experiment(tmp_path, *, model_config=None, approval=None, fault_hook=None):
    tmp_path.mkdir(parents=True,exist_ok=True)
    db = tmp_path / "ledger.sqlite3"
    results = tmp_path / "results.json"
    lock = tmp_path / "attempt.lock"
    approval_path = tmp_path / "approval.json"
    results.write_bytes(_template_bytes())
    approval = approval or _approval_manifest()
    approval_path.write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")
    config = dict(model_config or TEST_MODEL)
    plans, revision = runner.plan()
    manifest = _build_run_manifest(plans, revision, approval, config)
    Ledger.initialize(
        db,
        plan_rows=runner.plan_rows(plans),
        manifest=manifest,
        approved_protocol_sha256=manifest["approved_protocol_sha256"],
        initial_results_sha256=hashlib.sha256(results.read_bytes()).hexdigest(),
        lock_path=lock,
        fault_hook=fault_hook,
    )
    return {"db": db, "results": results, "lock": lock, "approval": approval_path,
            "config": config, "plans": plans, "revision": revision}


def _open_session(exp, receiver, **kwargs):
    return _open_fake_session(
        exp["db"], exp["results"], exp["approval"], fake_endpoint=receiver.url,
        model_config=exp["config"], lock_path=exp["lock"], **kwargs,
    )


def _valid_output(request_payload):
    schema = request_payload["format"]
    if "static_code_facts" in schema.get("properties", {}):
        result = {
            "outcome": "INSUFFICIENT_EVIDENCE",
            "static_code_facts": [], "runtime_observations": [],
            "behavioral_contract": [], "mechanism_hypotheses": [],
            "causal_attribution": {
                "status": "NOT_ESTABLISHED", "explanation": "runtime linkage is absent",
                "evidence_ids": ["event:0"], "missing_evidence": ["missing_evidence"],
            },
            "uncertainties": [{"text": "runtime input is not recorded", "evidence_ids": ["missing_evidence"]}],
        }
    else:
        result = {
            "outcome": "INSUFFICIENT_EVIDENCE",
            "observed_failure": {"text": "the event record reports a failure", "evidence_ids": ["event:0"]},
            "observed_facts": [], "hypotheses": [], "alternatives": [],
            "missing_evidence": ["Runtime arguments and execution trace were not captured."],
            "verification_steps": ["capture authenticated runtime input and trace"],
        }
    return result


class _ReceiverHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        body_hash = hashlib.sha256(raw).hexdigest()
        attempt_id = self.headers.get("X-Blackbox-Attempt-Id", "")
        connection = sqlite3.connect(str(self.server.ledger_path), timeout=1)
        try:
            event = connection.execute(
                "SELECT event_id,payload_json FROM events WHERE event_type='DISPATCH_INTENT' AND attempt_id=?",
                (attempt_id,),
            ).fetchone()
        finally:
            connection.close()
        receipt = {
            "request_id": str(uuid.uuid4()),
            "run_id": self.headers.get("X-Blackbox-Run-Id", ""),
            "evaluation_id": self.headers.get("X-Blackbox-Evaluation-Id", ""),
            "attempt_id": attempt_id,
            "accept_encoding": self.headers.get("Accept-Encoding", ""),
            "body_sha256": body_hash,
            "body": raw.decode("utf-8", "replace"),
            "dispatch_event_id_seen_before_receipt": event[0] if event else None,
        }
        self.server.receipts.append(receipt)
        with open(self.server.receipt_path, "ab") as stream:
            stream.write(canonical_bytes(receipt) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        mode = self.server.modes.get_nowait() if not self.server.modes.empty() else {"kind": "valid"}
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        result = _valid_output(payload)
        response = {
            "message": {"content": json.dumps(result, separators=(",", ":"))},
            "done_reason": "stop", "prompt_eval_count": 7, "eval_count": 11,
            "load_duration": 100, "eval_duration": 200,
        }
        response_bytes = json.dumps(response, separators=(",", ":")).encode("utf-8")
        kind = mode.get("kind", "valid")
        if kind == "invalid_json":
            response_bytes = b"this is a complete non-json response"
        elif kind == "schema_invalid":
            response["message"]["content"] = "{}"
            response_bytes = json.dumps(response, separators=(",", ":")).encode("utf-8")
        elif kind == "length":
            response["done_reason"] = "length"
            response_bytes = json.dumps(response, separators=(",", ":")).encode("utf-8")
        elif kind == "http500":
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            try:
                self.wfile.write(response_bytes)
                self.wfile.flush()
            except OSError:
                pass
            return
        elif kind == "redirect":
            self.send_response(302)
            self.send_header("Location", "/api/chat")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        elif kind == "partial":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes) + 50))
            self.end_headers()
            self.wfile.write(response_bytes[:12])
            self.wfile.flush()
            self.close_connection = True
            self.connection.close()
            return
        elif kind == "reset":
            self.connection.shutdown(2)
            self.connection.close()
            return
        elif kind == "delayed":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.flush()
            time.sleep(float(mode.get("seconds", 1.4)))
            try:
                self.wfile.write(response_bytes)
                self.wfile.flush()
            except OSError:
                pass
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("X-Request-Id", receipt["request_id"])
        self.end_headers()
        try:
            self.wfile.write(response_bytes)
            self.wfile.flush()
        except OSError:
            pass


class FakeReceiver:
    """Independent loopback HTTP server with a separately fsynced receipt log."""

    def __init__(self, ledger_path, receipt_path, modes=()):
        self.ledger_path = Path(ledger_path)
        self.receipt_path = Path(receipt_path)
        self.receipt_path.write_bytes(b"")
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ReceiverHandler)
        self.server.daemon_threads = True
        self.server.ledger_path = self.ledger_path
        self.server.receipt_path = self.receipt_path
        self.server.receipts = []
        self.server.modes = queue.Queue()
        for mode in modes:
            self.server.modes.put(dict(mode) if isinstance(mode, dict) else {"kind": mode})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def enqueue(self, mode): self.server.modes.put(dict(mode) if isinstance(mode, dict) else {"kind": mode})
    @property
    def receipts(self): return list(self.server.receipts)
    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close()


def _history(db):
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute("SELECT seq,event_id,evaluation_id,attempt_id,event_type,payload_json FROM events ORDER BY seq").fetchall()
        return [{"seq": r[0], "event_id": r[1], "evaluation_id": r[2], "attempt_id": r[3],
                 "event_type": r[4], "payload": json.loads(r[5])} for r in rows]
    finally:
        conn.close()


def _rehash_events(conn):
    conn.execute("DROP TRIGGER IF EXISTS events_no_update")
    columns=("seq","event_id","run_id","evaluation_id","attempt_id","event_type",
             "occurred_utc","payload_json","payload_sha256","prev_event_hash")
    rows=conn.execute("SELECT seq,event_id,run_id,evaluation_id,attempt_id,event_type,occurred_utc,"
                       "payload_json,payload_sha256,prev_event_hash FROM events ORDER BY seq").fetchall()
    previous="0"*64
    for row in rows:
        event=dict(zip(columns,row)); event["prev_event_hash"]=previous
        current=ledger_module._event_hash(event)
        conn.execute("UPDATE events SET prev_event_hash=?,event_hash=? WHERE seq=?",(previous,current,event["seq"]))
        previous=current
    conn.execute("CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END")


def _state(db, lock, eid):
    with Ledger.open_existing(db, lock_path=lock) as ledger:
        state = ledger.replay_validate().states[eid]
        return state


def _run_child(target, exp, receiver=None):
    endpoint = receiver.url if receiver else "http://127.0.0.1:1"
    code = r'''
import os,sys
from pathlib import Path
from scripts.evaluate_m4b3 import _open_fake_session_for_tests,execute
target,db,results,approval,lock,endpoint,config_json=sys.argv[1:]
import json
config=json.loads(config_json)
def test_verifier(value):
    return value.get('test_only') is True and value.get('signature')=='synthetic-only-test-approval'
def hook(name):
    if name==target: os._exit(73)
session=_open_fake_session_for_tests(db,results,approval,fake_endpoint=endpoint,model_config=config,lock_path=lock,
                          checkpoint=hook,ledger_fault_hook=hook,approval_verifier=test_verifier)
with session:
    execute(session,max_evaluations=1)
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    args = [sys.executable, "-c", code, target, str(exp["db"]), str(exp["results"]),
            str(exp["approval"]), str(exp["lock"]), endpoint, json.dumps(exp["config"])]
    return subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)


def _fresh_process_summary(exp):
    code = r'''
import json,sys
from blackbox.m4b3_ledger import Ledger
db,lock=sys.argv[1:]
with Ledger.open_existing(db,lock_path=lock) as ledger:
 r=ledger.replay_validate()
 print(json.dumps({"states":{k:v.state for k,v in r.states.items()},
  "attempts":{k:v.attempt_id for k,v in r.states.items()},"events":[e["event_type"] for e in r.events]}))
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run([sys.executable, "-c", code, str(exp["db"]), str(exp["lock"])],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise AssertionError(f"fresh-process replay failed: {result.stderr}")
    return json.loads(result.stdout.strip())


def _eval_id(exp, index=0):
    item = exp["plans"][index]
    return evaluation_id(item["revision"], item["case"], item["arm"])


def _reconcile(exp, eid, disposition, *, boundary=False):
    with Ledger._open_existing_for_tests(exp["db"], lock_path=exp["lock"],
            reconciliation_verifier=_test_reconciliation_verifier) as ledger:
        state = ledger.replay_validate().states[eid]
        assert state.state in {"IN_FLIGHT", "UNKNOWN_OUTCOME"}
        ledger.reconcile(eid, state.attempt_id, reviewer_identity="test reviewer",
            disposition=disposition,
            evidence_references=[{"reference": "independent test receipt log", "sha256": "a" * 64}],
            rationale="fault-injection test disposition",
            boundary_invariant_verified=boundary)
        return state.attempt_id


def _seed_attempt(exp, index=0, *, dispatch=False, unknown=False, failed=False):
    item=exp["plans"][index]; eid=_eval_id(exp,index)
    attempt=str(uuid.uuid4()); request_hash="b"*64
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        ledger.begin_attempt(eid,attempt,request_hash,request_spec_hash(item),"c"*64)
        if dispatch:
            ledger.authorize_dispatch(eid,attempt,request_hash)
        if unknown:
            ledger.record_unknown(eid,attempt,reason="seeded ambiguous outcome")
        if failed:
            evidence=ledger._local_failure_evidence(eid,attempt,error_type="LocalValidation",error="known before transport")
            ledger.record_failed(evidence)
    return eid,attempt,request_hash


def test_schema_and_immutable_plan_create_exact_24_rows(tmp_path):
    exp=_make_experiment(tmp_path)
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        replay=ledger.replay_validate()
        assert len(ledger.plan_rows())==24
        assert len(replay.states)==24
        assert [e["event_type"] for e in replay.events].count("EVALUATION_PLANNED")==24
        assert ledger.conn.execute("PRAGMA journal_mode").fetchone()[0].lower()=="wal"
        assert ledger.conn.execute("PRAGMA synchronous").fetchone()[0]==2
        assert ledger.conn.execute("PRAGMA foreign_keys").fetchone()[0]==1
        assert ledger.conn.execute("PRAGMA busy_timeout").fetchone()[0]==5000
        with pytest.raises(sqlite3.IntegrityError):
            ledger.conn.execute("UPDATE planned_evaluations SET arm='B' WHERE ordinal=1")


def test_run_fingerprint_changes_when_execution_component_changes(tmp_path):
    exp=_make_experiment(tmp_path)
    approval=_approval_manifest(); plans,revision=runner.plan()
    changed=dict(TEST_MODEL); changed["context_tokens"]=4096
    changed_manifest=_build_run_manifest(plans,revision,approval,changed)
    assert manifest_fingerprint(changed_manifest)!=manifest_fingerprint(
        _build_run_manifest(plans,revision,approval,TEST_MODEL))
    with pytest.raises(LedgerBlocked,match="fingerprint"):
        Ledger.open_existing(exp["db"],expected_fingerprint=manifest_fingerprint(changed_manifest),lock_path=exp["lock"])


def test_request_preparation_is_stable_and_loopback_only(tmp_path):
    exp=_make_experiment(tmp_path)
    item=exp["plans"][0]; eid=_eval_id(exp); attempt=str(uuid.uuid4())
    prompt=runner.SYSTEM+'\nUNTRUSTED EVIDENCE JSON:\n'+item["context"]
    schema=runner.Findings.model_json_schema()
    with M4B3OllamaDispatcher("run-test",endpoint="http://127.0.0.1:43210") as dispatcher:
        a=dispatcher.prepare(evaluation_id=eid,attempt_id=attempt,model=runner.MODEL,prompt=prompt,schema=schema)
        b=dispatcher.prepare(evaluation_id=eid,attempt_id=attempt,model=runner.MODEL,prompt=prompt,schema=schema)
        assert a.request_hash==b.request_hash
        assert a.request.content and json.loads(a.request.content)["stream"] is False
    with pytest.raises(ProviderError): M4B3OllamaDispatcher("r",endpoint="http://example.com")
    with pytest.raises(ProviderError): M4B3OllamaDispatcher("r",endpoint="http://127.0.0.1:11434")


def test_fake_receiver_sees_committed_marker_and_completion(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipts.jsonl") as receiver:
        with _open_session(exp,receiver) as session:
            result=runner.execute(session,max_evaluations=1)
    receipt=receiver.receipts[0]
    events=_history(exp["db"])
    assert receipt["dispatch_event_id_seen_before_receipt"]
    assert receipt["body_sha256"]==hashlib.sha256(receipt["body"].encode("utf-8")).hexdigest()
    dispatch=next(e for e in events if e["event_type"]=="DISPATCH_INTENT")
    assert dispatch["payload"]["request_payload_sha256"]==receipt["body_sha256"]
    assert [e["event_type"] for e in events][-4:-1]==["IN_FLIGHT","DISPATCH_INTENT","COMPLETED"]
    assert len(result)==1 and result[0]["valid"] is True
    assert json.loads(exp["results"].read_text())["results"][0]["valid"] is True


@pytest.mark.parametrize("mode",["invalid_json","schema_invalid","length"])
def test_complete_invalid_responses_are_consumed_without_retry(tmp_path,mode):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",[mode]) as receiver:
        with _open_session(exp,receiver) as session:
            result=runner.execute(session,max_evaluations=1)
        assert len(receiver.receipts)==1
        event_types=[e["event_type"] for e in _history(exp["db"])]
        assert event_types[-2]=="COMPLETED" and event_types[-1]=="EXPORT_WRITTEN"
        state=_state(exp["db"],exp["lock"],_eval_id(exp))
        assert state.state=="COMPLETED" and state.result["valid"] is False
        with _open_session(exp,receiver) as resumed:
            runner.execute(resumed,max_evaluations=1)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1
    assert result[0]["valid"] is False


@pytest.mark.parametrize("mode",["partial","reset","http500","redirect"])
def test_ambiguous_transport_outcomes_block_and_never_resend(tmp_path,mode):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",[mode]) as receiver:
        with _open_session(exp,receiver) as session:
            with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
        event_types=[e["event_type"] for e in _history(exp["db"])]
        assert event_types[-2]=="UNKNOWN_OUTCOME" and event_types[-1]=="EXPORT_WRITTEN"
        assert len(receiver.receipts)==1
        with pytest.raises(LedgerBlocked,match="reconciliation"):
            _open_session(exp,receiver)
        _reconcile(exp,_eval_id(exp),"ACCEPTED_UNKNOWN_MISSING")
        with _open_session(exp,receiver) as resumed:
            runner.execute(resumed,max_evaluations=1)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1
    assert len(receiver.receipts)==2  # one untouched next evaluation, never the uncertain one


def test_done_reason_length_is_stored_as_invalid_completed(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",["length"]) as receiver:
        with _open_session(exp,receiver) as session: runner.execute(session,max_evaluations=1)
    events=_history(exp["db"])
    completion=events[-2]["payload"]
    assert events[-2]["event_type"]=="COMPLETED" and completion["valid"] is False
    assert len(receiver.receipts)==1


def test_http_500_preserves_body_and_is_unknown(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",["http500"]) as receiver:
        with _open_session(exp,receiver) as session:
            with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
    last=_history(exp["db"])[-2]
    assert last["event_type"]=="UNKNOWN_OUTCOME"
    assert last["payload"]["metadata"]["status_code"]==500
    metadata=last["payload"]["metadata"]
    body=base64.b64decode(metadata["raw_body_b64"],validate=True)
    assert body.startswith(b'{"message"')
    assert hashlib.sha256(body).hexdigest()==metadata["raw_body_sha256"]
    assert len(receiver.receipts)==1


def test_partial_response_body_bytes_are_retained_for_audit(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",["partial"]) as receiver:
        with _open_session(exp,receiver) as session:
            with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
    event=_history(exp["db"])[-2]
    metadata=event["payload"]["metadata"]
    body=base64.b64decode(metadata["retained_prefix_b64"],validate=True)
    assert event["event_type"]=="UNKNOWN_OUTCOME"
    assert len(body)==12
    assert hashlib.sha256(body).hexdigest()==metadata["retained_prefix_sha256"]


@pytest.mark.parametrize("checkpoint,expected_last,receipt_count",[
    ("before_in_flight_insert","EVALUATION_PLANNED",0),
    ("after_in_flight_commit","IN_FLIGHT",0),
    ("after_dispatch_intent_commit","DISPATCH_INTENT",0),
    ("before_transport","DISPATCH_INTENT",0),
    ("after_receiver_receipt","DISPATCH_INTENT",1),
    ("during_completion_transaction","DISPATCH_INTENT",1),
    ("after_completion_commit","COMPLETED",1),
    ("after_json_replace_before_export_event","COMPLETED",1),
])
def test_child_process_termination_and_fresh_process_recovery(tmp_path,checkpoint,expected_last,receipt_count):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        child=_run_child(checkpoint,exp,receiver)
        assert child.returncode==73,child.stderr
        assert len(receiver.receipts)==receipt_count
        summary=_fresh_process_summary(exp)
        eid=_eval_id(exp)
        if checkpoint in {"before_in_flight_insert"}:
            assert summary["states"][eid]=="PLANNED"
        elif checkpoint=="after_in_flight_commit":
            assert summary["states"][eid]=="IN_FLIGHT"
        elif checkpoint in {"after_completion_commit","after_json_replace_before_export_event"}:
            assert summary["states"][eid]=="COMPLETED"
        else:
            assert summary["states"][eid]=="UNKNOWN_OUTCOME"
        assert expected_last in summary["events"]
        if checkpoint=="after_in_flight_commit":
            attempt=summary["attempts"][eid]
            _reconcile(exp,eid,"CONFIRMED_NOT_DISPATCHED",boundary=True)
            with _open_session(exp,receiver) as resumed: runner.execute(resumed,max_evaluations=1)
            assert _state(exp["db"],exp["lock"],eid).attempt_id==attempt
            assert len([r for r in receiver.receipts if r["evaluation_id"]==eid])==1
        elif checkpoint in {"after_completion_commit","after_json_replace_before_export_event"}:
            with _open_session(exp,receiver) as resumed: runner.execute(resumed,max_evaluations=1)
            assert len([r for r in receiver.receipts if r["evaluation_id"]==eid])==1
        elif checkpoint in {"after_dispatch_intent_commit","before_transport","after_receiver_receipt","during_completion_transaction"}:
            with pytest.raises(LedgerBlocked): _open_session(exp,receiver)
            _reconcile(exp,eid,"ACCEPTED_UNKNOWN_MISSING")
            with _open_session(exp,receiver) as resumed: runner.execute(resumed,max_evaluations=1)
            assert len([r for r in receiver.receipts if r["evaluation_id"]==eid])==receipt_count


def test_timeout_after_receiver_receipt_is_unknown(tmp_path):
    config=dict(TEST_MODEL); config["provider_timeout_seconds"]=1
    exp=_make_experiment(tmp_path,model_config=config)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",[{"kind":"delayed","seconds":1.5}]) as receiver:
        with _open_session(exp,receiver) as session:
            with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
    assert len(receiver.receipts)==1
    state=_state(exp["db"],exp["lock"],_eval_id(exp))
    assert state.state=="UNKNOWN_OUTCOME"
    assert [e["event_type"] for e in _history(exp["db"])][-2]=="UNKNOWN_OUTCOME"


def test_result_insert_failure_rolls_back_and_never_retries(tmp_path):
    exp=_make_experiment(tmp_path)
    def fault(name):
        if name=="during_completion_transaction": raise sqlite3.OperationalError("disk is full")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver,ledger_fault_hook=fault) as session:
            with pytest.raises(sqlite3.OperationalError): runner.execute(session,max_evaluations=1)
        assert len(receiver.receipts)==1
        state=_state(exp["db"],exp["lock"],_eval_id(exp))
        assert state.state=="UNKNOWN_OUTCOME"
        with pytest.raises(LedgerBlocked): _open_session(exp,receiver)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1


def test_in_flight_write_failure_sends_nothing_and_leaves_plan_untouched(tmp_path):
    exp=_make_experiment(tmp_path)
    def disk_full(checkpoint):
        if checkpoint=="before_in_flight_insert":
            raise sqlite3.OperationalError("database or disk is full")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver,ledger_fault_hook=disk_full) as session:
            with pytest.raises(sqlite3.OperationalError,match="disk is full"):
                runner.execute(session,max_evaluations=1)
    assert _history(exp["db"])[-1]["event_type"]=="EVALUATION_PLANNED"
    assert receiver.receipts==[]


def test_completion_commit_ack_ambiguity_recovers_completed(tmp_path):
    exp=_make_experiment(tmp_path)
    commit_count={"value":0}
    def fault(name):
        if name=="after_commit":
            commit_count["value"]+=1
            if commit_count["value"]==3: raise OSError("simulated lost completion commit acknowledgment")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver,ledger_fault_hook=fault) as session:
            with pytest.raises(CommitAmbiguous): runner.execute(session,max_evaluations=1)
        assert len(receiver.receipts)==1
        summary=_fresh_process_summary(exp)
        assert summary["states"][_eval_id(exp)]=="COMPLETED"
        with _open_session(exp,receiver) as resumed: runner.execute(resumed,max_evaluations=1)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1


def test_export_failure_keeps_completion_and_retries_export_only(tmp_path,monkeypatch):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver) as session:
            monkeypatch.setattr("blackbox.m4b3_ledger.os.replace",lambda *a,**k: (_ for _ in ()).throw(PermissionError("denied")))
            with pytest.raises(PermissionError): runner.execute(session,max_evaluations=1)
        monkeypatch.undo()
        assert len(receiver.receipts)==1
        assert _state(exp["db"],exp["lock"],_eval_id(exp)).state=="COMPLETED"
        with _open_session(exp,receiver) as resumed: runner.execute(resumed,max_evaluations=1)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1
    assert len(receiver.receipts)==2


def test_missing_ledger_and_nonempty_json_are_preserved(tmp_path):
    db=tmp_path/"absent.sqlite3"; results=tmp_path/"results.json"; approval=tmp_path/"approval.json"
    results.write_text('{"results":[{"user":"keep"}]}',encoding="utf8")
    approval.write_text(json.dumps(_approval_manifest()),encoding="utf8")
    with FakeReceiver(tmp_path/"not-used.sqlite3",tmp_path/"receipt.jsonl") as receiver:
        with pytest.raises(LedgerBlocked,match="existing attempt ledger"):
            _open_fake_session(db,results,approval,fake_endpoint=receiver.url,
                                     model_config=TEST_MODEL,lock_path=tmp_path/"lock")
        assert results.read_text(encoding="utf8")== '{"results":[{"user":"keep"}]}'
        assert not db.exists() and len(receiver.receipts)==0


def test_corrupt_database_and_bad_sidecar_fail_closed(tmp_path):
    exp=_make_experiment(tmp_path)
    # Preserve and test a deliberately corrupt copy; no recovery path creates a replacement.
    exp["db"].write_bytes(b"not a sqlite database")
    with pytest.raises(LedgerBlocked): Ledger.open_existing(exp["db"],lock_path=exp["lock"])
    assert exp["db"].read_bytes()==b"not a sqlite database"
    other=_make_experiment(tmp_path/"other")
    Path(str(other["db"])+"-wal").write_bytes(b"invalid-wal")
    with pytest.raises(LedgerBlocked): Ledger.open_existing(other["db"],lock_path=other["lock"])
    assert Path(str(other["db"])+"-wal").read_bytes()==b"invalid-wal"


def test_missing_wal_sidecar_is_normalized_by_sqlite_recovery(tmp_path):
    exp=_make_experiment(tmp_path)
    assert not Path(str(exp["db"])+"-wal").exists()
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        assert ledger.replay_validate().last_seq==25


def test_duplicate_evaluation_duplicate_attempt_and_budget_are_rejected(tmp_path):
    exp=_make_experiment(tmp_path)
    rows=runner.plan_rows(exp["plans"])
    duplicate=list(rows); duplicate[-1]=dict(duplicate[0],ordinal=24)
    with pytest.raises(LedgerBlocked):
        Ledger.initialize(tmp_path/"duplicate.sqlite3",plan_rows=duplicate,
          manifest={"fingerprint_inputs":{}},approved_protocol_sha256="a"*64,
          initial_results_sha256="b"*64,lock_path=tmp_path/"dup.lock")
    too_many=rows+[dict(rows[-1],ordinal=25,evaluation_id="overflow")]
    with pytest.raises(LedgerBlocked,match="exactly 24"):
        Ledger.initialize(tmp_path/"overflow.sqlite3",plan_rows=too_many,
          manifest={"fingerprint_inputs":{}},approved_protocol_sha256="a"*64,
          initial_results_sha256="b"*64,lock_path=tmp_path/"overflow.lock")
    item=exp["plans"][0]; eid=_eval_id(exp)
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        attempt=str(uuid.uuid4())
        ledger.begin_attempt(eid,attempt,"d"*64,request_spec_hash(item),"e"*64)
        with pytest.raises(LedgerBlocked): ledger.begin_attempt(eid,str(uuid.uuid4()),"f"*64,request_spec_hash(item),"e"*64)
        # Same attempt ID cannot be attached to another evaluation.
        with pytest.raises(sqlite3.IntegrityError): ledger.begin_attempt(_eval_id(exp,1),attempt,"1"*64,
                                                       request_spec_hash(exp["plans"][1]),"e"*64)
    assert [e["event_type"] for e in _history(exp["db"])].count("IN_FLIGHT")==1


def test_pre_dispatch_reconciliation_reuses_same_attempt_id(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        item=exp["plans"][0]; eid=_eval_id(exp); attempt=str(uuid.uuid4())
        prompt=runner.SYSTEM+'\nUNTRUSTED EVIDENCE JSON:\n'+item["context"]
        schema=runner.Findings.model_json_schema()
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url,
                    timeout_seconds=exp["config"]["provider_timeout_seconds"]) as dispatcher:
                prepared=dispatcher.prepare(evaluation_id=eid,attempt_id=attempt,model=runner.MODEL,
                    prompt=prompt,schema=schema,model_digest=exp["config"]["model_digest"])
            ledger.begin_attempt(eid,attempt,prepared.request_hash,request_spec_hash(item),prepared.config_sha256,
                                 prepared.body_sha256)
        assert _state(exp["db"],exp["lock"],eid).state=="IN_FLIGHT"
        with pytest.raises(LedgerBlocked): _open_session(exp,receiver)
        same=_reconcile(exp,eid,"CONFIRMED_NOT_DISPATCHED",boundary=True)
        assert same==attempt
        with _open_session(exp,receiver) as session: runner.execute(session,max_evaluations=1)
    assert len(receiver.receipts)==1 and receiver.receipts[0]["attempt_id"]==attempt
    assert [e["event_type"] for e in _history(exp["db"])].count("IN_FLIGHT")==1


def test_not_dispatched_reconciliation_after_dispatch_is_rejected(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,attempt,_=_seed_attempt(exp,dispatch=True,unknown=True)
    with Ledger._open_existing_for_tests(exp["db"],lock_path=exp["lock"],
            reconciliation_verifier=_test_reconciliation_verifier) as ledger:
        before=ledger.replay_validate().last_seq
        with pytest.raises(LedgerBlocked):
            ledger.reconcile(eid,attempt,reviewer_identity="reviewer",disposition="CONFIRMED_NOT_DISPATCHED",
              evidence_references=[{"reference":"missing receiver log","sha256":"a"*64}],
              rationale="attempt to replay",boundary_invariant_verified=True)
        assert ledger.replay_validate().last_seq==before


def test_replay_completed_failed_and_unknown_states(tmp_path):
    exp=_make_experiment(tmp_path)
    eid0,_,_=_seed_attempt(exp,0,dispatch=True)
    eid1,_,_=_seed_attempt(exp,1,failed=True)
    eid2,_,_=_seed_attempt(exp,2,dispatch=True,unknown=True)
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        states=ledger.replay_validate().states
        assert states[eid0].state=="UNKNOWN_OUTCOME"  # D without a terminal event derives unknown.
        assert states[eid1].state=="FAILED"
        assert states[eid2].state=="UNKNOWN_OUTCOME"


def test_failed_writer_rejects_self_asserted_flags_before_appending(tmp_path):
    exp=_make_experiment(tmp_path)
    in_flight_eid,in_flight_attempt,_=_seed_attempt(exp,0)
    dispatched_eid,dispatched_attempt,_=_seed_attempt(exp,1,dispatch=True)
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        before=ledger.replay_validate().last_seq
        with pytest.raises(TypeError):
            ledger.record_failed(in_flight_eid,in_flight_attempt,error_type="Injected",error="no proof",
                                no_dispatch_proof=True,definitive_provider_failure=True)
        with pytest.raises(LedgerBlocked,match="local failure evidence"):
            ledger._local_failure_evidence(dispatched_eid,dispatched_attempt,error_type="Injected",error="after dispatch")
        assert ledger.replay_validate().last_seq==before


def test_failed_after_dispatch_requires_explicit_confirmed_failed_reconciliation(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,attempt,_=_seed_attempt(exp,dispatch=True,unknown=True)
    _reconcile(exp,eid,"CONFIRMED_FAILED")
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        with pytest.raises(LedgerBlocked,match="explicit matching reconciliation"):
            ledger._confirmed_failure_evidence(_eval_id(exp,1),attempt,error_type="Injected",error="no approval")
        evidence=ledger._confirmed_failure_evidence(eid,attempt,error_type="ReviewedFailure",error="independent proof")
        ledger.record_failed(evidence)
        assert ledger.replay_validate().states[eid].state=="FAILED"


def test_dispatch_permit_is_atomic_under_two_simultaneous_consumers(tmp_path):
    exp=_make_experiment(tmp_path)
    item=exp["plans"][0]; eid=_eval_id(exp); attempt=str(uuid.uuid4())
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger._open_existing_for_tests(exp["db"],lock_path=exp["lock"],
                reconciliation_verifier=_test_reconciliation_verifier) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                prompt=runner.SYSTEM+'\nUNTRUSTED EVIDENCE JSON:\n'+item["context"]
                prepared=dispatcher.prepare(evaluation_id=eid,attempt_id=attempt,model=runner.MODEL,
                    prompt=prompt,schema=runner.Findings.model_json_schema())
                ledger.begin_attempt(eid,attempt,prepared.request_hash,request_spec_hash(item),prepared.config_sha256,
                                     prepared.body_sha256)
                permit=ledger.authorize_dispatch(eid,attempt,prepared.request_hash)
                outcomes=[]; errors=[]; barrier=threading.Barrier(3)
                def send():
                    barrier.wait()
                    try: outcomes.append(dispatcher.send_prepared(prepared,permit))
                    except Exception as exc: errors.append(exc)
                threads=[threading.Thread(target=send) for _ in range(2)]
                for t in threads: t.start()
                barrier.wait()
                for t in threads: t.join(timeout=5)
                assert len(outcomes)==1 and len(errors)==1 and isinstance(errors[0],LedgerBlocked)
        # Ledger close releases the writer lock before independent inspection.
        assert len(receiver.receipts)==1
        assert receiver.receipts[0]["dispatch_event_id_seen_before_receipt"]


def test_database_constraints_bound_dispatch_and_response_identity(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,attempt,request_hash=_seed_attempt(exp,dispatch=True)
    with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
        with pytest.raises(sqlite3.IntegrityError):
            ledger.conn.execute("INSERT INTO events(event_id,run_id,evaluation_id,attempt_id,event_type,occurred_utc,payload_json,payload_sha256,prev_event_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4()),ledger.run_id,eid,attempt,"DISPATCH_INTENT","2026-11-07T00:00:00Z","{}","a"*64,"b"*64,"c"*64))
    assert [e["event_type"] for e in _history(exp["db"])].count("DISPATCH_INTENT")==1


def test_fingerprint_mismatch_blocks_before_dispatcher_construction(tmp_path,monkeypatch):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        monkeypatch.setattr(runner,"M4B3OllamaDispatcher",lambda *a,**k: pytest.fail("dispatcher constructed before fingerprint check"))
        changed=dict(TEST_MODEL); changed["context_tokens"]=4096
        with pytest.raises(LedgerBlocked,match="fingerprint"):
            _open_fake_session(exp["db"],exp["results"],exp["approval"],fake_endpoint=receiver.url,
                                     model_config=changed,lock_path=exp["lock"])
        assert not receiver.receipts


def test_unknown_results_json_is_preserved_and_blocks(tmp_path):
    exp=_make_experiment(tmp_path)
    exp["results"].write_text('{"manual":"keep exactly"}',encoding="utf8")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with pytest.raises(LedgerBlocked,match="unknown contents"):
            _open_session(exp,receiver)
        assert exp["results"].read_text(encoding="utf8")== '{"manual":"keep exactly"}'
        assert not receiver.receipts


def test_pre_transport_request_construction_failure_has_no_attempt(tmp_path):
    exp=_make_experiment(tmp_path)
    with M4B3OllamaDispatcher("run",endpoint="http://127.0.0.1:43124") as dispatcher:
        with pytest.raises(ProviderError):
            dispatcher.prepare(evaluation_id=_eval_id(exp),attempt_id=str(uuid.uuid4()),model=runner.MODEL,
                prompt="x"*100000,schema=runner.Findings.model_json_schema(),context_length=1024)
    assert [e["event_type"] for e in _history(exp["db"])][-1]=="EVALUATION_PLANNED"


def test_dispatch_marker_commit_ambiguity_never_enters_transport(tmp_path):
    exp=_make_experiment(tmp_path)
    def fault(name):
        if name=="after_dispatch_intent_commit": raise OSError("lost marker acknowledgment")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver,ledger_fault_hook=fault) as session:
            with pytest.raises(OSError): runner.execute(session,max_evaluations=1)
        assert len(receiver.receipts)==0
        summary=_fresh_process_summary(exp)
        assert summary["states"][_eval_id(exp)]=="UNKNOWN_OUTCOME"
        with pytest.raises(LedgerBlocked): _open_session(exp,receiver)
    assert len(receiver.receipts)==0


def test_stale_recognized_json_is_rebuilt_from_committed_ledger(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver) as session: runner.execute(session,max_evaluations=1)
        # Initial template hash remains recognized even though it is stale.
        exp["results"].write_bytes(_template_bytes())
        with _open_session(exp,receiver) as resumed:
            assert len(json.loads(exp["results"].read_text())["results"])==1
            assert not any(e["event_type"]=="IN_FLIGHT" for e in _history(exp["db"])[-1:])
            runner.execute(resumed,max_evaluations=1)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1


def test_export_replace_crash_window_records_hash_without_resend(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        child=_run_child("after_json_replace_before_export_event",exp,receiver)
        assert child.returncode==73
        events=_history(exp["db"])
        assert events[-1]["event_type"]=="COMPLETED"  # replacement happened; export event did not.
        assert len(receiver.receipts)==1
        with _open_session(exp,receiver) as resumed:
            assert _history(exp["db"])[-1]["event_type"]=="EXPORT_WRITTEN"
            runner.execute(resumed,max_evaluations=1)
    assert len([r for r in receiver.receipts if r["evaluation_id"]==_eval_id(exp)])==1


def test_initialization_crash_is_atomic_and_never_calls_receiver(tmp_path):
    exp=_make_experiment(tmp_path)
    crashed_db=tmp_path/"crash-init.sqlite3"; crashed_lock=tmp_path/"crash-init.lock"
    plan_rows=runner.plan_rows(exp["plans"])
    manifest=_build_run_manifest(exp["plans"],exp["revision"],_approval_manifest(),TEST_MODEL)
    code=r'''
import os,sys,json
from blackbox.m4b3_ledger import Ledger
from scripts.evaluate_m4b3 import plan_rows
from pathlib import Path
from scripts.evaluate_m4b3 import plan,build_run_manifest,validate_approval_manifest
db,lock,approval_path=sys.argv[1:]
def test_verifier(value):
 return value.get('test_only') is True and value.get('signature')=='synthetic-only-test-approval'
plans,rev=plan(); approval=json.loads(Path(approval_path).read_text()); manifest=build_run_manifest(plans,rev,approval,approval_verifier=test_verifier)
def hook(name):
 if name=="during_initialization": os._exit(73)
Ledger.initialize(db,plan_rows=plan_rows(plans),manifest=manifest,
 approved_protocol_sha256=manifest["approved_protocol_sha256"],initial_results_sha256="a"*64,
 lock_path=lock,fault_hook=hook)
'''
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT)+os.pathsep+env.get("PYTHONPATH","")
    child=subprocess.run([sys.executable,"-c",code,str(crashed_db),str(crashed_lock),str(exp["approval"])],
                         cwd=ROOT,env=env,capture_output=True,text=True,timeout=15)
    assert child.returncode==73 and crashed_db.exists()
    with pytest.raises(LedgerBlocked): Ledger.open_existing(crashed_db,lock_path=crashed_lock)


def test_windows_or_posix_lock_excludes_second_process_and_survives_stale_path(tmp_path):
    lock_path=tmp_path/"stable.lock"; ready=tmp_path/"ready.txt"
    owner_code=r'''
import sys,time
from pathlib import Path
from blackbox.m4b3_ledger import RunLock
p,ready=sys.argv[1:]
with RunLock(p):
 Path(ready).write_text("held")
 time.sleep(30)
'''
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT)+os.pathsep+env.get("PYTHONPATH","")
    owner=subprocess.Popen([sys.executable,"-c",owner_code,str(lock_path),str(ready)],cwd=ROOT,env=env)
    try:
        deadline=time.time()+8
        while time.time()<deadline and not ready.exists(): time.sleep(.05)
        assert ready.exists()
        assert lock_path.exists()
        contender_code=r'''
import sys
from blackbox.m4b3_ledger import RunLock,LockUnavailable
try:
 with RunLock(sys.argv[1]): print("acquired")
except LockUnavailable: print("blocked")
'''
        result=subprocess.run([sys.executable,"-c",contender_code,str(lock_path)],cwd=ROOT,env=env,
                              capture_output=True,text=True,timeout=8)
        assert result.stdout.strip()=="blocked"
        owner.terminate(); owner.wait(timeout=8)
        assert lock_path.exists()  # release never deletes/replaces the stable path.
        again=subprocess.run([sys.executable,"-c",contender_code,str(lock_path)],cwd=ROOT,env=env,
                             capture_output=True,text=True,timeout=8)
        assert again.stdout.strip()=="acquired"
    finally:
        if owner.poll() is None: owner.kill(); owner.wait(timeout=5)


def test_two_runner_processes_contend_before_dispatcher_and_recover_owner_lock(tmp_path):
    exp=_make_experiment(tmp_path)
    config_path=tmp_path/"model-config.json"
    config_path.write_text(json.dumps(exp["config"]),encoding="utf-8")
    ready=tmp_path/"owner-session-open.txt"
    marker=tmp_path/"dispatcher-constructed.txt"
    owner_code=r'''
import json,sys,time
from pathlib import Path
from scripts import evaluate_m4b3 as runner
db,results,approval,lock,endpoint,config_path,ready=sys.argv[1:]
def test_verifier(value): return value.get('test_only') is True and value.get('signature')=='synthetic-only-test-approval'
session=runner._open_fake_session_for_tests(db,results,approval,fake_endpoint=endpoint,
  model_config=json.loads(Path(config_path).read_text()),lock_path=lock,approval_verifier=test_verifier)
Path(ready).write_text("open")
time.sleep(60)
session.close()
'''
    contender_code=r'''
import json,sys
from pathlib import Path
from blackbox.m4b3_ledger import LockUnavailable
from scripts import evaluate_m4b3 as runner
db,results,approval,lock,endpoint,config_path,marker=sys.argv[1:]
def forbidden(*args,**kwargs):
 Path(marker).write_text("constructed")
 raise RuntimeError("dispatcher must not be constructed")
runner.M4B3OllamaDispatcher=forbidden
def test_verifier(value): return value.get('test_only') is True and value.get('signature')=='synthetic-only-test-approval'
try:
 runner._open_fake_session_for_tests(db,results,approval,fake_endpoint=endpoint,
   model_config=json.loads(Path(config_path).read_text()),lock_path=lock,approval_verifier=test_verifier)
except LockUnavailable:
 print("blocked")
'''
    reopen_code=r'''
import json,sys
from pathlib import Path
from scripts import evaluate_m4b3 as runner
db,results,approval,lock,endpoint,config_path=sys.argv[1:]
def test_verifier(value): return value.get('test_only') is True and value.get('signature')=='synthetic-only-test-approval'
with runner._open_fake_session_for_tests(db,results,approval,fake_endpoint=endpoint,
  model_config=json.loads(Path(config_path).read_text()),lock_path=lock,approval_verifier=test_verifier):
 print("acquired")
'''
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT)+os.pathsep+env.get("PYTHONPATH","")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        owner=subprocess.Popen([sys.executable,"-c",owner_code,str(exp["db"]),str(exp["results"]),
          str(exp["approval"]),str(exp["lock"]),receiver.url,str(config_path),str(ready)],
          cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.time()+15
            while time.time()<deadline and not ready.exists() and owner.poll() is None:
                time.sleep(.05)
            assert ready.exists(),owner.stderr.read() if owner.poll() is not None else "owner did not acquire the run lock"
            contender=subprocess.run([sys.executable,"-c",contender_code,str(exp["db"]),str(exp["results"]),
              str(exp["approval"]),str(exp["lock"]),receiver.url,str(config_path),str(marker)],
              cwd=ROOT,env=env,capture_output=True,text=True,timeout=15)
            assert contender.returncode==0,contender.stderr
            assert contender.stdout.strip()=="blocked"
            assert not marker.exists()
            owner.terminate(); owner.wait(timeout=10)
            assert (tmp_path/"attempt.lock").exists()
            reopened=subprocess.run([sys.executable,"-c",reopen_code,str(exp["db"]),str(exp["results"]),
              str(exp["approval"]),str(exp["lock"]),receiver.url,str(config_path)],
              cwd=ROOT,env=env,capture_output=True,text=True,timeout=15)
            assert reopened.returncode==0,reopened.stderr
            assert reopened.stdout.strip()=="acquired"
        finally:
            if owner.poll() is None:
                owner.kill(); owner.wait(timeout=5)


def test_live_cli_is_hard_disabled_before_plan_provider_or_network(monkeypatch):
    monkeypatch.setenv("BLACKBOX_ENABLE_LIVE","true")
    monkeypatch.setattr("sys.argv",["evaluate_m4b3.py","--run-live"])
    monkeypatch.setattr(runner,"plan",lambda: pytest.fail("plan called before live guard"))
    monkeypatch.setattr(runner,"verify_local_model",lambda: pytest.fail("Ollama preflight called"))
    with pytest.raises(SystemExit,match="live execution is disabled"):
        runner.main()


def test_fake_cli_defaults_lock_beside_temporary_ledger(monkeypatch,tmp_path):
    ledger=tmp_path/"fake.sqlite3"; results=tmp_path/"fake-results.json"
    approval=tmp_path/"approval.json"; captured={}
    class FakeSession:
        def __enter__(self): return self
        def __exit__(self,*args): pass
    def fake_open(*args,**kwargs):
        captured.update(kwargs)
        return FakeSession()
    monkeypatch.setattr("sys.argv",["evaluate_m4b3.py","--run-fake",
      "--ledger-path",str(ledger),"--results-path",str(results),
      "--approval-manifest",str(approval),"--fake-endpoint","http://127.0.0.1:49123"])
    monkeypatch.setattr(runner,"open_fake_session",fake_open)
    monkeypatch.setattr(runner,"execute",lambda session: [])
    runner.main()
    assert captured["lock_path"]==ledger.with_suffix(".lock").resolve()


def test_real_initialization_refuses_unapproved_documents_without_creating_db(tmp_path):
    results=tmp_path/"results.json"; results.write_bytes(_template_bytes())
    with pytest.raises(LedgerBlocked,match="real M4B.3 initialization is disabled"):
        runner.initialize_experiment(tmp_path/"real.sqlite3",results,None,lock_path=tmp_path/"lock")
    assert not (tmp_path/"real.sqlite3").exists()


def test_hash_chain_tampering_blocks_replay(tmp_path):
    exp=_make_experiment(tmp_path)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP TRIGGER events_no_update")
    conn.execute("UPDATE events SET payload_json='{}' WHERE seq=2")
    conn.execute("CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END")
    conn.commit(); conn.close()
    with pytest.raises(LedgerBlocked): Ledger.open_existing(exp["db"],lock_path=exp["lock"])


def test_plan_table_event_history_disagreement_blocks_replay(tmp_path):
    exp=_make_experiment(tmp_path)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP TRIGGER plan_no_update")
    conn.execute("UPDATE planned_evaluations SET case_id='changed' WHERE ordinal=1")
    conn.execute("CREATE TRIGGER plan_no_update BEFORE UPDATE ON planned_evaluations BEGIN SELECT RAISE(ABORT,'registered plan is immutable'); END")
    conn.commit(); conn.close()
    with pytest.raises(LedgerBlocked): Ledger.open_existing(exp["db"],lock_path=exp["lock"])


def test_invalid_attempt_id_attached_to_rehashed_event_blocks_replay(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,attempt,_=_seed_attempt(exp,dispatch=True)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP TRIGGER events_no_update")
    conn.execute("UPDATE events SET attempt_id=? WHERE event_type='DISPATCH_INTENT'",("not-the-original-attempt",))
    rows=conn.execute("SELECT seq,event_id,run_id,evaluation_id,attempt_id,event_type,occurred_utc,payload_json,payload_sha256,prev_event_hash FROM events ORDER BY seq").fetchall()
    from blackbox.m4b3_ledger import _event_hash
    previous="0"*64
    for row in rows:
        record=dict(zip(("seq","event_id","run_id","evaluation_id","attempt_id","event_type","occurred_utc","payload_json","payload_sha256","prev_event_hash"),row))
        record["prev_event_hash"]=previous
        event_hash=_event_hash(record)
        conn.execute("UPDATE events SET prev_event_hash=?,event_hash=? WHERE seq=?",(previous,event_hash,row[0]))
        previous=event_hash
    conn.execute("CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END")
    conn.commit(); conn.close()
    with pytest.raises(LedgerBlocked,match="attempt ID"):
        Ledger.open_existing(exp["db"],lock_path=exp["lock"])


@pytest.mark.parametrize("tamper",["request_hash","plan_hash","payload_hash"])
def test_request_and_plan_fingerprint_tampering_blocks(tmp_path,tamper):
    exp=_make_experiment(tmp_path)
    eid,attempt,_=_seed_attempt(exp,dispatch=True)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP TRIGGER events_no_update")
    if tamper=="payload_hash":
        conn.execute("UPDATE events SET payload_sha256=? WHERE event_type='IN_FLIGHT'",("f"*64,))
    elif tamper=="request_hash":
        row=conn.execute("SELECT seq,payload_json FROM events WHERE event_type='DISPATCH_INTENT'").fetchone()
        payload=json.loads(row[1]); payload["request_hash"]="9"*64
        conn.execute("UPDATE events SET payload_json=?,payload_sha256=? WHERE seq=?",
          (json.dumps(payload,sort_keys=True,separators=(",",":")),hashlib.sha256(canonical_bytes(payload)).hexdigest(),row[0]))
    else:
        row=conn.execute("SELECT seq,payload_json FROM events WHERE event_type='EVALUATION_PLANNED' LIMIT 1").fetchone()
        payload=json.loads(row[1]); payload["plan_sha256"]="8"*64
        conn.execute("UPDATE events SET payload_json=?,payload_sha256=? WHERE seq=?",
          (json.dumps(payload,sort_keys=True,separators=(",",":")),hashlib.sha256(canonical_bytes(payload)).hexdigest(),row[0]))
    conn.execute("CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END")
    conn.commit(); conn.close()
    with pytest.raises(LedgerBlocked): Ledger.open_existing(exp["db"],lock_path=exp["lock"])


def test_known_pretransport_validation_failure_does_not_write_or_send(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with M4B3OllamaDispatcher("run",endpoint=receiver.url) as dispatcher:
            with pytest.raises(ProviderError):
                dispatcher.prepare(evaluation_id=_eval_id(exp),attempt_id=str(uuid.uuid4()),model=runner.MODEL,
                    prompt="x"*100000,schema=runner.Findings.model_json_schema(),context_length=1024)
        assert not receiver.receipts
    assert [e["event_type"] for e in _history(exp["db"])][-1]=="EVALUATION_PLANNED"


def test_unknown_missing_reconciliation_allows_only_untouched_next_evaluation(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,_,_=_seed_attempt(exp,dispatch=True,unknown=True)
    _reconcile(exp,eid,"ACCEPTED_UNKNOWN_MISSING")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver) as session: runner.execute(session,max_evaluations=1)
    events=_history(exp["db"])
    assert events[-1]["event_type"]=="EXPORT_WRITTEN"
    assert len(receiver.receipts)==1 and receiver.receipts[0]["evaluation_id"]!=eid
    assert _state(exp["db"],exp["lock"],eid).state=="UNKNOWN_OUTCOME"


@pytest.mark.parametrize("component",["approval","implementation","request","model"])
def test_individual_fingerprint_inputs_are_resume_blocking(tmp_path,component):
    exp=_make_experiment(tmp_path)
    manifest=_build_run_manifest(exp["plans"],exp["revision"],_approval_manifest(),TEST_MODEL)
    changed=json.loads(json.dumps(manifest))
    if component=="approval": changed["fingerprint_inputs"]["approved_protocol_sha256"]="0"*64
    elif component=="implementation": changed["fingerprint_inputs"]["runner_provider_and_schema_code_sha256"]["blackbox/providers.py"]="0"*64
    elif component=="request": changed["fingerprint_inputs"]["request_payload_sha256"][_eval_id(exp)]="0"*64
    else: changed["fingerprint_inputs"]["model_config"]["model_digest"]="0"*64
    with pytest.raises(LedgerBlocked,match="fingerprint"):
        Ledger.open_existing(exp["db"],expected_fingerprint=manifest_fingerprint(changed),lock_path=exp["lock"])


def test_attempt_replay_after_failed_terminal_never_dispatches(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,_,_=_seed_attempt(exp,failed=True)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver) as session: runner.execute(session,max_evaluations=1)
    assert not [r for r in receiver.receipts if r["evaluation_id"]==eid]
    assert _state(exp["db"],exp["lock"],eid).state=="FAILED"


def test_forged_legacy_permit_and_dispatch_without_database_never_send(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with M4B3OllamaDispatcher("no-ledger-run",endpoint=receiver.url) as dispatcher:
            prepared=dispatcher.prepare(evaluation_id=_eval_id(exp),attempt_id="forged-attempt",
                model=runner.MODEL,prompt="offline only",schema={"type":"object"})
            legacy_issuer=getattr(ledger_module,"_PERMIT_ISSUER",None)
            assert legacy_issuer is None
            with pytest.raises(LedgerBlocked):
                DispatchPermit("no-ledger-run",prepared.evaluation_id,prepared.attempt_id,
                               prepared.request_hash,"fabricated-event",legacy_issuer)
            forged=object.__new__(DispatchPermit)
            with pytest.raises(LedgerBlocked): dispatcher.send_prepared(prepared,forged)
    assert receiver.receipts==[]


def test_permit_event_attempt_request_body_and_config_mismatches_never_send(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp,0)
                _,other_eid,other_attempt,other_prepared,other_permit=_prepare_dispatch(ledger,dispatcher,exp,1)
                mutations=[
                    (permit,"dispatch_event_id","fabricated-event"),
                    (permit,"dispatch_event_id",other_permit.dispatch_event_id),
                    (permit,"evaluation_id",other_eid),
                    (permit,"attempt_id",other_attempt),
                    (permit,"request_hash","f"*64),
                    (permit,"run_id","other-run"),
                    (prepared,"config_sha256","e"*64),
                    (prepared,"body_sha256","d"*64),
                    (prepared,"request_hash","c"*64),
                ]
                for target,field,value in mutations:
                    original=getattr(target,field)
                    object.__setattr__(target,field,value)
                    with pytest.raises(LedgerBlocked): dispatcher.send_prepared(prepared,permit)
                    object.__setattr__(target,field,original)
                assert ledger.replay_validate().states[eid].state=="UNKNOWN_OUTCOME"
                assert ledger.replay_validate().states[other_eid].state=="UNKNOWN_OUTCOME"
    assert receiver.receipts==[]


def test_missing_dispatch_history_blocks_permit_and_preserves_database(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,_,_,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                conn=sqlite3.connect(str(exp["db"]))
                conn.execute("DROP TRIGGER events_no_delete")
                conn.execute("DELETE FROM events WHERE event_id=?",(permit.dispatch_event_id,))
                conn.execute("CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'event history is append-only'); END")
                conn.commit(); conn.close()
                with pytest.raises(LedgerBlocked): dispatcher.send_prepared(prepared,permit)
    assert receiver.receipts==[]
    assert not any(event["event_id"]==permit.dispatch_event_id for event in _history(exp["db"]))


def test_valid_permit_is_single_use_and_receiver_sees_exactly_one_request(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                outcome=dispatcher.send_prepared(prepared,permit)
                assert permit.consumed and outcome.response_receipt is not None
                with pytest.raises(LedgerBlocked,match="consumed"):
                    dispatcher.send_prepared(prepared,permit)
                ledger.record_unknown(eid,attempt,reason="test consumes a complete non-completion receipt",
                                      response_receipt=outcome.response_receipt)
    assert len(receiver.receipts)==1
    assert receiver.receipts[0]["dispatch_event_id_seen_before_receipt"]


def test_independent_database_confirms_marker_and_consumption_before_transport(tmp_path):
    exp=_make_experiment(tmp_path)
    permit_holder={}
    def checkpoint(name):
        if name!="before_transport": return
        permit=permit_holder["permit"]
        assert permit.consumed
        conn=sqlite3.connect(str(exp["db"]))
        try:
            row=conn.execute("SELECT seq,run_id,evaluation_id,attempt_id,event_type,payload_json FROM events WHERE event_id=?",
                             (permit.dispatch_event_id,)).fetchone()
            assert row is not None
            payload=json.loads(row[5])
            inflight=conn.execute("SELECT seq FROM events WHERE run_id=? AND evaluation_id=? AND attempt_id=? AND event_type='IN_FLIGHT'",
                                  (row[1],row[2],row[3])).fetchone()
            assert row[4]=="DISPATCH_INTENT" and inflight is not None and inflight[0]<row[0]
            assert payload["request_hash"]==permit.request_hash
        finally: conn.close()
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher._for_tests(ledger.run_id,endpoint=receiver.url,checkpoint=checkpoint) as dispatcher:
                _,_,_,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                permit_holder["permit"]=permit
                outcome=dispatcher.send_prepared(prepared,permit)
                assert outcome.response_receipt is not None
                ledger.record_unknown(_eval_id(exp),permit.attempt_id,reason="retain received response as unknown",
                                      response_receipt=outcome.response_receipt)
    assert len(receiver.receipts)==1
    assert receiver.receipts[0]["dispatch_event_id_seen_before_receipt"]


def test_transport_uses_validated_request_snapshot_after_caller_object_changes(tmp_path):
    exp=_make_experiment(tmp_path)
    holder={}
    def checkpoint(name):
        if name=="before_transport":
            object.__setattr__(holder["prepared"].request,"url",httpx.URL("http://127.0.0.1:1/api/chat"))
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher._for_tests(ledger.run_id,endpoint=receiver.url,checkpoint=checkpoint) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                holder["prepared"]=prepared
                outcome=dispatcher.send_prepared(prepared,permit)
                assert outcome.response_receipt is not None
                ledger.record_unknown(eid,attempt,reason="test-only receipt",response_receipt=outcome.response_receipt)
    assert len(receiver.receipts)==1
    dispatch=next(e for e in _history(exp["db"]) if e["event_type"]=="DISPATCH_INTENT")
    assert receiver.receipts[0]["dispatch_event_id_seen_before_receipt"]==permit.dispatch_event_id
    assert dispatch["payload"]["request_payload_sha256"]==receiver.receipts[0]["body_sha256"]


def test_stale_permit_is_rejected_after_accepted_unknown_missing(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger._open_existing_for_tests(exp["db"],lock_path=exp["lock"],
                reconciliation_verifier=_test_reconciliation_verifier) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                ledger.reconcile(eid,attempt,reviewer_identity="test reviewer",
                    disposition="ACCEPTED_UNKNOWN_MISSING",
                    evidence_references=[{"reference":"independent test log","sha256":"a"*64}],
                    rationale="close the unknown test attempt")
                with pytest.raises(LedgerBlocked): dispatcher.send_prepared(prepared,permit)
                with pytest.raises(LedgerBlocked): ledger.authorize_dispatch(eid,attempt,prepared.request_hash)
    assert receiver.receipts==[]
    assert _state(exp["db"],exp["lock"],_eval_id(exp)).missing_closed


def test_dispatch_and_reconciliation_race_has_one_serialized_outcome(tmp_path):
    exp=_make_experiment(tmp_path)
    transport_entered=threading.Event(); release_transport=threading.Event()
    def checkpoint(name):
        if name=="before_transport":
            transport_entered.set()
            assert release_transport.wait(5)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher._for_tests(ledger.run_id,endpoint=receiver.url,checkpoint=checkpoint) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                outcomes=[]; errors=[]
                def send():
                    try: outcomes.append(dispatcher.send_prepared(prepared,permit))
                    except Exception as exc: errors.append(exc)
                sender=threading.Thread(target=send); sender.start()
                assert transport_entered.wait(5)
                releaser=threading.Thread(target=lambda:(time.sleep(.1),release_transport.set()))
                releaser.start()
                with pytest.raises(LedgerBlocked,match="awaiting durable completion"):
                    ledger.reconcile(eid,attempt,reviewer_identity="test reviewer",
                        disposition="ACCEPTED_UNKNOWN_MISSING",
                        evidence_references=[{"reference":"independent test log","sha256":"b"*64}],
                        rationale="race closure")
                sender.join(timeout=5); releaser.join(timeout=5)
                assert not sender.is_alive() and len(outcomes)==1 and errors==[]
                # The full response receipt prevents reconciliation from closing the attempt
                # between HTTP receipt and durable COMPLETED recording.
                result=_completion_result(outcomes[0],eid,attempt,prepared)
                completion=ledger._make_completion(outcomes[0].response_receipt,result,
                    response_metadata=_completion_metadata(outcomes[0]))
                ledger.record_completed(completion)
    assert len(receiver.receipts)==1


def test_false_completion_without_response_receipt_is_rejected_and_remains_unknown(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                with pytest.raises(TypeError):
                    ledger.record_completed(eid,attempt,prepared.request_hash,
                        raw_response=b"not a provider response",
                        result_record={"case":"fabricated","valid":True},valid=True)
                with pytest.raises(LedgerBlocked): ledger.record_completed(None)
                assert ledger.replay_validate().states[eid].state=="UNKNOWN_OUTCOME"
                assert ledger.replay_validate().last_seq==len(_history(exp["db"]))
    assert receiver.receipts==[]


def test_receipt_identity_completion_derivation_and_single_use_are_enforced(tmp_path):
    exp=_make_experiment(tmp_path)
    foreign=_make_experiment(tmp_path/"foreign")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                outcome=dispatcher.send_prepared(prepared,permit)
                result=_completion_result(outcome,eid,attempt,prepared)
                metadata=_completion_metadata(outcome)
                wrong_eval=dict(result,evaluation_id=_eval_id(exp,1))
                with pytest.raises(LedgerBlocked,match="identity"):
                    ledger._make_completion(outcome.response_receipt,wrong_eval,
                                            response_metadata=metadata)
                wrong_attempt=dict(result,attempt_id="other-attempt")
                with pytest.raises(LedgerBlocked,match="identity"):
                    ledger._make_completion(outcome.response_receipt,wrong_attempt,
                                            response_metadata=metadata)
                with Ledger.open_existing(foreign["db"],lock_path=foreign["lock"]) as foreign_ledger:
                    with pytest.raises(LedgerBlocked,match="unused complete response receipt"):
                        foreign_ledger._make_completion(outcome.response_receipt,result,
                            response_metadata=metadata)
                completion=ledger._make_completion(outcome.response_receipt,result,
                    response_metadata=metadata)
                ledger.record_completed(completion)
                with pytest.raises(LedgerBlocked,match="already consumed"):
                    ledger.record_completed(completion)
                assert ledger.replay_validate().states[eid].state=="COMPLETED"
    assert len(receiver.receipts)==1


def test_rehashed_completion_result_disagreement_blocks_replay(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_fake_session(exp["db"],exp["results"],exp["approval"],fake_endpoint=receiver.url,
                                model_config=exp["config"],lock_path=exp["lock"]) as session:
            runner.execute(session,max_evaluations=1)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP TRIGGER events_no_update")
    row=conn.execute("SELECT seq,payload_json FROM events WHERE event_type='COMPLETED'").fetchone()
    payload=json.loads(row[1]); payload["result_record"]["raw_output_text"]="not the received content"
    payload_json=canonical_bytes(payload).decode("utf-8")
    conn.execute("UPDATE events SET payload_json=?,payload_sha256=? WHERE seq=?",
        (payload_json,hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),row[0]))
    _rehash_events(conn); conn.commit(); conn.close()
    with pytest.raises(LedgerBlocked,match="derivation metadata|exact response bytes"):
        Ledger.open_existing(exp["db"],lock_path=exp["lock"])


def test_schema_requires_global_attempt_index_without_rebuilding_database(tmp_path):
    exp=_make_experiment(tmp_path)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP INDEX one_attempt_id_per_run"); conn.commit(); conn.close()
    before=_history(exp["db"])
    with pytest.raises(LedgerBlocked,match="schema objects are incomplete"):
        Ledger.open_existing(exp["db"],lock_path=exp["lock"])
    conn=sqlite3.connect(str(exp["db"]))
    index=conn.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='one_attempt_id_per_run'").fetchone()
    conn.close()
    assert index is None and _history(exp["db"])==before


def test_rehashed_duplicate_attempt_history_is_rejected_by_application_replay(tmp_path,monkeypatch):
    exp=_make_experiment(tmp_path)
    _,attempt,_=_seed_attempt(exp,0)
    _seed_attempt(exp,1)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP INDEX one_attempt_id_per_run")
    conn.execute("DROP TRIGGER events_no_update")
    second=conn.execute("SELECT seq FROM events WHERE event_type='IN_FLIGHT' ORDER BY seq DESC LIMIT 1").fetchone()[0]
    conn.execute("UPDATE events SET attempt_id=? WHERE seq=?",(attempt,second))
    _rehash_events(conn); conn.commit(); conn.close()
    monkeypatch.setattr(ledger_module,"_validate_connection",lambda *args,**kwargs:None)
    with pytest.raises(LedgerBlocked,match="globally unique"):
        Ledger.open_existing(exp["db"],lock_path=exp["lock"])


def test_approval_verification_fails_closed_and_test_verifier_is_isolated(tmp_path,monkeypatch):
    approval=_approval_manifest()
    with pytest.raises(LedgerBlocked,match="no trusted approval verifier"):
        runner.validate_approval_manifest(approval)
    arbitrary=dict(approval,signature="any caller supplied text")
    with pytest.raises(LedgerBlocked,match="did not authenticate"):
        runner.validate_approval_manifest(arbitrary,verifier=lambda value:False)
    with pytest.raises(LedgerBlocked,match="did not authenticate"):
        runner.validate_approval_manifest(approval,verifier=lambda value:"signature")
    assert runner.validate_approval_manifest(approval,verifier=_test_approval_verifier)==approval
    draft=json.loads(json.dumps(approval))
    draft["documents"]["research/56_M4B3_PROSPECTIVE_AMENDMENT_DRAFT.md"]["approval"]="DRAFT"
    with pytest.raises(LedgerBlocked,match="approval status is unresolved"):
        runner.validate_approval_manifest(draft,verifier=_test_approval_verifier)
    results=tmp_path/"results.json"; results.write_bytes(_template_bytes())
    db=tmp_path/"real.sqlite3"
    monkeypatch.setenv("BLACKBOX_M4B3_LIVE_EXECUTION_ENABLED","1")
    with pytest.raises(LedgerBlocked,match="real M4B.3 initialization is disabled"):
        runner.initialize_experiment(db,results,approval,lock_path=tmp_path/"real.lock")
    approval_path=tmp_path/"synthetic-approval.json"
    approval_path.write_text(json.dumps(approval),encoding="utf-8")
    monkeypatch.setattr("sys.argv",["evaluate_m4b3.py","--initialize",
        "--ledger-path",str(db),"--results-path",str(results),
        "--approval-manifest",str(approval_path),"--lock-path",str(tmp_path/"cli.lock")])
    with pytest.raises(LedgerBlocked,match="real M4B.3 initialization is disabled"):
        runner.main()
    monkeypatch.setattr("sys.argv",["evaluate_m4b3.py","--run-live"])
    with pytest.raises(SystemExit,match="live execution is disabled"):
        runner.main()
    assert not db.exists() and runner.LIVE_EXECUTION_ENABLED is False
    _make_experiment(tmp_path/"synthetic-test")


def test_test_source_provenance_does_not_change_fingerprint_but_runtime_does(tmp_path):
    exp=_make_experiment(tmp_path)
    manifest=_build_run_manifest(exp["plans"],exp["revision"],_approval_manifest(),TEST_MODEL)
    changed=json.loads(json.dumps(manifest))
    test_key="tests/test_m4b3_ledger.py"
    changed["audit_metadata"]["test_source_sha256"][test_key]="0"*64
    assert manifest_fingerprint(changed)==manifest_fingerprint(manifest)
    runtime_key="blackbox/providers.py"
    changed=json.loads(json.dumps(manifest))
    changed["fingerprint_inputs"]["runner_provider_and_schema_code_sha256"][runtime_key]="0"*64
    assert manifest_fingerprint(changed)!=manifest_fingerprint(manifest)


def test_initialize_requires_acquired_matching_lock(tmp_path):
    exp=_make_experiment(tmp_path/"source")
    rows=runner.plan_rows(exp["plans"])
    manifest=_build_run_manifest(exp["plans"],exp["revision"],_approval_manifest(),TEST_MODEL)
    bad_db=tmp_path/"unacquired.sqlite3"; expected=tmp_path/"expected.lock"
    with pytest.raises(LedgerBlocked,match="acquired lock"):
        Ledger.initialize(bad_db,plan_rows=rows,manifest=manifest,
            approved_protocol_sha256=manifest["approved_protocol_sha256"],initial_results_sha256="a"*64,
            lock_path=expected,held_lock=RunLock(expected))
    class SpoofedLock(RunLock):
        def owns(self,path): return True
    spoof_db=tmp_path/"spoofed.sqlite3"
    with pytest.raises(LedgerBlocked,match="acquired lock"):
        Ledger.initialize(spoof_db,plan_rows=rows,manifest=manifest,
            approved_protocol_sha256=manifest["approved_protocol_sha256"],initial_results_sha256="a"*64,
            lock_path=expected,held_lock=SpoofedLock(expected))
    mismatch_db=tmp_path/"mismatched.sqlite3"
    with RunLock(tmp_path/"different.lock") as acquired:
        with pytest.raises(LedgerBlocked,match="acquired lock"):
            Ledger.initialize(mismatch_db,plan_rows=rows,manifest=manifest,
                approved_protocol_sha256=manifest["approved_protocol_sha256"],initial_results_sha256="b"*64,
                lock_path=expected,held_lock=acquired)
    assert not bad_db.exists() and not spoof_db.exists() and not mismatch_db.exists()


@pytest.mark.parametrize("case",["exact_limit","declared_over_limit","small_length_overflow",
                                  "missing_length_overflow","one_large_chunk","multiple_chunks","interrupted"])
def test_response_stream_is_bounded_and_ambiguous_outcomes_are_never_retried(tmp_path,case):
    limit=ledger_module.MAX_RESPONSE_BYTES
    if case=="exact_limit":
        chunks=[b"x"*limit]; transport_kwargs={"content_length":limit}
    elif case=="declared_over_limit":
        chunks=[b"x"*(limit+1)]; transport_kwargs={"content_length":limit+1}
    elif case=="small_length_overflow":
        chunks=[b"x"*(limit+1)]; transport_kwargs={"content_length":1}
    elif case=="one_large_chunk":
        chunks=[b"x"*(limit+1)]; transport_kwargs={"include_length":False}
    elif case in {"missing_length_overflow","multiple_chunks"}:
        chunks=[b"x"*(limit//2),b"y"*(limit//2),b"z"*2]
        transport_kwargs={"include_length":case!="missing_length_overflow",
                          "content_length":1 if case=="multiple_chunks" else None}
    else:
        chunks=[b"partial response prefix"]; transport_kwargs={"content_length":100,"error_after":0}
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        transport=_ResponseMutationTransport(chunks,**transport_kwargs)
        with _open_session(exp,receiver,transport=transport) as session:
            if case=="exact_limit":
                result=runner.execute(session,max_evaluations=1)
                assert result[0]["valid"] is False
            else:
                with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
        assert len(receiver.receipts)==1
    events=_history(exp["db"])
    if case=="exact_limit":
        completion=next(e for e in events if e["event_type"]=="COMPLETED")
        raw=base64.b64decode(completion["payload"]["response_receipt"]["raw_body_b64"],validate=True)
        assert len(raw)==limit and _state(exp["db"],exp["lock"],_eval_id(exp)).state=="COMPLETED"
    else:
        unknown=next(e for e in reversed(events) if e["event_type"]=="UNKNOWN_OUTCOME")
        metadata=unknown["payload"]["metadata"]
        prefix=base64.b64decode(metadata["retained_prefix_b64"],validate=True)
        assert len(prefix)<=limit
        assert hashlib.sha256(prefix).hexdigest()==metadata["retained_prefix_sha256"]
        assert metadata["observed_response_bytes"]>=len(prefix)
        assert _state(exp["db"],exp["lock"],_eval_id(exp)).state=="UNKNOWN_OUTCOME"
        with pytest.raises(LedgerBlocked):
            with _open_session(exp,receiver) as session: runner.execute(session,max_evaluations=1)
        assert len(receiver.receipts)==1


def _completion_result(outcome,evaluation,attempt,prepared):
    return {"evaluation_id":evaluation,"attempt_id":attempt,"request_hash":prepared.request_hash,
            "test_metadata":"caller fields are not response-derived"}


def _completion_metadata(outcome):
    return {"dispatch_event_id":outcome.dispatch_event_id,"request_hash":outcome.request_hash,
            "response_body_complete":True,"status_code":outcome.status_code,
            "safe_headers":outcome.safe_headers or {},
            "observed_response_bytes":outcome.observed_response_bytes,
            "retained_prefix_sha256":outcome.retained_prefix_sha256,
            "declared_content_length":outcome.declared_content_length}


def test_session_registry_rejects_forgery_substitution_and_closed_sessions(tmp_path):
    exp=_make_experiment(tmp_path/"main")
    other=_make_experiment(tmp_path/"other")
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        session=_open_session(exp,receiver)
        forged=runner.RunSession(session.ledger,session.plans,session.dispatcher,
            session.output_path,session.envelope,session.model_config,"fake-test")
        with pytest.raises(LedgerBlocked): runner.execute(forged,max_evaluations=1)
        with pytest.raises(AttributeError): session.dispatcher=object()
        class ArbitraryDispatcher:
            def prepare(self,**_kwargs): raise AssertionError("must be rejected before preparation")
            def send_prepared(self,*_args,**_kwargs): raise AssertionError("must not dispatch")
            def close(self): pass
        custom=runner.RunSession(session.ledger,session.plans,ArbitraryDispatcher(),
            session.output_path,session.envelope,session.model_config,"fake-test")
        with pytest.raises(LedgerBlocked): runner.execute(custom,max_evaluations=1)
        with Ledger.open_existing(other["db"],lock_path=other["lock"]) as other_ledger:
            cross_ledger=runner.RunSession(other_ledger,session.plans,session.dispatcher,
                session.output_path,session.envelope,session.model_config,"fake-test")
            with pytest.raises(LedgerBlocked): runner.execute(cross_ledger,max_evaluations=1)
        original=dict(session.plans[0])
        session.plans[0]["arm"]="D"
        with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
        session.plans[0].clear(); session.plans[0].update(original)
        session.close()
        with pytest.raises(LedgerBlocked): runner.execute(session,max_evaluations=1)
        assert receiver.receipts==[]


def test_completion_is_rederived_from_receipt_and_schema(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl",modes=["schema_invalid"]) as receiver:
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with M4B3OllamaDispatcher(ledger.run_id,endpoint=receiver.url) as dispatcher:
                _,eid,attempt,prepared,permit=_prepare_dispatch(ledger,dispatcher,exp)
                outcome=dispatcher.send_prepared(prepared,permit)
                forged=_completion_result(outcome,eid,attempt,prepared)
                forged.update({"valid":True,"raw_output":{"fabricated":True},
                               "validated_output":{"caller_claim":"accepted"},
                               "usage":{"output_tokens":999}})
                with pytest.raises(TypeError):
                    ledger._make_completion(outcome.response_receipt,forged,valid=True,
                        validation={"valid":True},response_metadata=_completion_metadata(outcome))
                completion=ledger._make_completion(outcome.response_receipt,forged,
                    response_metadata=_completion_metadata(outcome))
                assert completion.valid is False
                assert completion.result_record["valid"] is False
                assert "validated_output" not in completion.result_record
                assert completion.validation["valid"] is False
                ledger.record_completed(completion)
                state=ledger.replay_validate().states[eid]
                assert state.state=="COMPLETED" and state.result["valid"] is False
                assert state.result["usage"]["output_tokens"]==11
    assert len(receiver.receipts)==1


def test_reconciliation_fails_closed_without_verifier_or_exact_true(tmp_path):
    exp=_make_experiment(tmp_path)
    eid,attempt,_=_seed_attempt(exp,dispatch=True,unknown=True)
    before=len(_history(exp["db"]))
    for disposition in ("ACCEPTED_UNKNOWN_MISSING","CONFIRMED_FAILED"):
        with Ledger.open_existing(exp["db"],lock_path=exp["lock"]) as ledger:
            with pytest.raises(LedgerBlocked,match="no trusted reconciliation verifier"):
                ledger.reconcile(eid,attempt,reviewer_identity="forged reviewer",
                    disposition=disposition,evidence_references=[{"reference":"fabricated","sha256":"a"*64}],
                    rationale="caller asserted approval")
            with pytest.raises(TypeError):
                ledger.reconcile(eid,attempt,reviewer_identity="forged reviewer",
                    disposition=disposition,evidence_references=[{"reference":"fabricated","sha256":"a"*64}],
                    rationale="caller asserted approval",approval_result=True)
    raising_verifier=lambda _proposal: (_ for _ in ()).throw(RuntimeError("synthetic verifier fault"))
    for verifier in (lambda _proposal:False,lambda _proposal:object(),raising_verifier):
        with Ledger._open_existing_for_tests(exp["db"],lock_path=exp["lock"],
                reconciliation_verifier=verifier) as ledger:
            with pytest.raises(LedgerBlocked,match="verifier"):
                ledger.reconcile(eid,attempt,reviewer_identity="test reviewer",
                    disposition="ACCEPTED_UNKNOWN_MISSING",
                    evidence_references=[{"reference":"fabricated","sha256":"a"*64}],
                    rationale="synthetic verifier rejection")
    assert len(_history(exp["db"]))==before
    with pytest.raises(TypeError):
        runner.open_fake_session(exp["db"],exp["results"],exp["approval"],
            fake_endpoint="http://127.0.0.1:1",lock_path=exp["lock"],
            approval_verifier=_test_approval_verifier)


def test_test_only_approval_verifier_is_not_exposed_through_real_cli(tmp_path,monkeypatch):
    exp=_make_experiment(tmp_path)
    monkeypatch.setattr("sys.argv",["evaluate_m4b3.py","--run-fake",
        "--ledger-path",str(exp["db"]),"--results-path",str(exp["results"]),
        "--approval-manifest",str(exp["approval"]),"--lock-path",str(exp["lock"]),
        "--fake-endpoint","http://127.0.0.1:1"])
    with pytest.raises(LedgerBlocked,match="no trusted approval verifier"):
        runner.main()


def test_compressed_response_is_unknown_and_request_requires_identity(tmp_path):
    exp=_make_experiment(tmp_path)
    compressed=gzip.compress(b"expanded response body"*5000)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        transport=_ResponseMutationTransport([compressed],content_encoding="gzip")
        with _open_session(exp,receiver,transport=transport) as session:
            with pytest.raises(LedgerBlocked,match="unknown"):
                runner.execute(session,max_evaluations=1)
        assert receiver.receipts[0]["accept_encoding"]=="identity"
        assert _state(exp["db"],exp["lock"],_eval_id(exp)).state=="UNKNOWN_OUTCOME"
        assert not any(e["event_type"]=="COMPLETED" for e in _history(exp["db"]))


@pytest.mark.parametrize("tamper",["parsed_output","validation_metadata"])
def test_rehashed_completion_derivation_tampering_blocks_replay(tmp_path,tamper):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        with _open_session(exp,receiver) as session:
            runner.execute(session,max_evaluations=1)
    conn=sqlite3.connect(str(exp["db"]))
    conn.execute("DROP TRIGGER events_no_update")
    row=conn.execute("SELECT seq,payload_json FROM events WHERE event_type='COMPLETED'").fetchone()
    payload=json.loads(row[1])
    if tamper=="parsed_output":
        payload["result_record"]["raw_output"]={"forged":True}
    else:
        payload["valid"]=False
        payload["validation"]={"valid":False,"error_type":"Forged"}
        payload["result_record"]["valid"]=False
    encoded=canonical_bytes(payload).decode("utf-8")
    conn.execute("UPDATE events SET payload_json=?,payload_sha256=? WHERE seq=?",
        (encoded,hashlib.sha256(encoded.encode("utf-8")).hexdigest(),row[0]))
    _rehash_events(conn); conn.commit(); conn.close()
    with pytest.raises(LedgerBlocked,match="completion output or validation"):
        Ledger.open_existing(exp["db"],lock_path=exp["lock"])


@pytest.mark.skipif(os.name=="nt",reason="POSIX permits replacing an open lock pathname")
def test_lock_ownership_detects_path_replacement_and_database_identity(tmp_path):
    exp=_make_experiment(tmp_path/"ledger")
    lock=RunLock(exp["lock"]).acquire()
    moved=tmp_path/"original.lock"
    os.replace(exp["lock"],moved)
    exp["lock"].write_bytes(b"replacement")
    assert lock.owns(exp["lock"]) is False
    lock.release()
    with pytest.raises(LedgerBlocked,match="registered lock file"):
        Ledger.open_existing(exp["db"],lock_path=exp["lock"])


@pytest.mark.skipif(os.name=="nt",reason="fork ownership semantics are POSIX-specific")
def test_forked_child_cannot_reuse_or_release_parent_run_lock(tmp_path):
    lock_path=tmp_path/"fork.lock"
    with RunLock(lock_path) as owner:
        read_fd,write_fd=os.pipe()
        child=os.fork()
        if child==0:
            os.close(read_fd)
            owned=owner.owns(lock_path)
            owner.release()
            os.write(write_fd,b"1" if owned else b"0")
            os.close(write_fd)
            os._exit(0)
        os.close(write_fd)
        result=os.read(read_fd,1); os.close(read_fd)
        _,status=os.waitpid(child,0)
        assert status==0 and result==b"0"
        assert owner.owns(lock_path) is True
        with pytest.raises(LockUnavailable): RunLock(lock_path).acquire()


def test_cross_process_dispatch_and_reconciliation_are_serialized_by_run_lock(tmp_path):
    exp=_make_experiment(tmp_path)
    with FakeReceiver(exp["db"],tmp_path/"receipt.jsonl") as receiver:
        ready=tmp_path/"transport-ready.txt"; release=tmp_path/"transport-release.txt"
        config_path=tmp_path/"model-config.json"
        config_path.write_text(json.dumps(exp["config"]),encoding="utf-8")
        child_code=(
            "import sys,time\n"
            "from pathlib import Path\n"
            "from scripts import evaluate_m4b3 as runner\n"
            "db,results,approval,lock,endpoint,ready,release,config_path=sys.argv[1:]\n"
            "def verifier(value): return value.get('test_only') is True and value.get('signature')=='synthetic-only-test-approval'\n"
            "def checkpoint(name):\n"
            "    if name=='before_transport':\n"
            "        Path(ready).write_text('ready')\n"
            "        deadline=time.time()+10\n"
            "        while not Path(release).exists() and time.time()<deadline: time.sleep(.01)\n"
            "import json\n"
            "config=json.loads(Path(config_path).read_text())\n"
            "session=runner._open_fake_session_for_tests(db,results,approval,fake_endpoint=endpoint,\n"
            "    model_config=config,lock_path=lock,approval_verifier=verifier,checkpoint=checkpoint)\n"
            "with session: runner.execute(session,max_evaluations=1)\n"
        )
        env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT)+os.pathsep+env.get("PYTHONPATH","")
        child=subprocess.Popen([sys.executable,"-c",child_code,str(exp["db"]),str(exp["results"]),
            str(exp["approval"]),str(exp["lock"]),receiver.url,str(ready),str(release),str(config_path)],
            cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.time()+12
            while time.time()<deadline and not ready.exists(): time.sleep(.02)
            if not ready.exists():
                stdout,stderr=child.communicate(timeout=5)
                pytest.fail(f"dispatching process missed the pre-transport barrier: {stdout}\n{stderr}")
            conn=sqlite3.connect(str(exp["db"]))
            row=conn.execute("SELECT evaluation_id FROM events WHERE event_type='DISPATCH_INTENT'").fetchone()
            conn.close()
            assert row is not None
            with pytest.raises(LockUnavailable):
                Ledger._open_existing_for_tests(exp["db"],lock_path=exp["lock"],
                    reconciliation_verifier=_test_reconciliation_verifier)
            release.write_text("continue")
            stdout,stderr=child.communicate(timeout=15)
            assert child.returncode==0,(stdout,stderr)
            assert len(receiver.receipts)==1
            assert _state(exp["db"],exp["lock"],row[0]).state=="COMPLETED"
        finally:
            if child.poll() is None:
                child.kill(); child.wait(timeout=5)

