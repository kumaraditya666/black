# Graph Report - black  (2026-11-05)

## Corpus Check
- 89 files · ~84,551 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .log 4, .example 1, (none) 1)

## Summary
- 402 nodes · 754 edges · 38 communities (19 shown, 19 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `01b73f01`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- investigator.py
- 22_RESEARCH_READINESS_AUDIT.md
- test_engine.py
- extract_facts
- Seer user journeys
- providers.py
- Research readiness audit
- json
- Public Seer UX audit
- test_evidence_facts.py
- AI engineering design
- Milestone 2.9 — AI reliability benchmark
- Product requirements — research-stage proposal
- AGENTS.md
- 01_RESEARCH_MASTER_PLAN.md
- 16_FINAL_PRODUCT_BLUEPRINT.md
- RESEARCH_LOG.md
- buggy_apps/README.md
- Targeted inspection findings
- Milestone 2.9.1 — structured-output reliability fix and revalidation
- Observable workflow research
- Open-source architecture research
- Quality and evaluation plan
- ₹0 development MVP plan
- 04_SEER_FRONTEND_OBSERVATIONS.md
- 09_DEPENDENCY_GRAPHS.md
- 14_TECH_STACK_FEASIBILITY.md
- 23_M28_FAILURE_ANALYSIS.md
- Investigation evaluation record

## God Nodes (most connected - your core abstractions)
1. `ProviderResult` - 23 edges
2. `create_app()` - 23 edges
3. `Findings` - 21 edges
4. `ProviderError` - 21 edges
5. `investigate()` - 20 edges
6. `validate()` - 16 edges
7. `Store` - 16 edges
8. `normalize_abstention()` - 15 edges
9. `collect()` - 14 edges
10. `extract_facts()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Milestone 2.9 — repetition and stability, 2026-11-04` --references--> `evidence_hash()`  [INFERRED]
  EVALUATION.md → blackbox/investigator.py
- `AI investigation (opt-in)` --references--> `evidence_hash()`  [INFERRED]
  README.md → blackbox/investigator.py
- `5. Revalidation protocol` --references--> `evidence_hash()`  [INFERRED]
  research/26_M291_RELIABILITY_FIX.md → blackbox/investigator.py
- `Deterministic layer` --references--> `check_atomic_claim()`  [INFERRED]
  EVALUATION.md → blackbox/evidence_facts.py
- `1. Original Codex state` --references--> `normalize_abstention()`  [INFERRED]
  research/24_M28_HANDOFF_COMPLETION.md → blackbox/investigator.py

## Import Cycles
- None detected.

## Communities (38 total, 19 thin omitted)

### Community 0 - "investigator.py"
Cohesion: 0.08
Nodes (18): create_app(), context(), report(), start_investigation(), collect(), evidence_hash(), investigate(), redact() (+10 more)

### Community 1 - "22_RESEARCH_READINESS_AUDIT.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Proposed system architecture, Competitive gap analysis, Opportunities to validate, not claims of novelty, Development roadmap — proposed, Source index, Open questions and risks

### Community 2 - "test_engine.py"
Cohesion: 0.08
Nodes (31): ProviderResult, 4. Tests executed, MockProvider, setup(), test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze() (+23 more)

### Community 3 - "extract_facts"
Cohesion: 0.13
Nodes (13): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, fallback_findings() (+5 more)

### Community 4 - "Seer user journeys"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 5 - "providers.py"
Cohesion: 0.07
Nodes (19): configured_provider(), output_budget(), Provider, ProviderError, 4. Tests, test_gemini_adapter_configures_structured_response(), test_model_facing_schema_bounds_observation_and_step_lists(), test_ollama_adapter_sends_bounded_schema_and_adaptive_budget() (+11 more)

### Community 6 - "Research readiness audit"
Cohesion: 0.20
Nodes (10): Architecture assessment, Benchmarks and acceptance tests, Development skills and tools, Differentiation to validate, Evidence and outstanding research, Exact first development milestone, MVP and dependencies, Research readiness audit (+2 more)

### Community 7 - "json"
Cohesion: 0.19
Nodes (3): main(), main(), request()

### Community 8 - "Public Seer UX audit"
Cohesion: 0.50
Nodes (3): Information architecture, Public Seer UX audit, UX hypotheses for independent design

### Community 9 - "test_evidence_facts.py"
Cohesion: 0.11
Nodes (29): Claim, Findings, Hypothesis, InvestigationRequest, clean_observations(), _dedupe(), missing_evidence_references(), normalize_abstention() (+21 more)

### Community 10 - "AI engineering design"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 11 - "Milestone 2.9 — AI reliability benchmark"
Cohesion: 0.08
Nodes (24): Final live evaluation, 3. Files modified or added, 5. Actual live model results, 6. Before and after, 7. Unresolved issues, 8. Final status, Milestone 2.8 handoff completion, 10. Limits (+16 more)

### Community 22 - "Targeted inspection findings"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

### Community 23 - "Milestone 2.9.1 — structured-output reliability fix and revalidation"
Cohesion: 0.09
Nodes (19): AI investigation (opt-in), BLACKBOX — local evidence and AI investigation, Limits, One-command demo, Run the service and tests, Setup, 1. Confirmed failure mechanism, 2. Schema fix (+11 more)

### Community 24 - "Observable workflow research"
Cohesion: 0.50
Nodes (3): Documentation-derived workflows, Observable workflow research, Public discovery observed with Playwright

### Community 25 - "Open-source architecture research"
Cohesion: 0.50
Nodes (3): MCP boundary: direct source inspection, Observability pipeline, Open-source architecture research

### Community 26 - "Quality and evaluation plan"
Cohesion: 0.50
Nodes (3): Dataset and ground truth, Measurements, Quality and evaluation plan

### Community 27 - "₹0 development MVP plan"
Cohesion: 0.50
Nodes (3): ₹0 development MVP plan, Exit checks, Scope and dependency order

### Community 32 - "Investigation evaluation record"
Cohesion: 0.11
Nodes (18): Changes, Confirmed cause, Continuation fixes (after the interrupted Codex state), Deterministic layer, Investigation evaluation record, Milestone 2.5 — local availability check, 2026-11-04, Milestone 2.6 — measured local inference, 2026-11-04, Milestone 2.7 — evidence and abstention, 2026-11-04 (+10 more)

## Knowledge Gaps
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evidence_hash()` connect `investigator.py` to `Investigation evaluation record`, `test_evidence_facts.py`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`, `json`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `InvestigationRequest` and `ProviderError`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `investigator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07680491551459294 - nodes in this community are weakly interconnected._
- **Why does `Milestone 2.9 — AI reliability benchmark` connect `Milestone 2.9 — AI reliability benchmark` to `investigator.py`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `Findings` (e.g. with `validate()` and `validate_frame_narrative()`) actually correct?**
  _`Findings` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Should `22_RESEARCH_READINESS_AUDIT.md` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Why does `create_app()` connect `investigator.py` to `test_evidence_facts.py`, `test_engine.py`, `providers.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._