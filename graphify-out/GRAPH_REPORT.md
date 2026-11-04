# Graph Report - black  (2026-11-05)

## Corpus Check
- 123 files · ~98,226 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .log 4, .example 1, (none) 1)

## Summary
- 604 nodes · 1277 edges · 54 communities (23 shown, 31 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a7ee4fe7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- investigator.py
- 22_RESEARCH_READINESS_AUDIT.md
- test_engine.py
- pipeline.py
- Seer user journeys
- repair_cli.py
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
- test_repair.py
- ProviderResult
- 23_M28_FAILURE_ANALYSIS.md
- Investigation evaluation record
- Provider
- output_budget
- test_ollama_adapter_uses_structured_output
- 12_COMPETITIVE_GAP_ANALYSIS.md
- setup
- test_provider_timeout_keeps_facts_and_reports_timeout

## God Nodes (most connected - your core abstractions)
1. `Store` - 30 edges
2. `ProviderResult` - 29 edges
3. `run_repair()` - 28 edges
4. `ProviderError` - 27 edges
5. `investigate()` - 24 edges
6. `create_app()` - 23 edges
7. `evaluate()` - 21 edges
8. `Findings` - 20 edges
9. `main()` - 17 edges
10. `validate()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `4. Patch generator` --references--> `PatchProposal`  [INFERRED]
  research/27_M3A_PROOF_OF_FIX.md → blackbox/repair/schema.py
- `7. Review interface` --references--> `approve()`  [INFERRED]
  research/27_M3A_PROOF_OF_FIX.md → tests/test_repair.py
- `Deterministic layer` --references--> `check_atomic_claim()`  [INFERRED]
  EVALUATION.md → blackbox/evidence_facts.py
- `Milestone 2.9 — repetition and stability, 2026-11-04` --references--> `evidence_hash()`  [INFERRED]
  EVALUATION.md → blackbox/investigator.py
- `AI investigation (opt-in)` --references--> `evidence_hash()`  [INFERRED]
  README.md → blackbox/investigator.py

## Import Cycles
- None detected.

## Communities (54 total, 31 thin omitted)

### Community 0 - "investigator.py"
Cohesion: 0.08
Nodes (21): create_app(), context(), report(), start_investigation(), clean_observations(), collect(), evidence_hash(), fallback_findings() (+13 more)

### Community 1 - "22_RESEARCH_READINESS_AUDIT.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Dependency graphs and limits, Proposed system architecture, Technology feasibility and costs, Development roadmap — proposed, Source index, Open questions and risks

### Community 2 - "test_engine.py"
Cohesion: 0.13
Nodes (11): 4. Tests executed, MockProvider, test_abstention_requires_missing_information_and_no_primary_hypothesis(), test_completed_result_marks_model_diagnosis_source(), test_fabricated_hypothesis_reference_persists_failure(), test_invalid_events(), test_invalid_path(), test_investigation_caching_and_new_evidence() (+3 more)

### Community 3 - "pipeline.py"
Cohesion: 0.13
Nodes (16): Claim, Hypothesis, InvestigationRequest, build_prompt(), parse_proposal(), PatchFormatError, PatchRejected, validate_and_apply() (+8 more)

### Community 4 - "Seer user journeys"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 5 - "repair_cli.py"
Cohesion: 0.14
Nodes (19): configured_provider(), ProviderError, command_approve(), command_attempt(), command_eligibility(), command_list(), command_review(), command_show() (+11 more)

### Community 6 - "Research readiness audit"
Cohesion: 0.20
Nodes (10): Architecture assessment, Benchmarks and acceptance tests, Development skills and tools, Differentiation to validate, Evidence and outstanding research, Exact first development milestone, MVP and dependencies, Research readiness audit (+2 more)

### Community 7 - "json"
Cohesion: 0.08
Nodes (14): _dedupe(), detect_isolation(), _docker_command(), _environment(), ExecutionResult, Isolation, run_tests(), _timeout() (+6 more)

### Community 8 - "Public Seer UX audit"
Cohesion: 0.50
Nodes (3): Information architecture, Public Seer UX audit, UX hypotheses for independent design

### Community 9 - "test_evidence_facts.py"
Cohesion: 0.06
Nodes (41): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, Findings (+33 more)

### Community 10 - "AI engineering design"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 11 - "Milestone 2.9 — AI reliability benchmark"
Cohesion: 0.07
Nodes (25): Final live evaluation, 3. Files modified or added, 5. Actual live model results, 6. Before and after, 7. Unresolved issues, 8. Final status, Milestone 2.8 handoff completion, 10. Limits (+17 more)

### Community 22 - "Targeted inspection findings"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

### Community 23 - "Milestone 2.9.1 — structured-output reliability fix and revalidation"
Cohesion: 0.05
Nodes (37): find_index(), AI investigation (opt-in), BLACKBOX — local evidence and AI investigation, Limits, One-command demo, Restricted Proof-of-Fix (Milestone 3A), Run the service and tests, Setup (+29 more)

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

### Community 29 - "test_repair.py"
Cohesion: 0.10
Nodes (31): Eligibility, evaluate(), evidence_reference_errors(), hypothesis_digest(), blob_at(), content_pinned(), fixture_path(), get_fixture() (+23 more)

### Community 30 - "ProviderResult"
Cohesion: 0.15
Nodes (17): ProviderResult, test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze(), analyze(), test_fake_file_reference_is_rejected(), generate() (+9 more)

### Community 32 - "Investigation evaluation record"
Cohesion: 0.08
Nodes (24): Changes, Confirmed cause, Continuation fixes (after the interrupted Codex state), Deterministic layer, Deterministic tests and isolation, Investigation evaluation record, Measured cost, Milestone 2.5 — local availability check, 2026-11-04 (+16 more)

### Community 38 - "Provider"
Cohesion: 0.15
Nodes (4): Provider, test_gemini_adapter_configures_structured_response(), test_ollama_local_only(), test_ollama_rejects_truncated_completion()

### Community 39 - "output_budget"
Cohesion: 0.18
Nodes (7): output_budget(), 4. Tests, test_model_facing_schema_bounds_observation_and_step_lists(), test_ollama_adapter_sends_bounded_schema_and_adaptive_budget(), test_output_budget_shrinks_for_large_prompts_without_dropping_evidence(), test_truncated_json_is_a_hard_failure(), analyze()

## Knowledge Gaps
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evidence_hash()` connect `investigator.py` to `Investigation evaluation record`, `json`, `Milestone 2.9 — AI reliability benchmark`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`, `test_repair.py`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `Store` (e.g. with `collect()` and `investigate()`) actually correct?**
  _`Store` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `investigator.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08028846153846154 - nodes in this community are weakly interconnected._
- **Why does `Investigation evaluation record` connect `Investigation evaluation record` to `Milestone 2.9.1 — structured-output reliability fix and revalidation`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `ProviderResult` (e.g. with `MockProvider` and `CauseProvider`) actually correct?**
  _`ProviderResult` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `22_RESEARCH_READINESS_AUDIT.md` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Why does `investigate()` connect `investigator.py` to `test_evidence_facts.py`, `test_repair.py`, `repair_cli.py`, `json`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._