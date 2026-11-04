# Competitive gap analysis

Sources accessed 2026-11-04. CONFIRMED refers to vendor-described functionality, not independently tested efficacy. UNKNOWN means not verified, not absent.

| Product | Documented investigation and evidence | Code / verification | Pricing and scope |
|---|---|---|---|
| Sentry Seer | Production telemetry and code context, agent and Autofix described on [product page](https://sentry.io/product/seer/). | Page describes fixes and code review; actual test verification and CI handling UNKNOWN. | [Pricing](https://sentry.io/pricing/); exact Seer entitlement/limits require verification at purchase. |
| Datadog Bits | Investigates alerts; integrates source and other data; role controls, audit events and per-monitor rate limits documented. | [Bits integration](https://docs.datadoghq.com/bits_ai/bits_investigation/configure/) says source access required for Bits Code fix generation; tests UNKNOWN. | [AI credits](https://docs.datadoghq.com/account_management/billing/ai_credits/), plus relevant platform products; exact entitlement/rates need account verification. |
| Grafana Assistant Investigations | Cross-signal hypotheses, query-linked citations, user corrections and reports documented. | GitHub MCP can supply source context; independent repair verification UNKNOWN. | Usage-based [Assistant pricing](https://grafana.com/docs/grafana-cloud/platform/grafana-assistant/pricing/); allowances and rates depend on plan. |
| Dynatrace Intelligence | [Causal topology root-cause analysis](https://docs.dynatrace.com/docs/dynatrace-intelligence/root-cause-analysis). | Repair and tests UNKNOWN. | [Pricing model](https://www.dynatrace.com/pricing/) varies by capability and usage; quote required for comparison. |
| Resolve AI | [AI SRE](https://resolve.ai/product/ai-sre) describes incident investigation across environment. | Code changes and proof of repair UNKNOWN. | Product page asks users to get pricing; no verified public unit price. |
| New Relic Autopilot | [Autopilot](https://docs.newrelic.com/docs/agentic-ai/autopilot/overview/) describes investigation, diagnosis and remediation using telemetry. | Verification details UNKNOWN; [MCP](https://docs.newrelic.com/docs/agentic-ai/mcp/overview/) exposes selected data tools. | [Pricing](https://newrelic.com/pricing); AI-specific current allowance UNKNOWN. |
| Proposed product | Evidence-linked hypotheses with explicit abstention; initially one repository and controlled event input. | Reproduction and isolated before/after tests as later gated capability; human approves all PRs. | Target local-first development; no hosted free guarantee. |

Browser journey testing, privacy terms, repository permissions, onboarding friction, incident maps, test verification and free-tier availability require product-specific checks; absence of evidence is not evidence of absence. Competitor marketing does not prove a root-cause claim or its correctness.

## Opportunities to validate, not claims of novelty

| Concept | User value hypothesis | Complexity | Evidence / disconfirmation |
|---|---|---|---|
| Proof of Fix | Show same baseline failure then passing patch and regression checks; meaningful trust signal. | High: deterministic fixtures, isolation, flaky tests, realistic environment. | Interview maintainers and measure reproducibility; not novel merely because tests are shown. |
| Ghost User Testing | Detect visible broken flows without an exception. | High: stable synthetic journeys, test credentials and false positives. | Compare against existing synthetic monitoring; validate failures with consenting users. |
| Project Brain | Join stack frames, commit SHA and dependency/symbol search. | Medium; stale indexes and permission boundary risks. | Compare BM25/grep/symbol baseline against embeddings before paying for vectors. |
| Layered explanation | Help less experienced users see next action and original evidence. | Medium; wording can conceal uncertainty. | Usability test correct comprehension and escalation, not subjective polish alone. |
| Pre-deployment intelligence | Compare PR changes to known incidents. | High: mapping, noisy correlations, data leakage. | Benchmark false positive rate and outcomes versus ordinary CI. |
| Interactive dependency map | Navigate actual observed service/code relationships and time ranges. | Medium-high; incomplete or stale edges. | Require provenance and evidence coverage; demonstrate task completion against a list view. |

All demand and willingness-to-pay claims remain **HYPOTHESIS** until interviews and measured usage. Grafana already documents source citations, hypothesis controls and diagrams, so these are not defensible novelty claims alone.
