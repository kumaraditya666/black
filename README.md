# BLACKBOX — local evidence and AI investigation

Milestone 1 captures a real sample exception and resolves its frames against an exact Git commit. It does not determine root cause or make repairs. The sample is intentionally broken and all sample reports are demonstrations.

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

## Limits

This is a local, single-user prototype with no authentication or tenant isolation; do not expose it on a public network or use production secrets. Redaction is a best-effort set of patterns for common key/value secrets and token formats, not a guarantee against all secrets, personal data, multiline credentials or secrets embedded in arbitrary file paths. Minimize data before sending it, and inspect reports before sharing. Validation errors may echo invalid input. Exact duplicates are compared after redaction, so two payloads differing only in redacted values are indistinguishable. Existing SQLite files, the sample Git history and generated reports are not encrypted or automatically deleted. Event grouping is a simple stack signature and is not causal analysis. Incoming frames are client-provided evidence, not proof the reported code actually executed. Only one configured local repository is supported, and only full SHA-1 Git commits are accepted. No code repair or deployment is involved.

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

For this project's selected `qwen3.5:4b` model, `./scripts/start_ollama.ps1` starts the server with a 2,048-token context window and a 120-second local inference timeout after the model and `.venv` are installed. The 9B model remains available for custom launches. The adapter disables thinking and rejects truncated output. The output budget is adaptive: `min(768, context − estimated prompt − 64)`, estimated conservatively at 3.5 characters per token, with a 320-token minimum. A prompt that cannot fit a complete result fails with `EVIDENCE_TOO_LARGE` instead of silently dropping evidence. Set `BLACKBOX_OLLAMA_CONTEXT_LENGTH` to a value from 1,024 to 32,768 and `BLACKBOX_OLLAMA_TIMEOUT_SECONDS` to a value from 1 to 600 for custom launches; a larger context uses more memory. The investigation cache does not distinguish different context lengths, so use `--force` after changing it.

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
