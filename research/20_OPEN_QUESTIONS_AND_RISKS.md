# Open questions and risks

- UNKNOWN: Exact feature entitlements, pricing, regional availability and product changes require checks immediately before purchase or implementation.
- UNKNOWN: Authentic user demand and willingness to pay for proof-of-fix and journey testing; conduct interviews and pilots.
- UNKNOWN: Reproduction feasibility for missing data, third-party dependencies, nondeterministic bugs and privacy-sensitive production state.
- Risk: untrusted telemetry and repository text can contain instructions. Use independent authorization and scoped tools; no prompt-only defense is sufficient. [OWASP](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).
- Risk: untrusted repository tests can execute arbitrary code; sandbox with no secrets, constrained network, resource quotas and teardown. Container isolation is not a universal security boundary.
- Risk: observability data may expose personal information or credentials; provide minimization, redaction, deletion and access control.
- Risk: benchmark contamination, underspecified tests and distribution shift can inflate apparent performance; audit and use held-out, reproducible cases.
- Risk: a no-cost local prototype does not prove a sustainable no-cost hosted service; compute, storage, egress and inference have marginal costs.
