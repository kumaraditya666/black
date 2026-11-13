const state = {
  incidents: [],
  selectedId: null,
  report: null,
  investigations: [],
  context: null,
  contextError: null,
  selectedInvestigation: null,
};

const main = document.querySelector('#main');
const incidentList = document.querySelector('#incident-list');
const incidentCount = document.querySelector('#incident-count');
const refreshButton = document.querySelector('#refresh');
const toastEl = document.querySelector('#toast');
let toastTimer = null;

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatDate(value) {
  if (!value) return 'unknown time';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function statusBadge(status) {
  const normalized = String(status || 'unknown').toLowerCase();
  const kind = normalized === 'completed' ? 'ok'
    : normalized === 'failed' ? 'error'
    : normalized === 'running' ? 'blue'
    : 'warn';
  return `<span class="badge ${kind}">${esc(normalized)}</span>`;
}

function toast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.classList.toggle('error', isError);
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), 4200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const text = await response.text();
  let body = {};
  try { body = text ? JSON.parse(text) : {}; } catch { body = { detail: text }; }
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (HTTP ${response.status})`);
  }
  return body;
}

function renderIncidentList() {
  incidentCount.textContent = String(state.incidents.length);
  if (!state.incidents.length) {
    incidentList.innerHTML = '<p class="panel-note" style="padding: 8px 8px;">No incidents yet.</p>';
    return;
  }
  incidentList.innerHTML = state.incidents.map((incident) => `
    <button class="incident-item ${incident.id === state.selectedId ? 'active' : ''}"
            type="button" data-incident="${esc(incident.id)}">
      <span class="incident-id">Incident ${esc(incident.id)}</span>
      <span class="incident-meta">${esc(incident.event_count)} event${Number(incident.event_count) === 1 ? '' : 's'}</span>
    </button>
  `).join('');
}

function renderEmpty() {
  state.report = null;
  state.investigations = [];
  state.context = null;
  state.selectedInvestigation = null;
  main.innerHTML = `
    <section class="empty-state">
      <div class="eyebrow">Ready</div>
      <h2>No incidents in this local evidence store.</h2>
      <p>Run the demo to create a real sample incident, then refresh this page.</p>
      <pre style="max-width: 560px;"><code>.\\\\.venv\\\\Scripts\\\\python scripts/demo.py</code></pre>
      <p class="panel-note" style="margin-top: 14px;">The same app is available from the CLI and at <a href="/docs">/docs</a>.</p>
    </section>
  `;
}

function renderFrameRow(frame, index, evidence) {
  const source = evidence?.[index] || {};
  const resolved = source.status === 'resolved';
  const status = resolved ? 'resolved' : (source.status || 'unresolved');
  const sourceLine = source.source_line
    ? `<div class="source-line">${esc(source.source_line)}</div>`
    : `<div class="source-reason">${esc(source.reason || 'source unavailable')}</div>`;
  return `
    <tr>
      <td><span class="path">${esc(frame.path)}</span><br><span class="source-status ${resolved ? '' : 'source-reason'}">${esc(status)}</span></td>
      <td>${esc(frame.line)}</td>
      <td>${esc(frame.function)}</td>
      <td>${sourceLine}</td>
    </tr>
  `;
}

function renderEvent(event) {
  const frames = Array.isArray(event.frames) ? event.frames : [];
  const evidence = Array.isArray(event.source_evidence) ? event.source_evidence : [];
  return `
    <article class="event">
      <div class="event-head">
        <div>
          <h3 class="event-title">${esc(event.exception_type)}</h3>
          <div class="event-time">${esc(formatDate(event.occurred_at || event.received_at))}</div>
        </div>
        <span class="badge warn">event</span>
      </div>
      <p class="event-message">${esc(event.message || '(empty message)')}</p>
      <div class="event-meta">
        <span class="badge">commit ${esc(String(event.commit || '').slice(0, 10))}</span>
        <span class="badge">${esc(frames.length)} frame${frames.length === 1 ? '' : 's'}</span>
        <span class="badge">${esc(event.event_id)}</span>
      </div>
      ${frames.length ? `
        <table class="frames" aria-label="Stack frames">
          <thead><tr><th>File</th><th>Line</th><th>Function</th><th>Pinned source</th></tr></thead>
          <tbody>${frames.map((frame, index) => renderFrameRow(frame, index, evidence)).join('')}</tbody>
        </table>
      ` : ''}
      ${event.traceback ? `
        <details>
          <summary>Recorded traceback</summary>
          <pre>${esc(event.traceback)}</pre>
        </details>
      ` : ''}
    </article>
  `;
}

function renderInvestigations() {
  if (!state.investigations.length) {
    return '<p class="panel-note">No investigations yet. Review the evidence and start one below.</p>';
  }
  return `<div class="investigation-list">${state.investigations.map((item) => `
    <button class="investigation-item ${item.id === state.selectedInvestigation?.id ? 'active' : ''}"
            type="button" data-investigation="${esc(item.id)}">
      <div class="investigation-top">
        <span class="badge ${item.status === 'completed' ? 'ok' : item.status === 'failed' ? 'error' : 'blue'}">${esc(item.status)}</span>
        <span class="investigation-meta">${esc(formatDate(item.updated_at || item.created_at))}</span>
      </div>
      <div class="investigation-model">${esc(item.provider)} / ${esc(item.model)}</div>
      <div class="investigation-meta">${esc(item.id)}</div>
    </button>
  `).join('')}</div>`;
}

function refs(label, values) {
  if (!Array.isArray(values) || !values.length) return '';
  return `<div class="refs">${esc(label)}: ${values.map(esc).join(', ')}</div>`;
}

function renderFindings(investigation) {
  if (investigation.status === 'running') {
    return '<p class="panel-note">Investigation is still running. Refresh to check again.</p>';
  }
  if (investigation.status === 'failed') {
    return `
      <div class="warning error-box">
        <strong>${esc(investigation.failure_kind || 'INVESTIGATION_FAILED')}</strong><br>
        ${esc(investigation.error || 'The investigation did not produce a validated result.')}
      </div>
    `;
  }
  const findings = investigation.findings;
  if (!findings) {
    return '<p class="panel-note">No validated findings were saved for this investigation.</p>';
  }
  const hypotheses = Array.isArray(findings.hypotheses) ? findings.hypotheses : [];
  const alternatives = Array.isArray(findings.alternatives) ? findings.alternatives : [];
  const missing = Array.isArray(findings.missing_evidence) ? findings.missing_evidence : [];
  const steps = Array.isArray(findings.verification_steps) ? findings.verification_steps : [];
  return `
    <div class="run-result">
      <p class="result-outcome"><span class="badge ${findings.outcome === 'LIKELY_CAUSE' ? 'ok' : 'warn'}">${esc(findings.outcome)}</span></p>
      <p class="result-text">${esc(findings.observed_failure?.text || '')}</p>
      ${refs('References', findings.observed_failure?.evidence_ids)}
      ${hypotheses.length ? `
        <div class="result-block">
          <h4>Primary hypotheses</h4>
          ${hypotheses.map((hypothesis) => `
            <p class="result-text">${esc(hypothesis.explanation)}</p>
            ${refs('Supporting', hypothesis.supporting_evidence)}
            ${refs('Contradicting', hypothesis.contradicting_evidence)}
          `).join('')}
        </div>
      ` : ''}
      ${alternatives.length ? `
        <div class="result-block">
          <h4>Alternatives</h4>
          ${alternatives.map((hypothesis) => `
            <p class="result-text">${esc(hypothesis.explanation)}</p>
            ${refs('Supporting', hypothesis.supporting_evidence)}
          `).join('')}
        </div>
      ` : ''}
      ${missing.length ? `
        <div class="result-block">
          <h4>Missing evidence</h4>
          <ul>${missing.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>
        </div>
      ` : ''}
      ${steps.length ? `
        <div class="result-block">
          <h4>Suggested verification</h4>
          <ul>${steps.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>
        </div>
      ` : ''}
      <p class="panel-note" style="margin-top: 14px;">Citations are checked against captured evidence. Narrative accuracy and causal claims still require human review.</p>
    </div>
  `;
}

function renderIncident() {
  const incident = state.incidents.find((item) => item.id === state.selectedId);
  if (!incident || !state.report) return;
  const events = Array.isArray(state.report.events) ? state.report.events : [];
  const contextHash = state.context?.evidence_hash;
  const contextWarning = state.context?.warning;
  const contextError = state.contextError;
  const selected = state.selectedInvestigation;
  main.innerHTML = `
    <section class="incident-header">
      <div>
        <div class="eyebrow">Local evidence</div>
        <h2>Incident ${esc(incident.id)}</h2>
        <p class="sub">${esc(incident.event_count)} recorded event${Number(incident.event_count) === 1 ? '' : 's'} in this stack signature.</p>
      </div>
      <div class="header-badges">
        <span class="badge ok">evidence only</span>
        <span class="badge">${esc(state.investigations.length)} investigation${state.investigations.length === 1 ? '' : 's'}</span>
      </div>
    </section>

    ${contextError ? `<div class="warning">Evidence context could not be built: ${esc(contextError)}</div>` : ''}

    <div class="grid">
      <div class="stack">
        <section class="panel">
          <div class="panel-head"><h3>Recorded events</h3><span class="panel-note">${esc(events.length)}</span></div>
          ${events.length ? events.map(renderEvent).join('') : '<p class="panel-body panel-note">No events recorded.</p>'}
        </section>

        <section class="panel">
          <div class="panel-head"><h3>Investigations</h3><span class="panel-note">human review required</span></div>
          <div class="panel-body">${renderInvestigations()}</div>
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <div class="panel-head"><h3>Run investigation</h3><span class="badge ${contextHash ? 'ok' : 'warn'}">${contextHash ? 'context ready' : 'context unavailable'}</span></div>
          <div class="panel-body">
            ${contextWarning ? `<p class="warning">${esc(contextWarning)}</p>` : ''}
            ${contextHash ? `
              <p class="panel-note">Review the exact evidence snapshot before sending it to the configured provider. The reviewed hash binds consent to this snapshot.</p>
              <details class="context-box">
                <summary>Preview evidence and hash</summary>
                <div class="refs">evidence_hash: ${esc(contextHash)}</div>
                <pre>${esc(JSON.stringify(state.context.context, null, 2))}</pre>
              </details>
              <label class="consent-row">
                <input id="consent" type="checkbox">
                <span>I reviewed every field above and approve sending this bounded snapshot to the configured provider.</span>
              </label>
              <label class="consent-row">
                <input id="force" type="checkbox">
                <span>Force a new run even if an identical evidence/provider/model result is cached.</span>
              </label>
              <button id="run-investigation" class="button button-primary" type="button" disabled>Start investigation</button>
              <p class="panel-note" style="margin-top: 10px;">Local Ollama stays on this machine. A configured cloud provider receives the snapshot above.</p>
            ` : `
              <p class="panel-note">The incident report is available, but the investigation context could not be built. Check the configured Git repository and commit.</p>
            `}
          </div>
        </section>

        ${selected ? `
          <section class="panel" id="investigation-detail">
            <div class="panel-head">
              <h3>Selected investigation</h3>
              ${statusBadge(selected.status)}
            </div>
            <div class="panel-body">
              <p class="investigation-meta">${esc(selected.provider)} / ${esc(selected.model)} · ${esc(formatDate(selected.updated_at || selected.created_at))}</p>
              ${renderFindings(selected)}
            </div>
          </section>
        ` : ''}
      </div>
    </div>
  `;

  const consent = document.querySelector('#consent');
  if (consent) {
    consent.addEventListener('change', () => {
      document.querySelector('#run-investigation').disabled = !consent.checked;
    });
  }
}

async function showInvestigation(id) {
  try {
    state.selectedInvestigation = await api(`/investigations/${encodeURIComponent(id)}`);
    renderIncident();
  } catch (error) {
    toast(error.message, true);
  }
}

async function runInvestigation() {
  const consent = document.querySelector('#consent');
  const force = document.querySelector('#force');
  const button = document.querySelector('#run-investigation');
  if (!consent?.checked || !state.context?.evidence_hash) {
    toast('Review the evidence and check the consent box first.', true);
    return;
  }
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> Running…';
  try {
    const result = await api(`/incidents/${state.selectedId}/investigations`, {
      method: 'POST',
      body: JSON.stringify({
        consent_external: true,
        reviewed_evidence_hash: state.context.evidence_hash,
        force: Boolean(force?.checked),
      }),
    });
    toast(result.cached ? 'Loaded the cached investigation.' : 'Investigation completed.');
    await loadInvestigations();
    state.selectedInvestigation = result.investigation || null;
    if (state.selectedInvestigation) renderIncident();
  } catch (error) {
    toast(error.message, true);
    button.disabled = false;
    button.textContent = 'Start investigation';
  }
}

async function loadInvestigations() {
  state.investigations = await api(`/incidents/${state.selectedId}/investigations`);
}

async function selectIncident(id) {
  state.selectedId = Number(id);
  state.selectedInvestigation = null;
  state.report = null;
  state.investigations = [];
  state.context = null;
  state.contextError = null;
  renderIncidentList();
  main.innerHTML = '<section class="empty-state"><div class="eyebrow">Loading</div><h2>Loading incident…</h2></section>';
  try {
    const [report, investigations] = await Promise.all([
      api(`/incidents/${state.selectedId}/report`),
      api(`/incidents/${state.selectedId}/investigations`),
    ]);
    state.report = report;
    state.investigations = investigations;
    try {
      state.context = await api(`/incidents/${state.selectedId}/context`);
    } catch (error) {
      state.contextError = error.message;
    }
    renderIncident();
  } catch (error) {
    main.innerHTML = `<section class="empty-state"><div class="eyebrow">Error</div><h2>Could not load incident.</h2><p>${esc(error.message)}</p></section>`;
  }
}

async function loadIncidents() {
  try {
    state.incidents = await api('/incidents');
    renderIncidentList();
    if (!state.incidents.length) {
      renderEmpty();
      return;
    }
    const preferred = state.incidents.some((item) => item.id === state.selectedId)
      ? state.selectedId : state.incidents[0].id;
    await selectIncident(preferred);
  } catch (error) {
    main.innerHTML = `<section class="empty-state"><div class="eyebrow">Error</div><h2>Could not reach the local API.</h2><p>${esc(error.message)}</p></section>`;
  }
}

incidentList.addEventListener('click', (event) => {
  const button = event.target.closest('[data-incident]');
  if (button) selectIncident(button.dataset.incident);
});

main.addEventListener('click', (event) => {
  const investigation = event.target.closest('[data-investigation]');
  if (investigation) {
    showInvestigation(investigation.dataset.investigation);
    return;
  }
  if (event.target.closest('#run-investigation')) runInvestigation();
});

refreshButton.addEventListener('click', loadIncidents);
loadIncidents();
