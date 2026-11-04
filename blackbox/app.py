import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from .schemas import Event
from .source import resolve
from .store import ConflictError, Store
from .investigation_schema import InvestigationRequest
from .investigator import collect, evidence_hash, investigate
from .providers import configured_provider, ProviderError


def create_app(db_path: str | None = None, repo_path: str | None = None) -> FastAPI:
    store = Store(db_path or os.environ.get('BLACKBOX_DB', 'data/events.db'))
    repo = Path(repo_path or os.environ.get('BLACKBOX_REPO', 'sample_repo')).resolve()
    app = FastAPI(title='BLACKBOX local evidence engine')

    @app.post('/events', status_code=201)
    def ingest(event: Event):
        try:
            incident_id, created = store.ingest(event)
        except ConflictError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {'incident_id': incident_id, 'event_id': str(event.event_id), 'created': created}

    @app.get('/incidents/{incident_id}/report')
    def report(incident_id: int):
        events = store.events(incident_id)
        if not events:
            raise HTTPException(404, 'incident not found')
        for event in events:
            event['source_evidence'] = [resolve(repo, event['commit'], f) for f in event['frames']]
        return {'incident_id': incident_id, 'event_count': len(events), 'events': events,
                'notice': 'Evidence only; no root cause has been established.'}

    @app.get('/incidents')
    def list_incidents():
        return store.incidents()

    @app.get('/incidents/{incident_id}/context')
    def context(incident_id: int):
        try:
            snapshot = collect(store, repo, incident_id)
        except KeyError:
            raise HTTPException(404, 'incident not found')
        return {'evidence_hash': evidence_hash(snapshot), 'context': snapshot,
                'warning': 'Review every field before external transmission; redaction is not complete.'}

    @app.post('/incidents/{incident_id}/investigations')
    def start_investigation(incident_id: int, request: InvestigationRequest):
        try:
            snapshot = collect(store, repo, incident_id)
        except KeyError:
            raise HTTPException(404, 'incident not found')
        try:
            provider = configured_provider()
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
        if provider.name == 'gemini' and (not request.consent_external or request.reviewed_evidence_hash != evidence_hash(snapshot)):
            raise HTTPException(403, 'Review the current context and explicitly consent to external transmission with its evidence hash.')
        result, cached = investigate(store, repo, incident_id, provider, request.force, snapshot)
        return {'cached': cached, 'investigation': result,
                'warning': 'Citation IDs are checked; narrative accuracy and causal claims require human review.'}

    @app.get('/incidents/{incident_id}/investigations')
    def list_investigations(incident_id: int):
        if not store.events(incident_id):
            raise HTTPException(404, 'incident not found')
        return store.investigations(incident_id)

    @app.get('/investigations/{investigation_id}')
    def get_investigation(investigation_id: str):
        result = store.investigation(investigation_id)
        if result is None:
            raise HTTPException(404, 'investigation not found')
        return result

    return app


app = create_app()
