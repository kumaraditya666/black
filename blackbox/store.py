import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .redaction import redact
from .schemas import Event


class ConflictError(Exception):
    pass


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY, incident_id INTEGER NOT NULL REFERENCES incidents(id),
                    content_hash TEXT NOT NULL, received_at TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY, incident_id INTEGER NOT NULL REFERENCES incidents(id),
                    provider TEXT NOT NULL, model TEXT NOT NULL, evidence_hash TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    evidence TEXT NOT NULL, findings TEXT, error TEXT, latency_ms INTEGER, usage TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_running_investigation ON investigations
                    (incident_id, provider, model, evidence_hash) WHERE status='running';
                CREATE TABLE IF NOT EXISTS repair_approvals (
                    id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL,
                    hypothesis_index INTEGER NOT NULL, hypothesis_sha256 TEXT NOT NULL,
                    evidence_hash TEXT NOT NULL, reviewer TEXT NOT NULL, note TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_repair_approval ON repair_approvals
                    (investigation_id, hypothesis_index, hypothesis_sha256);
                CREATE TABLE IF NOT EXISTS repair_attempts (
                    id TEXT PRIMARY KEY, incident_id INTEGER, investigation_id TEXT NOT NULL,
                    fixture TEXT NOT NULL, "commit" TEXT, status TEXT NOT NULL, approval_id TEXT,
                    proposal TEXT, validation TEXT, diff TEXT, reproduction_before TEXT,
                    reproduction_after TEXT, regression TEXT, isolation TEXT, error TEXT,
                    timings TEXT, usage TEXT, review TEXT, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def ingest(self, event: Event):
        data = event.model_dump(mode='json')
        data['message'] = redact(data['message'])
        data['traceback'] = redact(data['traceback'])
        for frame in data['frames']:
            frame['function'] = redact(frame['function'])
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        # A logical issue groups the same exception at the same application stack, across commits.
        signature = [data['exception_type'], [[f['path'], f['line'], f['function']] for f in data['frames']]]
        fingerprint = hashlib.sha256(json.dumps(signature, ensure_ascii=False).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT * FROM events WHERE event_id=?', (data['event_id'],)).fetchone()
            if existing:
                if existing['content_hash'] != digest:
                    raise ConflictError('event_id already exists with different redacted content')
                return existing['incident_id'], False
            db.execute('INSERT OR IGNORE INTO incidents(fingerprint) VALUES (?)', (fingerprint,))
            incident_id = db.execute('SELECT id FROM incidents WHERE fingerprint=?', (fingerprint,)).fetchone()[0]
            db.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?)', (data['event_id'], incident_id, digest, datetime.now(timezone.utc).isoformat(), payload))
            return incident_id, True

    def events(self, incident_id: int):
        with self.connect() as db:
            rows = db.execute('SELECT received_at,payload FROM events WHERE incident_id=? ORDER BY rowid', (incident_id,)).fetchall()
        return [{'received_at': r['received_at'], **json.loads(r['payload'])} for r in rows]

    def incidents(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT incident_id AS id, COUNT(*) AS event_count FROM events GROUP BY incident_id ORDER BY incident_id')]

    def investigations(self, incident_id: int):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT id, incident_id, provider, model, status, created_at, updated_at FROM investigations WHERE incident_id=? ORDER BY rowid DESC', (incident_id,))]

    def add_repair_approval(self, investigation_id: str, hypothesis_index: int, hypothesis_sha256: str,
                            evidence_hash: str, reviewer: str, note: str | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO repair_approvals (id,investigation_id,hypothesis_index,hypothesis_sha256,evidence_hash,reviewer,note,created_at) VALUES (?,?,?,?,?,?,?,?)',
                       (str(uuid.uuid4()), investigation_id, hypothesis_index, hypothesis_sha256,
                        evidence_hash, reviewer, note, now))
            row = db.execute('SELECT * FROM repair_approvals WHERE investigation_id=? AND hypothesis_index=? AND hypothesis_sha256=?',
                             (investigation_id, hypothesis_index, hypothesis_sha256)).fetchone()
        return dict(row)

    def repair_approvals(self, investigation_id: str) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                'SELECT * FROM repair_approvals WHERE investigation_id=? ORDER BY created_at DESC',
                (investigation_id,))]

    def save_repair_attempt(self, record: dict):
        columns = ('id', 'incident_id', 'investigation_id', 'fixture', 'commit', 'status', 'approval_id',
                   'proposal', 'validation', 'diff', 'reproduction_before', 'reproduction_after',
                   'regression', 'isolation', 'error', 'timings', 'usage', 'review', 'created_at', 'updated_at')
        encoded = []
        for key in columns:
            value = record.get(key)
            if key in ('proposal', 'validation', 'reproduction_before', 'reproduction_after', 'regression',
                       'isolation', 'timings', 'usage', 'review') and value is not None:
                value = json.dumps(value, ensure_ascii=False)
            encoded.append(value)
        quoted = [f'"{column}"' if column == 'commit' else column for column in columns]
        with self.connect() as db:
            db.execute(f"INSERT OR REPLACE INTO repair_attempts ({','.join(quoted)}) VALUES ({','.join('?' * len(columns))})", encoded)

    def repair_attempt(self, attempt_id: str):
        with self.connect() as db:
            row = db.execute('SELECT * FROM repair_attempts WHERE id=?', (attempt_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        for key in ('proposal', 'validation', 'reproduction_before', 'reproduction_after', 'regression',
                    'isolation', 'timings', 'usage', 'review'):
            result[key] = json.loads(result[key]) if result[key] else None
        return result

    def repair_attempts(self) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                'SELECT id, incident_id, investigation_id, fixture, "commit", status, created_at, updated_at '
                'FROM repair_attempts ORDER BY rowid DESC')]

    def review_repair_attempt(self, attempt_id: str, decision: str, reviewer: str, note: str | None = None):
        if decision not in ('accept', 'reject'):
            raise ValueError('review decision must be accept or reject')
        if not reviewer.strip():
            raise ValueError('reviewer is required')
        review = {'decision': decision, 'reviewer': reviewer.strip(), 'note': note,
                  'reviewed_at': datetime.now(timezone.utc).isoformat(),
                  'notice': 'Developer review of the attempt; it cannot change the test-derived verification status.'}
        with self.connect() as db:
            updated = db.execute('UPDATE repair_attempts SET review=?, updated_at=? WHERE id=?',
                                 (json.dumps(review, ensure_ascii=False), review['reviewed_at'], attempt_id))
            if not updated.rowcount:
                return None
        return self.repair_attempt(attempt_id)

    def investigation(self, investigation_id: str):
        with self.connect() as db:
            row = db.execute('SELECT * FROM investigations WHERE id=?', (investigation_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        for key in ('evidence', 'findings', 'usage'):
            result[key] = json.loads(result[key]) if result[key] else None
        if result['status'] == 'failed':
            result['outcome'] = 'INVESTIGATION_FAILED'
            error = result['error'] or ''
            if error.startswith(('Provider returned invalid structured output', 'Evidence validation failed',
                                 'Model output reached the token limit')):
                result['failure_kind'] = 'INVALID_MODEL_RESPONSE'
            elif error.startswith('Provider request timed out'):
                result['failure_kind'] = 'PROVIDER_TIMEOUT'
            elif error.startswith('Evidence prompt does not fit'):
                result['failure_kind'] = 'EVIDENCE_TOO_LARGE'
            elif error.startswith('Provider configuration or local endpoint'):
                result['failure_kind'] = 'PROVIDER_UNAVAILABLE'
            else:
                result['failure_kind'] = 'PROVIDER_FAILURE'
        elif result['status'] == 'completed' and result['findings']:
            result['outcome'] = result['findings'].get('outcome', 'LEGACY_UNCLASSIFIED')
        else:
            result['outcome'] = None
        return result
