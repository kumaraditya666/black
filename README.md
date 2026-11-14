# BLACKBOX â€” local evidence and AI investigation

Milestone 1 captures a real sample exception and resolves its frames against an exact Git commit. That milestone does not determine root cause or make repairs; later milestones add a reviewed AI investigation and a restricted, test-verified repair workflow. The sample is intentionally broken and all sample reports are demonstrations.

## Setup

Requires Python 3.11 or newer and Git. From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` in place of `.\.venv\Scripts\python`.

## One-command demo

```powershell
.\.venv\Scripts\python scripts/demo.py
```

The script creates `sample_repo/` as an independent Git repository from `sample_template/` if it does not already exist, commits the intentionally buggy application with a local demo identity, starts FastAPI on `127.0.0.1:18765`, executes the sample, posts its actual exception, prints the report, saves `data/investigation-report.json` and stops the server. It refuses to overwrite a nonempty uninitialized sample directory or use a modified sample file. Repeated runs add separate events to a matching incident. SQLite data persists in `data/events.db`. Port 18765 must be free.

## Run the service and tests

```powershell
.\.venv\Scripts\python -m uvicorn blackbox.app:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python -m pytest -q
```

Set `BLACKBOX_DB` and `BLACKBOX_REPO` to select the database and an authorized local Git repository; defaults are `data/events.db` and `sample_repo`. Interactive API documentation is at `http://127.0.0.1:8000/docs`. `POST /events` accepts a UUID `event_id`, timezone-aware `occurred_at`, full 40-character lowercase Git commit SHA, exception type, message, traceback and repository-relative POSIX stack frames. `GET /incidents/{id}/report` returns stored events and source evidence. Schema validation errors return 422. Reposting the same redacted payload and ID is idempotent; reusing an ID for different redacted content returns 409. Distinct IDs with the same exception type and ordered frame path, line and function are grouped into one incident; commit and message do not affect grouping. A changed stack may create a different incident.

The resolver reads committed Git objects, never working-tree content. Missing commits, files, lines, Git errors, binary files and oversized source files are explicitly reported unresolved. Repository location is configured on the server, not supplied per event. Reports resolve on request; retain the repository and referenced Git objects for later access.

## Capture exceptions from your own FastAPI app

Start the local API against your repository. The launcher uses `data/blackbox-local.db` and local Ollama by default; pass `-NoAi` for evidence collection only:

```powershell
.\scripts\start_local.ps1 -Repo C:\path\to\your\repo
```

Add the capture middleware once, at app startup:

```python
from blackbox.capture import install_blackbox

install_blackbox(app)
```

Run your app with these environment variables. `PYTHONPATH` lets your app import this project's `blackbox` package:

```powershell
$env:BLACKBOX_REPO = 'C:\path\to\your\repo'
$env:BLACKBOX_API_URL = 'http://127.0.0.1:8000/events'
$env:PYTHONPATH = 'C:\Users\Adi\Documents\ChatGPT\black'
.\.venv\Scripts\python -m uvicorn your_app:app --host 127.0.0.1 --port 8100
```

The middleware captures unhandled exceptions only. It always re-raises the original error, skips dependency, virtualenv and capture-internal frames, and logs capture failures without changing the application response. The endpoint must be loopback and the repository must contain the full commit that produced the error. Handled `HTTPException` responses are not failures and are not captured.

The included demo exercises the full path:

```powershell
$env:BLACKBOX_REPO = (Get-Location).Path
$env:BLACKBOX_API_URL = 'http://127.0.0.1:8000/events'
.\.venv\Scripts\python -m uvicorn examples.fastapi_capture_demo:app --host 127.0.0.1 --port 8100
```

In another window, trigger its real `ZeroDivisionError`, then inspect the resulting incident:

