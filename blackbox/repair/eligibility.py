"""Strict eligibility gate. Model confidence is never consulted; only recorded state is."""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from .fixtures import content_pinned, fixture_path, get_fixture, revision_available, trusted


def hypothesis_digest(hypothesis: dict) -> str:
    payload = json.dumps(hypothesis, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class Eligibility:
    eligible: bool = False
    checks: list[dict] = field(default_factory=list)
    investigation: dict | None = None
    fixture: dict | None = None
    hypothesis_index: int | None = None
    hypothesis: dict | None = None
    frame: dict | None = None
    commit: str | None = None
    approval: dict | None = None

    def add(self, code: str, ok: bool, detail: str):
        self.checks.append({'code': code, 'ok': bool(ok), 'detail': detail})
        return ok

    def summary(self) -> dict:
        return {
            'eligible': self.eligible,
            'reasons': [{'code': item['code'], 'detail': item['detail']} for item in self.checks if not item['ok']],
            'checks': self.checks,
            'investigation_id': (self.investigation or {}).get('id'),
            'fixture': (self.fixture or {}).get('name'),
            'hypothesis_index': self.hypothesis_index,
            'hypothesis_sha256': hypothesis_digest(self.hypothesis) if self.hypothesis else None,
            'approval_id': (self.approval or {}).get('id'),
            'frame': self.frame,
            'commit': self.commit,
        }


def evidence_reference_errors(findings: dict, snapshot: dict) -> list[str]:
    """Re-check the references that the investigation layer validated, without trusting the model."""
    ids = {item['id'] for item in snapshot.get('evidence', [])}
    errors = []
    observed_failure = findings.get('observed_failure') or {}
    refs = list(observed_failure.get('evidence_ids') or [])
    for claim in findings.get('observed_facts') or []:
        refs.extend(claim.get('evidence_ids') or [])
    for hypothesis in (findings.get('hypotheses') or []) + (findings.get('alternatives') or []):
        refs.extend(hypothesis.get('supporting_evidence') or [])
        refs.extend(hypothesis.get('contradicting_evidence') or [])
    unknown = set(refs) - ids
    if unknown:
        errors.append('unknown evidence references: ' + ', '.join(sorted(unknown)))
    event_ids = {item['id'] for item in snapshot.get('evidence', []) if item.get('type') == 'event'}
    if not event_ids.intersection(observed_failure.get('evidence_ids') or []):
        errors.append('observed failure does not cite the recorded event')
    resolved = {item['id'] for item in snapshot.get('evidence', [])
                if item.get('type') == 'stack_frame' and item.get('status') == 'resolved'}
    unresolved = {item['id'] for item in snapshot.get('evidence', [])
                  if item.get('status') == 'unresolved'}
    if findings.get('outcome') == 'LIKELY_CAUSE':
        for index, hypothesis in enumerate(findings.get('hypotheses') or []):
            supporting = set(hypothesis.get('supporting_evidence') or [])
            if not event_ids.intersection(supporting) or not resolved.intersection(supporting):
                errors.append(f'hypothesis {index} lacks an event and resolved source reference')
            if supporting & unresolved:
                errors.append(f'hypothesis {index} cites unresolved source')
    return errors


def evaluate(store, repo: Path, investigation_id: str, fixture_name: str,
             hypothesis_index: int | None = None) -> Eligibility:
    result = Eligibility()
    investigation = store.investigation(investigation_id)
    result.investigation = investigation
    if not result.add('investigation_exists', investigation is not None, 'investigation record exists'):
        return result

    status, outcome = investigation['status'], investigation.get('outcome')
    result.add('investigation_completed', status == 'completed',
               f'investigation status is {status}')
    # INVESTIGATION_FAILED and INSUFFICIENT_EVIDENCE are hard blocks, not weaker approvals.
    result.add('outcome_likely_cause', outcome == 'LIKELY_CAUSE',
               f'investigation outcome is {outcome or "unclassified"}')

    try:
        fixture = get_fixture(fixture_name)
    except KeyError:
        result.add('fixture_known', False, f'unknown fixture: {fixture_name}')
        return result
    result.fixture = fixture
    result.add('fixture_known', True, f'fixture {fixture_name} is registered')
    ok, detail = trusted(repo, fixture)
    result.add('repository_trusted', ok, detail)

    snapshot = investigation.get('evidence') or {}
    findings = investigation.get('findings') or {}
    errors = evidence_reference_errors(findings, snapshot)
    result.add('evidence_references_valid', not errors, '; '.join(errors) or 'all references resolve')

    event = next((item for item in snapshot.get('evidence', []) if item.get('type') == 'event'), None)
    if not event:
        result.add('recorded_revision', False, 'investigation has no recorded event')
        return result
    result.commit = event.get('commit')
    result.add('recorded_revision', revision_available(repo, result.commit),
               f'revision {result.commit} is present in the repository')
    ok, detail = content_pinned(repo, result.commit, fixture)
    result.add('source_pinned', ok, detail)

    hypotheses = findings.get('hypotheses') or []
    index = hypothesis_index
    if index is None:
        index = next((position for position, hypothesis in enumerate(hypotheses)
                      if any(item.get('id') in (hypothesis.get('supporting_evidence') or [])
                             for item in snapshot.get('evidence', [])
                             if item.get('type') == 'stack_frame' and item.get('status') == 'resolved')),
                     0 if hypotheses else None)
    if index is None or not 0 <= index < len(hypotheses):
        result.add('approved_hypothesis', False, 'investigation has no hypothesis to approve')
        return result
    result.hypothesis_index = index
    result.hypothesis = hypotheses[index]

    frames = [item for item in snapshot.get('evidence', [])
              if item.get('type') == 'stack_frame'
              and item.get('id') in (result.hypothesis.get('supporting_evidence') or [])]
    resolved_frames = [frame for frame in frames if frame.get('status') == 'resolved']
    result.add('resolved_source_frame', bool(resolved_frames),
               'a cited source frame is resolved at the recorded revision')
    if resolved_frames:
        # Frames are recorded innermost first, so the first cited resolved frame is the failure site.
        result.frame = resolved_frames[0]
        cited_path = result.frame.get('path')
        base = fixture_path(fixture) + '/'
        result.add('frame_in_approved_file', any(cited_path == base + allowed for allowed in fixture['allowed_files']),
                   f'cited frame {cited_path} is in the allowed patch files')
        result.add('frame_matches_fixture', cited_path == fixture['event']['frame']['path'],
                   f'cited frame matches the registered fixture failure location')

    approvals = store.repair_approvals(investigation_id)
    digest = hypothesis_digest(result.hypothesis)
    matching = next((approval for approval in approvals
                     if approval['hypothesis_index'] == index
                     and approval['hypothesis_sha256'] == digest
                     and approval['evidence_hash'] == investigation.get('evidence_hash')), None)
    result.approval = matching
    result.add('human_approval', bool(matching),
               'a human review record matches this hypothesis and evidence snapshot' if matching
               else 'no review record matches this hypothesis and evidence snapshot')

    result.eligible = all(item['ok'] for item in result.checks)
    return result
