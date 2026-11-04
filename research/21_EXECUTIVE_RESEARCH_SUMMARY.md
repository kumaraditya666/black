# Executive research summary

Research date: 2026-11-04. Scope: public sources, limited browser observation and scoped open-source analysis. This is a research baseline, not exhaustive product testing.

**CONFIRMED:** Sentry publicly describes Seer as investigating application issues using monitoring and code context, with proposed solutions and code changes. Its documented issue-fix API supports root cause, solution, code changes and PR stages. Exact private architecture, universal approvals and guaranteed reproduction remain **UNKNOWN**. See [journeys](03_SEER_USER_JOURNEYS.md).

**Observed:** public page and initial demo frames; one demo interaction timed out. No signed-in investigation was exercised. See reports 02–05.

**Open source:** OpenTelemetry describes receivers, processors and exporters. Scoped Graphify analysis of Sentry MCP and direct source inspection found an API helper using contextual credentials and validating an optional region URL. Neither establishes hosted topology. See reports 08–09.

**Proposed:** start with one instrumented test application, repository read access, commit-aware search, redacted events and evidence-linked investigation with abstention. Add isolated reproduction, patch checks and approved draft PRs after the core is reliable. Grafana already documents citations and diagrams; the value of stronger proof-of-fix, synthetic journeys and layered explanations remains a hypothesis requiring user research.

**Risks:** privacy, prompt injection, untrusted test execution, nondeterministic reproduction, missing evidence, overconfidence, pricing changes and benchmark contamination. The evaluation plan proposes measurements rather than invented results.

**₹0 feasibility:** conditional for local development with existing hardware and open-source components. Hosting, model inference and scaling may cost money; free-tier terms change. See reports 14–15.

**Next-phase skills:** observability, backend, GitHub integration, security and sandboxing, AI retrieval and evaluation, accessible frontend design, browser testing and product research. No application was built.
