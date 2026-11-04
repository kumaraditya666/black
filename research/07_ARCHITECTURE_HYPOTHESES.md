# Architecture hypotheses

These are independent product design hypotheses, not statements about Sentry internals.

- **HYPOTHESIS:** A durable state machine can track investigation steps, artifacts, retries and approval transitions more reliably than an unconstrained loop. Test with injected worker crashes and repeated events.
- **HYPOTHESIS:** A combined exact-symbol, stack-frame and lexical retrieval index will provide a practical initial baseline; compare against semantic retrieval before introducing a vector database.
- **HYPOTHESIS:** Evidence citations tied to immutable event and commit identifiers can improve auditability. Measure citation validity and user review effort.
- **UNKNOWN:** Private model routing, prompts, orchestration implementation and internal production evaluation of competitors. Public marketing cannot establish these details.
- **HYPOTHESIS:** Untrusted logs and code comments should be treated as data, with authorization enforced outside the model; this reduces the effect of instruction injection, but does not guarantee prevention. See [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).
