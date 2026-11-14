const state = { signup: true, user: null, projects: [], project: null, issue: null };
const $ = (selector) => document.querySelector(selector);
const auth = $('#auth');
const app = $('#app');
const toastEl = $('#toast');

function esc(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

function fmt(value) {
  if (!value) return 'unknown';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat(undefined,
    { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function toast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.classList.toggle('error', isError);
  toastEl.classList.add('show');
  clearTimeout(toastEl.timer);
  toastEl.timer = setTimeout(() => toastEl.classList.remove('show'), 4000);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: options.body ? { 'Content-Type': 'application/json' } : {},
    credentials: 'same-origin',
    ...options,
  });
  const text = await response.text();
  let body = {};
  try { body = text ? JSON.parse(text) : {}; } catch { body = { detail: text }; }
  if (!response.ok) {
    const error = new Error(typeof body.detail === 'string' ? body.detail : `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function showAuth() {
  state.user = null;
  auth.hidden = false;
  app.hidden = true;
  $('#logout').hidden = true;
}

function showApp(user) {
  state.user = user;
  auth.hidden = true;
  app.hidden = false;
  $('#logout').hidden = false;
  $('#user-email').textContent = user.email;
  loadProjects();
}

function renderProjectList() {
  const list = $('#project-list');
  if (!state.projects.length) {
    list.innerHTML = '<p class="fine" style="padding:8px">No projects yet.</p>';
    return;
  }
  list.innerHTML = state.projects.map((project) => `
    <button class="project-item ${state.project?.id === project.id ? 'active' : ''}" data-project="${project.id}" type="button">
      <b>${esc(project.name)}</b>
      <small>${esc(project.key_prefix)}…</small>
    </button>
  `).join('');
}

function renderEmptyProject() {
  $('#content-head').innerHTML = '<div><div class="eyebrow">Workspace</div><h2>Select a project</h2></div>';
  $('#content-body').innerHTML = '<div class="empty"><h3>Create your first project</h3><p>Projects separate API keys, events and issues.</p></div>';
}

function renderIssues() {
  const project = state.project;
  $('#content-head').innerHTML = `<div><div class="eyebrow">Project</div><h2>${esc(project.name)}</h2><p>${esc(project.repo_path || 'No repository path configured')}</p></div>
    <span class="badge">${esc(project.key_prefix)}…</span>`;
  if (!state.issues.length) {
    $('#content-body').innerHTML = `<div class="empty"><h3>No issues yet</h3><p>Send an exception to <code>/api/ingest</code> with the project key.</p></div>`;
    return;
  }
  $('#content-body').innerHTML = `<section class="panel"><div class="panel-head"><span>Issues</span><span>${state.issues.length}</span></div>
    <div class="issue-list">${state.issues.map((issue) => `
      <button class="issue-row" data-issue="${issue.id}" type="button">
        <span><b>${esc(issue.exception_type)}</b><small>last seen ${esc(fmt(issue.last_seen))}</small></span>
        <span class="count">${esc(issue.event_count)} event${Number(issue.event_count) === 1 ? '' : 's'}</span>
      </button>`).join('')}
    </div></section>`;
}

function renderEvent(event, index) {
  const frames = Array.isArray(event.frames) ? event.frames : [];
  const sources = Array.isArray(event.source_evidence) ? event.source_evidence : [];
  return `<div class="event">
    <h4>Event ${index + 1} · ${esc(event.exception_type)}</h4>
    <div class="meta">${esc(fmt(event.occurred_at))} · ${esc(event.commit.slice(0, 10))}</div>
    <p>${esc(event.message || '(no message)')}</p>
    <table class="frames"><thead><tr><th>File</th><th>Line</th><th>Function</th><th>Pinned source</th></tr></thead><tbody>
      ${frames.map((frame, i) => {
        const source = sources[i] || {};
        return `<tr><td>${esc(frame.path)}</td><td>${esc(frame.line)}</td><td>${esc(frame.function)}</td>
          <td>${source.source_line ? `<span class="source">${esc(source.source_line)}</span>` : `<span class="reason">${esc(source.reason || 'unresolved')}</span>`}</td></tr>`;
      }).join('')}
    </tbody></table>
    ${event.traceback ? `<details><summary>Traceback</summary><pre>${esc(event.traceback)}</pre></details>` : ''}
  </div>`;
}

function renderIssue() {
  const issue = state.issue;
  const project = state.project;
  $('#content-head').innerHTML = `<div><div class="eyebrow">Issue #${issue.id}</div><h2>${esc(issue.exception_type)}</h2><p>${esc(project.name)} · ${esc(issue.event_count)} events</p></div>
    <button id="explain" class="primary" type="button">Explain with AI</button>`;
  const ai = issue.ai;
  $('#content-body').innerHTML = `<section class="panel detail">
    <div class="event"><div class="meta">First seen ${esc(fmt(issue.first_seen))} · Last seen ${esc(fmt(issue.last_seen))}</div></div>
    ${(issue.events || []).map(renderEvent).join('')}
    ${ai ? `<div class="ai"><h4>AI explanation · ${esc(ai.confidence)} confidence</h4>
      <p><b>Summary:</b> ${esc(ai.summary)}</p><p><b>Likely cause:</b> ${esc(ai.likely_cause)}</p>
      <p><b>Suggested fix:</b> ${esc(ai.fix)}</p>${(ai.evidence || []).length ? `<p class="fine">${esc(ai.evidence.join(' · '))}</p>` : ''}</div>` : ''}
  </section>`;
}

async function loadProjects() {
  try {
    state.projects = await api('/api/projects');
    renderProjectList();
    if (state.project) {
      const still = state.projects.find((item) => item.id === state.project.id);
      if (!still) { state.project = null; state.issues = []; renderEmptyProject(); }
    }
  } catch (error) {
    if (error.status === 401) showAuth(); else toast(error.message, true);
  }
}

async function selectProject(id) {
  state.project = state.projects.find((item) => item.id === Number(id));
  state.issue = null;
  renderProjectList();
  if (!state.project) return;
  try {
    state.issues = await api(`/api/projects/${state.project.id}/issues`);
    renderIssues();
  } catch (error) {
    if (error.status === 401) showAuth(); else toast(error.message, true);
  }
}

async function selectIssue(id) {
  try {
    state.issue = await api(`/api/issues/${id}`);
    renderIssue();
  } catch (error) {
    if (error.status === 401) showAuth(); else toast(error.message, true);
  }
}

async function explainIssue() {
  if (!state.issue) return;
  const button = $('#explain');
  button.disabled = true;
  button.textContent = 'Analyzing…';
  try {
    const result = await api(`/api/issues/${state.issue.id}/explain`, { method: 'POST' });
    state.issue.ai = result.ai;
    renderIssue();
    toast('AI explanation saved.');
  } catch (error) {
    toast(error.message, true);
    button.disabled = false;
    button.textContent = 'Explain with AI';
  }
}

$('#auth-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const errorEl = $('#auth-error');
  errorEl.textContent = '';
  const submit = $('#auth-submit');
  submit.disabled = true;
  submit.textContent = state.signup ? 'Creating…' : 'Signing in…';
  try {
    const user = await api(state.signup ? '/api/auth/signup' : '/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: $('#email').value, password: $('#password').value }),
    });
    showApp(user.user);
  } catch (error) {
    errorEl.textContent = error.message;
  } finally {
    submit.disabled = false;
    submit.textContent = state.signup ? 'Create account' : 'Sign in';
  }
});

$('#switch-auth').addEventListener('click', () => {
  state.signup = !state.signup;
  $('#auth-title').textContent = state.signup ? 'Create an account' : 'Welcome back';
  $('#auth-submit').textContent = state.signup ? 'Create account' : 'Sign in';
  $('#switch-auth').textContent = state.signup ? 'Already have an account? Sign in' : 'Need an account? Create one';
  $('#password').autocomplete = state.signup ? 'new-password' : 'current-password';
  $('#auth-error').textContent = '';
});

$('#logout').addEventListener('click', async () => {
  try { await api('/api/auth/logout', { method: 'POST' }); } catch { /* local cleanup */ }
  state.user = null;
  state.projects = [];
  state.project = null;
  state.issues = [];
  renderEmptyProject();
  showAuth();
});

$('#new-project').addEventListener('click', () => $('#project-dialog').showModal());
$('#cancel-project').addEventListener('click', () => $('#project-dialog').close());
$('#project-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const result = await api('/api/projects', {
      method: 'POST',
      body: JSON.stringify({ name: $('#project-name').value, repo_path: $('#project-repo').value }),
    });
    $('#project-dialog').close();
    $('#project-key').textContent = result.key;
    $('#ingest-url').textContent = `${location.origin}/api/ingest`;
    $('#key-dialog').showModal();
    await loadProjects();
    await selectProject(result.id);
  } catch (error) {
    toast(error.message, true);
  }
});
$('#close-key').addEventListener('click', () => $('#key-dialog').close());

$('#project-list').addEventListener('click', (event) => {
  const button = event.target.closest('[data-project]');
  if (button) selectProject(button.dataset.project);
});
$('#content-body').addEventListener('click', (event) => {
  const issue = event.target.closest('[data-issue]');
  if (issue) selectIssue(issue.dataset.issue);
});
$('#content-head').addEventListener('click', (event) => {
  if (event.target.closest('#explain')) explainIssue();
});

(async () => {
  try {
    const result = await api('/api/me');
    if (result.user) showApp(result.user); else showAuth();
  } catch { showAuth(); }
})();
