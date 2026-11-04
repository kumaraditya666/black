# AI engineering design

This is a **proposed** design, not a description of Sentry implementation. Date: 2026-11-04.

## Repository intelligence
Index repository identity, commit SHA, file paths, line ranges, imports and symbols; correlate stack frames against matching releases. Start with lexical search, exact paths and AST symbol links; test retrieval recall on known incidents before adding embeddings. Semantic vector search is optional and adds index, privacy and update costs. Mark unsupported languages, dynamic edges and stale commits explicitly.

## Investigation
Freeze a bounded incident snapshot; gather stack, timeline, release, relevant traces and code; generate competing hypotheses with evidence IDs and counterevidence; request missing evidence; stop on tool budget/deadline. Return findings as supported, plausible, or insufficient evidence, not invented numeric confidence. A claim must link to a preserved excerpt, timestamp and source revision. Logs, comments and source are untrusted data; never treat instructions in them as authority.

## Repair and verification
Use a disposable, resource-limited VM or appropriately hardened isolated runner with no production credentials and default-deny networking. Capture a failing baseline when reproducible; generate a minimal patch; run static checks, target test and independent regression suite; preserve logs and environment digest. State separately: generated, static checks passed, tests passed, original failure reproduced and resolved, and production outcome confirmed. A passing build alone is not a verified fix. Require explicit developer approval for PR creation and separately for merge/deploy. If baseline or environment unavailable, report tests-only evidence.

## Orchestration alternatives
| Approach | Benefit | Cost/risk |
|---|---|---|
| Single agent with typed tools | simplest baseline | sequential latency, one context |
| Deterministic workflow with bounded model calls | auditable state and retry | requires careful state-machine design |
| Sequential specialists | clearer responsibilities | context handoff loss and latency |
| Parallel specialists/coordinator | diverse hypotheses | extra tokens, conflicting evidence, synchronization |

**HYPOTHESIS:** deterministic workflow plus one tool-using agent is a practical initial baseline. Run paired evaluations before adding workers; no multi-agent gain is assumed. Restrict credentials, audit all tool calls, redact secrets before model transmission, enforce data retention, isolate untrusted code, and make approval enforcement independent of model instructions. Review [OWASP LLM prompt injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) and verify applicability to actual execution environment.
