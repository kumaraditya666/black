# Graph Report - black  (2026-11-04)

## Corpus Check
- 63 files · ~27,900 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: .example 1, (none) 1, .zip 1)

## Summary
- 250 nodes · 423 edges · 27 communities (12 shown, 15 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- investigator.py
- 22_RESEARCH_READINESS_AUDIT.md
- test_engine.py
- providers.py
- Seer user journeys
- BLACKBOX — local evidence-to-source engine
- json
- Public Seer UX audit
- investigation_schema.py
- AI engineering design
- Investigation evaluation record
- Product requirements — research-stage proposal
- AGENTS.md
- 01_RESEARCH_MASTER_PLAN.md
- 16_FINAL_PRODUCT_BLUEPRINT.md
- RESEARCH_LOG.md
- buggy_apps/README.md
- Targeted inspection findings
- buggy_app.py

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 21 edges
2. `investigate()` - 16 edges
3. `Store` - 14 edges
4. `collect()` - 13 edges
5. `redact()` - 11 edges
6. `Findings` - 10 edges
7. `ProviderResult` - 10 edges
8. `Research readiness audit` - 10 edges
9. `resolve()` - 9 edges
10. `Provider` - 9 edges

## Surprising Connections (you probably didn't know these)
- `test_abstention_requires_missing_information_and_no_primary_hypothesis()` --uses--> `Findings`  [INFERRED]
  tests/test_engine.py → blackbox/investigation_schema.py
- `setup()` --calls--> `create_app()`  [EXTRACTED]
  tests/test_engine.py → blackbox/app.py
- `generate()` --calls--> `ProviderResult`  [EXTRACTED]
  tests/test_engine.py → blackbox/providers.py
- `test_ollama_local_only()` --calls--> `Provider`  [EXTRACTED]
  tests/test_engine.py → blackbox/providers.py
- `investigate()` --uses--> `Findings`  [INFERRED]
  blackbox/investigator.py → blackbox/investigation_schema.py

## Import Cycles
- None detected.

## Communities (27 total, 15 thin omitted)

### Community 0 - "investigator.py"
Cohesion: 0.12
Nodes (15): create_app(), context(), report(), start_investigation(), collect(), evidence_hash(), investigate(), sanitize_output() (+7 more)

### Community 1 - "22_RESEARCH_READINESS_AUDIT.md"
Cohesion: 0.04
Nodes (34): Tool readiness, 2026-11-04 — public page, Chrome DevTools MCP, Frontend observation log, Documentation-derived workflows, Observable workflow research, Public discovery observed with Playwright, Architecture hypotheses, MCP boundary: direct source inspection (+26 more)

### Community 2 - "test_engine.py"
Cohesion: 0.11
Nodes (16): ProviderResult, MockProvider, setup(), test_abstention_requires_missing_information_and_no_primary_hypothesis(), test_fabricated_reference_persists_failure(), test_fake_file_reference_is_rejected(), generate(), test_invalid_events() (+8 more)

### Community 3 - "providers.py"
Cohesion: 0.10
Nodes (7): configured_provider(), Provider, ProviderError, test_gemini_adapter_configures_structured_response(), test_ollama_adapter_uses_structured_output(), test_ollama_local_only(), test_ollama_rejects_truncated_completion()

### Community 4 - "Seer user journeys"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 5 - "BLACKBOX — local evidence-to-source engine"
Cohesion: 0.29
Nodes (6): AI investigation (opt-in), BLACKBOX — local evidence and AI investigation, Limits, One-command demo, Run the service and tests, Setup

### Community 7 - "json"
Cohesion: 0.15
Nodes (3): main(), main(), request()

### Community 8 - "Public Seer UX audit"
Cohesion: 0.50
Nodes (3): Information architecture, Public Seer UX audit, UX hypotheses for independent design

### Community 9 - "investigation_schema.py"
Cohesion: 0.19
Nodes (5): Claim, Findings, Hypothesis, InvestigationRequest, Frame

### Community 10 - "AI engineering design"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 11 - "Investigation evaluation record"
Cohesion: 0.33
Nodes (5): Investigation evaluation record, Milestone 2.5 — local availability check, 2026-11-04, Milestone 2.6 — measured local inference, 2026-11-04, Milestone 2.7 — evidence and abstention, 2026-11-04, Real-model observations, not mocks

### Community 22 - "Targeted inspection findings"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

## Knowledge Gaps
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `investigator.py` to `investigation_schema.py`, `test_engine.py`, `providers.py`, `json`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `InvestigationRequest` and `ProviderError`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `investigator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11818181818181818 - nodes in this community are weakly interconnected._
- **Why does `Findings` connect `investigation_schema.py` to `investigator.py`, `test_engine.py`, `providers.py`, `json`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `investigate()` (e.g. with `Findings` and `Store`) actually correct?**
  _`investigate()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `22_RESEARCH_READINESS_AUDIT.md` be split into smaller, more focused modules?**
  _Cohesion score 0.04081632653061224 - nodes in this community are weakly interconnected._
- **Why does `Store` connect `investigator.py` to `json`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._