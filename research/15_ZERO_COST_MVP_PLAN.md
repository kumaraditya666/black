# ₹0 development MVP plan

Research proposal, not implemented. ₹0 in service fees is plausible for a single developer using existing hardware, open-source tools and a local model, if its quality is acceptable. Electricity, machine wear, developer time and internet are real costs; it is not a promise of free hosted operation.

## Scope and dependency order

1. Use an intentionally buggy local sample app and a pre-recorded synthetic incident; no production account, webhook or background hosting required.
2. Capture a bounded error event, stack and commit identifier via local OpenTelemetry or a controlled fixture; redact secrets and record timestamps and provenance.
3. Index a user-authorized local repository with symbols, filenames and full-text search; map a stack frame to source at a known commit. Show missing mapping explicitly.
4. Run one opt-in investigation using a local model where available, or a user-supplied API key with explicit consent and budget cap. Collect evidence deterministically; show competing hypotheses, cited snippets and an 'insufficient evidence' outcome.
5. Save a local report with observations, citations, assumptions and exact input versions. Human review precedes any later write action.
6. In a later phase, execute a demonstrably failing fixture and a proposed patch inside a disposable, resource-bounded environment. Report baseline, patched result and regressions separately. Do not equate a passing test with a verified production outcome.

Optional GitHub App integration requires deliberate setup and least-privilege authorization; draft PR creation remains out of the first local demonstration. A hosted service needs authentication, tenant isolation, persistent job handling, secret management, retention controls, abuse protection and a realistic cost budget. A local demo proves neither those controls nor a production-ready service.

## Exit checks

- A real recorded error navigates to a specific source revision, or displays a transparent missing-context state.
- Every factual diagnosis links to evidence; insufficient data produces abstention.
- Tests cover malicious instructions in logs and stale/missing commit references.
- No third-party model receives code or telemetry without explicit user choice.
- Report includes measured local runtime and resource consumption; no invented accuracy target or free-hosting claim.

Limit and policy sources: [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [Supabase pricing](https://supabase.com/pricing), [Vercel Hobby restrictions](https://vercel.com/docs/plans/hobby), all accessed 2026-11-04.