```powershell
curl.exe -s -o NUL -w "status=%{http_code}`n" http://127.0.0.1:8100/crash
.\.venv\Scripts\python scripts/investigate.py list
.\.venv\Scripts\python scripts/investigate.py preview 1
```

## Limits

This is a local, single-user prototype with no authentication or tenant isolation; do not expose it on a public network or use production secrets. Redaction is a best-effort set of patterns for common key/value secrets and token formats, not a guarantee against all secrets, personal data, multiline credentials or secrets embedded in arbitrary file paths. Minimize data before sending it, and inspect reports before sharing. Validation errors may echo invalid input. Exact duplicates are compared after redaction, so two payloads differing only in redacted values are indistinguishable. Existing SQLite files, the sample Git history and generated reports are not encrypted or automatically deleted. Event grouping is a simple stack signature and is not causal analysis. Incoming frames are client-provided evidence, not proof the reported code actually executed. Only one configured local repository is supported, and only full SHA-1 Git commits are accepted. Repair is a restricted local proposal-and-test workflow on pinned trusted fixtures; there is no merge, pull request, deployment or autonomous repair permission.

## AI investigation (opt-in)

Install requirements in the venv as above. Start the server on `127.0.0.1:8000`, then list incidents and preview the bounded evidence:

```powershell
.\.venv\Scripts\python scripts/investigate.py list
.\.venv\Scripts\python scripts/investigate.py preview 1
```

Configure the provider and model in the server's shell **before starting** the server. For Ollama, install and run it locally and choose an installed model:

```powershell
$env:BLACKBOX_AI_PROVIDER='ollama'
$env:BLACKBOX_AI_MODEL='<your installed model name>'
.\.venv\Scripts\python -m uvicorn blackbox.app:app --host 127.0.0.1 --port 8000
```

For this project's selected `qwen3.5:4b` model, `./scripts/start_ollama.ps1` starts the server with a 2,048-token context window and a 120-second local inference timeout after the model and `.venv` are installed. The 9B model remains available for custom launches. The adapter disables thinking and rejects truncated output. The output budget is adaptive: `min(768, context âˆ’ estimated prompt âˆ’ 64)`, estimated conservatively at 3.5 characters per token, with a 320-token minimum. A prompt that cannot fit a complete result fails with `EVIDENCE_TOO_LARGE` instead of silently dropping evidence. Set `BLACKBOX_OLLAMA_CONTEXT_LENGTH` to a value from 1,024 to 32,768 and `BLACKBOX_OLLAMA_TIMEOUT_SECONDS` to a value from 1 to 600 for custom launches; a larger context uses more memory. The investigation cache does not distinguish different context lengths, so use `--force` after changing it.

For Gemini use `$env:BLACKBOX_AI_PROVIDER='gemini'`, set `BLACKBOX_AI_MODEL` to a model available to your account and `GEMINI_API_KEY` to your key. Do not put credentials in source control. See [.env.example](.env.example); it is documentation and is not automatically loaded. [Gemini model documentation](https://ai.google.dev/gemini-api/docs/models) and [pricing](https://ai.google.dev/gemini-api/docs/pricing) change; eligibility, free limits and data-use terms vary. Free tier data may be used to improve Google's products. Check your account before using it.

For Ollama run `python scripts/investigate.py start 1`. For Gemini, **manually inspect every field** in `preview 1` for secrets and private information, then explicitly authorize that exact preview using `python scripts/investigate.py start 1 --consent-external-hash <evidence_hash>`. If evidence changes, fetch and review a new preview. The transmitted snapshot contains the latest event message, occurrence summary, revision, stack frames and up to five lines around each of at most ten frames. Full raw tracebacks and entire repositories are not sent. Automated redaction is incomplete; consent does not make sensitive data safe to send. Do not approve any snapshot containing secrets or information you cannot share. No provider gets tools, shell access, repository write access or PR permissions. Ollama URLs are limited to local HTTP.

Use `python scripts/investigate.py history 1` and `python scripts/investigate.py show <investigation-id>` to inspect persisted results and evidence. `--force` starts a new run; otherwise identical completed evidence/provider/model snapshots are cached. Failed attempts are retained; runs interrupted for fifteen minutes are marked failed on the next request. Requests are synchronous, use bounded provider timeouts and have no application retry. Missing provider configuration returns HTTP 503; errors and invalid output yield a persisted failed attempt. Results include latency, token counts when returned and unknown cost. Schema and reference checks validate IDs and some explicit references, not semantic truth: model narratives may still be wrong. All hypotheses require human review. Deployment context and comprehensive dependency indexing are unavailable.

Investigation outcomes are `LIKELY_CAUSE`, `INSUFFICIENT_EVIDENCE`, `ROOT_CAUSE_SUPPORTED`, and `INVESTIGATION_FAILED`. A likely cause must cite the incident event and resolved source for each primary hypothesis; abstention requires missing information and no primary cause. `ROOT_CAUSE_SUPPORTED` is reserved for future independently verified evidence and is currently rejected, so the model cannot declare its own hypothesis verified. Runtime or validation failures are surfaced as `INVESTIGATION_FAILED` without a generated diagnosis. Historic results created before this schema are displayed as `LEGACY_UNCLASSIFIED` and remain intact.

A result also carries `atomic_claims`: typed facts read directly from the recorded event, the client-reported frames and the pinned Git revision, each with its evidence IDs, a verification status (`RECORDED`, `VERIFIED_SOURCE`, `STATIC_ONLY`) and a provenance entry naming the record, revision and resolution status. Model-written observations are never displayed as facts: `observed_facts` is empty, `observed_failure` is the exact recorded exception, and every hypothesis is labelled `HYPOTHESIS_REQUIRES_REVIEW`. The model-facing schema bounds `observed_facts` and `verification_steps` to three items, so constrained decoding cannot enumerate a list long enough to truncate the response. `diagnosis_source` is `MODEL` for a validated model result. A failed investigation keeps `outcome: INVESTIGATION_FAILED` together with the deterministic claims and no model prose (`diagnosis_source: DETERMINISTIC_FALLBACK`), and `failure_kind` separates `INVALID_MODEL_RESPONSE`, `PROVIDER_TIMEOUT`, `PROVIDER_UNAVAILABLE`, `PROVIDER_FAILURE` and `EVIDENCE_TOO_LARGE`. A truncated completion keeps its token counters in `usage`, so a cutoff is measurable rather than silent. `dropped_observation_count` counts model observations discarded because their references were unknown, empty or malformed; unverifiable references in a displayed hypothesis or alternative still fail the investigation, and an invalid output is never counted as an abstention.

The evidence collector also checks up to three direct same-file Python name matches for the innermost resolved frame, using the recorded Git commit. These static matches are incomplete and are not proof that a call was executed or that a name resolved to a specific function. Files are bounded in size; unsupported or unparseable files produce no static matches. A matching frame reported by a client is not independently verified runtime execution. A narrative that attaches a recorded frame line to a different recorded function, or names a function a cited frame does not record, is rejected. Inspect cited evidence and model statements separately; existence of an ID does not prove a narrative claim.

For a separate real-model check run `python scripts/live_evaluate.py 1` (with the same consent hash option for Gemini). It reports actual run status and usage; correctness, abstention and unsupported-claim rates remain unscored until a human adjudicates independently labeled cases. Automated tests use mocked model responses and must not be presented as live AI accuracy measurements. The ten scenario descriptions and three toy programs are in `tests/fixtures/`.

`python scripts/evaluate_m28.py` runs the same five synthetic payloads plus the recorded incident into `data/milestone28-evaluation.db` and saves latency, token usage, status and validation results in `data/milestone28-run.json`. `python scripts/diagnose_m28.py <incident> --db <path>` prints one raw local-model response and its exact validation failure without persisting either; use it only with local synthetic evidence.

`python scripts/evaluate_m29.py --mode replay` re-runs each 2.8 scenario three times against the exact stored evidence snapshots and asserts each replayed `evidence_hash` matches; `--mode fresh` builds equivalent snapshots with fixed IDs and timestamps in per-scenario databases. `--runs`, `--output` and `--extra` adjust the repetition count, artifact path and two unseen generalization scenarios. Both write `data/milestone29-run.json` and `data/milestone29-replay-run.json` with per-run latency, tokens, status, validity, abstention, evidence hash and fact digest. The measurements and their limits are in [research/25_M29_STABILITY_EVALUATION.md](research/25_M29_STABILITY_EVALUATION.md).

`python scripts/evaluate_m27.py` runs five labeled synthetic cases against the configured provider and stores them in `data/milestone27-evaluation.db`, separately from the original incident database. It sends their text to the configured provider; use Ollama locally for this evaluation. Review results in `data/milestone27-live-cases.json`. The synthetic events are not production failures, the set is tiny and repeated runs can accumulate incident history, so do not generalize its results into product-wide accuracy claims.

## Restricted Proof-of-Fix (Milestone 3A)

Repair is a separate, opt-in workflow. It is allowed only when an investigation is `completed` with outcome `LIKELY_CAUSE`, a human review record matches the exact hypothesis and evidence hashes, the cited source frame is resolved at the recorded revision, every evidence reference resolves, every fixture file matches its pinned content hash, and the repository is the trusted fixture repository in this project. `INVESTIGATION_FAILED`, `INSUFFICIENT_EVIDENCE`, stale approvals, missing revisions, unresolved frames, invalid references and untrusted repositories are hard blocks. Model confidence is never treated as proof.

Start from a stored investigation ID (use `scripts/investigate.py history <incident>` to find one):

```powershell
python scripts/repair_cli.py eligibility <investigation-id> --fixture division_by_zero
python scripts/repair_cli.py approve <investigation-id> --hypothesis 0 --reviewer <name>
# The first call prints the hypothesis hash; review the text, then re-run with --confirm-hash <hash>.
python scripts/repair_cli.py attempt <investigation-id> --fixture division_by_zero
python scripts/repair_cli.py show <attempt-id>
python scripts/repair_cli.py review <attempt-id> --decision accept --reviewer <name>
python scripts/repair_cli.py list
```

A `show` report contains the original incident, approved hypothesis and reviewer, proposed changes, unified diff, reproduction output before and after the patch, regression output, exact revision, status, timings, token usage and remaining risks. Review records a developer decision but cannot change the test-derived status.

The patch generator receives only verified records, the approved hypothesis, pinned source, allowed files, expected behaviour and the trusted reproduction test. It must return a bounded structured proposal of exact `find`/`replace` changes. Paths outside the allowed files, test edits, missing or repeated `find` text, unsafe process/network/dynamic-code constructs, invalid Python and oversized diffs are rejected before writing. No model-proposed shell command is executed, and the real repository is never modified.

Statuses are `VERIFIED_IN_TEST_ENVIRONMENT` (reproduction failed before, passed after, regression passed), `PATCH_FAILED`, `UNVERIFIED` (the bug was not reproduced), `ENVIRONMENT_FAILED`, `PATCH_REJECTED`, `GENERATION_FAILED` and `ELIGIBILITY_BLOCKED`. `VERIFIED_IN_TEST_ENVIRONMENT` is not production success or proof that the tests are adequate.

`BLACKBOX_REPAIR_ISOLATION` selects `auto`, `docker` or explicit `process`. Auto requires Docker and never silently falls back. Docker execution requires `BLACKBOX_REPAIR_DOCKER_IMAGE_ID` set to an explicitly approved full local `sha256:` image ID with Python and pytest. The runner forces UID/GID 65534, checks container settings and effective security state, and journals each owned container. If cleanup is uncertain, new Docker runs are blocked. After confirming no repair is active and Docker is connected to the original daemon, an operator may run `python -m blackbox.repair.execution --recover`; inspect the pending journal and audit first. Abrupt host termination or daemon failure can prevent immediate cleanup. Explicit process mode is a cooperative jail without OS-level confinement, permitted only for pinned trusted fixtures. General-purpose untrusted repair remains blocked.

`fixtures/repair/registry.json` pins every fixture file by SHA-256; `pytest.ini` keeps these disposable fixture suites out of the project test run. `python scripts/evaluate_m3a.py --approve-all` runs the five real model cases and writes `data/milestone3a-run.json`. Benchmark approvals are fixture-level and are not evidence of human review. There is no merge, pull request, deployment, dashboard or autonomous repair permission. Measurements and limits are in [research/27_M3A_PROOF_OF_FIX.md](research/27_M3A_PROOF_OF_FIX.md).
