# Proposed system architecture

All components and edges below are **PROPOSED**, not observations of Sentry's internals. The pipeline shape is informed by [OpenTelemetry](https://opentelemetry.io/docs/collector/architecture/) and the API boundary in [sentry-mcp](https://github.com/getsentry/sentry-mcp/blob/b8c480fc09c6ef2fbab337c1027705955d255456/packages/mcp-core/src/internal/tool-helpers/api.ts#L19).

```mermaid
flowchart LR
  APP[Instrumented app] -->|events/traces, build ID| ING[Receiver and redaction]
  ING -->|validated event| STORE[(Events and incident groups)]
  GH[Git provider] -->|authorized immutable revision| IDX[Symbol and text index]
  STORE -->|scoped evidence| ORCH[Investigation workflow]
  IDX -->|source spans and revision| ORCH
  ORCH -->|typed requests| AI[Model and read-only tools]
  AI -->|claims plus evidence IDs| ORCH
  ORCH --> UI[Evidence and uncertainty view]
  UI -->|explicit approval| PATCH[Patch proposal]
  PATCH --> BOX[Isolated reproducibility and tests]
  BOX -->|logs and graded result| UI
  UI -->|separate approval| PR[Draft pull request]
  APP -->|post-release signals| STORE
```

Persist incident identity, source revision, evidence provenance, tool calls, model version, state transitions and verification artifacts. The worker must enforce tenant boundaries and scoped read credentials independently of model output. Model-produced patches never directly mutate the source repository; validate in a disposable environment and gate PR creation. Handle duplicate events idempotently, queue saturation with explicit drops and retries, missing source maps as missing evidence, and deletion/retention across derived indexes. Prioritize a single language and event source for MVP. No 3D visualization is required for correctness.
