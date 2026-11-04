# Product requirements — research-stage proposal

**Audience:** developers and small teams who can instrument a test application and authorize repository access. **Goal:** reduce time spent locating and checking a reported failure while preserving human control. **Non-goal:** autonomous production deployment or guaranteed diagnosis.

## Core requirements
- Every incident has a source, time, release/commit when known, ingestion status and visible missing fields.
- Every AI claim must cite inspectable evidence or be marked as unsupported; hypotheses and observations must be separate. An investigation may abstain.
- Scope repository credentials to selected repositories; revoke access and delete stored data on request according to a defined retention policy.
- Show real observed data only. No invented incidents, metrics or test results.
- All test runs use an isolated environment with quotas, restricted network and no production secrets; show sandbox failures distinctly.
- Require explicit approval for external writes, including draft PRs. Record actor, action, revision and outcome.
- Display patch generation, static checks, tests, reproduction and production outcomes separately, with logs and limitations.
- On missing telemetry, integration failure or model error, preserve available evidence and provide a retry or manual path.

**Release criteria:** measurable on held-out reproducible cases; security boundaries tested against malicious repository and telemetry inputs; privacy and cost limits reviewed; no success rate invented in advance.
