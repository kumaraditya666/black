# Graph Report - black  (2026-11-04)

## Corpus Check
- 83 files · ~56,681 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .log 2, .example 1, (none) 1)

## Summary
- 365 nodes · 688 edges · 36 communities (17 shown, 19 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 37 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `04873044`
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
- Observable workflow research
- Open-source architecture research
- Quality and evaluation plan
- ₹0 development MVP plan
- 04_SEER_FRONTEND_OBSERVATIONS.md
- 09_DEPENDENCY_GRAPHS.md
- 14_TECH_STACK_FEASIBILITY.md
- 23_M28_FAILURE_ANALYSIS.md

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 23 edges
2. `ProviderResult` - 20 edges
3. `investigate()` - 19 edges
4. `Findings` - 18 edges
5. `Store` - 16 edges
6. `validate()` - 16 edges
7. `normalize_abstention()` - 15 edges
8. `collect()` - 14 edges
9. `Milestone 2.9 — AI reliability benchmark` - 13 edges
10. `extract_facts()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Deterministic layer` --references--> `check_atomic_claim()`  [INFERRED]
  EVALUATION.md → blackbox/evidence_facts.py
- `Milestone 2.9 — repetition and stability, 2026-11-04` --references--> `evidence_hash()`  [INFERRED]
  EVALUATION.md → blackbox/investigator.py
- `AI investigation (opt-in)` --references--> `evidence_hash()`  [INFERRED]
  README.md → blackbox/investigator.py
- `Final live evaluation` --references--> `calculate_average()`  [INFERRED]
  EVALUATION.md → sample_template/buggy_app.py
- `1. Objective and method` --references--> `evidence_hash()`  [INFERRED]
  research/25_M29_STABILITY_EVALUATION.md → blackbox/investigator.py

## Import Cycles
- None detected.

## Communities (36 total, 19 thin omitted)

### Community 0 - "investigator.py"
Cohesion: 0.08
Nodes (22): create_app(), context(), report(), start_investigation(), Claim, Hypothesis, InvestigationRequest, clean_observations() (+14 more)

### Community 1 - "22_RESEARCH_READINESS_AUDIT.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Proposed system architecture, Competitive gap analysis, Opportunities to validate, not claims of novelty, Development roadmap — proposed, Source index, Open questions and risks

### Community 2 - "test_engine.py"
Cohesion: 0.08
Nodes (27): ProviderResult, 4. Tests executed, MockProvider, test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze(), test_completed_result_marks_model_diagnosis_source() (+19 more)

### Community 3 - "extract_facts"
Cohesion: 0.15
Nodes (12): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, 1. Original Codex state (+4 more)

### Community 4 - "Seer user journeys"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 5 - "providers.py"
Cohesion: 0.10
Nodes (9): configured_provider(), Provider, ProviderError, test_gemini_adapter_configures_structured_response(), test_ollama_adapter_uses_structured_output(), test_ollama_local_only(), test_ollama_rejects_truncated_completion(), test_provider_unavailable_is_reported_separately() (+1 more)

### Community 6 - "Research readiness audit"
Cohesion: 0.20
Nodes (10): Architecture assessment, Benchmarks and acceptance tests, Development skills and tools, Differentiation to validate, Evidence and outstanding research, Exact first development milestone, MVP and dependencies, Research readiness audit (+2 more)

### Community 7 - "json"
Cohesion: 0.10
Nodes (7): _dedupe(), main(), record_api(), record_one(), summarize(), main(), request()

### Community 8 - "Public Seer UX audit"
Cohesion: 0.50
Nodes (3): Information architecture, Public Seer UX audit, UX hypotheses for independent design

### Community 9 - "test_evidence_facts.py"
Cohesion: 0.14
Nodes (23): Findings, missing_evidence_references(), normalize_abstention(), _recorded_missing_text(), validate(), validate_frame_narrative(), validate_model_output(), 2. Freebuff changes (+15 more)

### Community 10 - "AI engineering design"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 11 - "Milestone 2.9 — AI reliability benchmark"
Cohesion: 0.04
Nodes (42): Continuation fixes (after the interrupted Codex state), Deterministic layer, Final live evaluation, Investigation evaluation record, Milestone 2.5 — local availability check, 2026-11-04, Milestone 2.6 — measured local inference, 2026-11-04, Milestone 2.7 — evidence and abstention, 2026-11-04, Milestone 2.8 — deterministic evidence layer and abstention reliability, 2026-11-04 (+34 more)

### Community 22 - "Targeted inspection findings"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

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

## Knowledge Gaps
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evidence_hash()` connect `investigator.py` to `Milestone 2.9 — AI reliability benchmark`, `json`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `InvestigationRequest` and `ProviderError`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `investigator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07738095238095238 - nodes in this community are weakly interconnected._
- **Why does `Milestone 2.9 — AI reliability benchmark` connect `Milestone 2.9 — AI reliability benchmark` to `investigator.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `investigate()` (e.g. with `Store` and `.connect()`) actually correct?**
  _`investigate()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `22_RESEARCH_READINESS_AUDIT.md` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Why does `1. Objective and method` connect `investigator.py` to `Milestone 2.9 — AI reliability benchmark`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._