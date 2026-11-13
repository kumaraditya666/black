# Graph Report - black  (2026-11-14)

## Corpus Check
- 247 files · ~205,764 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .log 2, .example 1)

## Summary
- 2221 nodes · 6480 edges · 189 communities (71 shown, 118 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 636 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b96840fe`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pipeline.py
- LedgerBlocked
- test_engine.py
- Ledger
- execution.py
- test_approval_scoring.py
- validation.py
- Milestone 4B.1 — tool-use feasibility
- AI engineering design
- test_repair.py
- investigator.py
- 4. Tests
- MalformedAbstention
- 01_RESEARCH_MASTER_PLAN.md
- m4b3_ledger.py
- test_evidence_facts.py
- configuration.py
- input_handling.py
- buggy_apps/README.md
- fixtures.py
- Investigation evaluation record
- Milestone 2.9.1 — structured-output reliability fix and revalidation
- pytest
- Open-source architecture research
- Quality and evaluation plan
- CaseId
- Codex handoff: repair evaluation
- InvestigationResult
- 42_M4A_BLACKBOX_GAP_ANALYSIS.md
- Milestone 4A — experiment designs
- test_ollama_adapter_sends_bounded_schema_and_adaptive_budget
- start_ollama.ps1
- Milestone 3A — restricted Proof-of-Fix engine
- test_repair.py
- investigate
- test_telemetry.py
- OpenAICompatibleProvider
- test_ollama_adapter_sends_bounded_schema_and_adaptive_budget
- off_by_one/tests/test_regression.py
- extract_facts
- Store
- real_cases.py
- unreproducible/app.py
- 12_COMPETITIVE_GAP_ANALYSIS.md
- Path
- Exception
- m3c_trim_total/tests/test_regression.py
- m3c_window/tests/test_regression.py
- m3c_config/tests/test_regression.py
- evaluate_m29.py
- .analyze
- m4b_negative/tests/test_reproduction.py
- m4b_inventory/tests/test_regression.py
- m4b_average/tests/test_reproduction.py
- repair_cli.py
- m4b_negative/tests/test_regression.py
- Milestone 3B.1 — Docker lifecycle validation
- m4b1_caller/tests/test_regression.py
- m4b1_config/tests/test_regression.py
- m4b1_index/tests/test_regression.py
- m4b1_negative/tests/test_regression.py
- json
- Milestone 3D — repository intelligence and paired evaluation
- test_agent_retrieval.py
- ExternalRepairError
- FakeReceiver
- json
- HttpResponseBase
- field_validator
- argparse
- M4B3OllamaDispatcher
- models.py
- RunLock
- create_app
- Milestone 2.8 handoff completion
- test_real_review.py
- Milestone 3E — semantic reasoning and safe abstention
- buggy_app.py
- test_synthetic_scoring.py
- response.py
- StreamingHttpResponse
- bdb5/__init__.py
- HttpResponse
- bdb5_prepare_t1.py
- evaluate_m4b3.py
- _ReceiverHandler
- test_session_registry_rejects_forgery_substitution_and_closed_sessions
- prepare_m4b1_fixtures.py
- _ResponseMutationTransport
- .__init__
- BLACKBOX â€” local evidence and AI investigation
- bdb5_prepare_p1.py
- prepare_m4b_fixtures.py
- test_ollama_rejects_truncated_completion
- Milestone 4A — competitor architectures
- ._content_type_for_repr
- ._convert_to_charset
- SelectedTelemetry

## God Nodes (most connected - your core abstractions)
1. `LedgerBlocked` - 102 edges
2. `Ledger` - 81 edges
3. `_make_experiment()` - 74 edges
4. `CaseId` - 68 edges
5. `Store` - 59 edges
6. `InvestigationResult` - 54 edges
7. `investigate()` - 52 edges
8. `FakeReceiver` - 49 edges
9. `ProviderResult` - 44 edges
10. `CaseManifest` - 42 edges

## Surprising Connections (you probably didn't know these)
- `4. Patch generator` --references--> `PatchProposal`  [INFERRED]
  research/27_M3A_PROOF_OF_FIX.md → blackbox/repair/schema.py
- `Milestone 2.9 — repetition and stability, 2026-11-04` --references--> `evidence_hash()`  [INFERRED]
  EVALUATION.md → blackbox/investigator.py
- `AI investigation (opt-in)` --references--> `evidence_hash()`  [INFERRED]
  README.md → blackbox/investigator.py
- `1. Objective and method` --references--> `evidence_hash()`  [INFERRED]
  research/25_M29_STABILITY_EVALUATION.md → blackbox/investigator.py
- `5. Revalidation protocol` --references--> `evidence_hash()`  [INFERRED]
  research/26_M291_RELIABILITY_FIX.md → blackbox/investigator.py

## Import Cycles
- None detected.

## Communities (189 total, 118 thin omitted)

### Community 0 - "pipeline.py"
Cohesion: 0.13
Nodes (16): detect_isolation(), build_prompt(), parse_proposal(), PatchFormatError, PatchRejected, validate_and_apply(), _drop(), _elapsed() (+8 more)

### Community 1 - "LedgerBlocked"
Cohesion: 0.13
Nodes (11): FailureEvidence, Ledger, op(), op(), op(), op(), op(), op() (+3 more)

### Community 2 - "test_engine.py"
Cohesion: 0.08
Nodes (33): git(), plan(), source(), validate_response(), validate_template(), verify_local_model(), verify_model_config(), Attribution (+25 more)

### Community 3 - "Ledger"
Cohesion: 0.09
Nodes (50): dispatcher(), _approval_manifest(), _build_run_manifest(), _completion_metadata(), _completion_result(), _make_experiment(), _open_fake_session(), _prepare_dispatch() (+42 more)

### Community 4 - "execution.py"
Cohesion: 0.10
Nodes (29): _docker(), _docker_command(), _environment(), ExecutionResult, _inspect_owned(), Isolation, _journal_event(), recover_container() (+21 more)

### Community 5 - "test_approval_scoring.py"
Cohesion: 0.07
Nodes (38): _approval_base(), ApprovalError, ApprovalRecord, build_approval(), _manifest_and_packet(), ReviewerSignoff, validate_approval(), label_vault_hash() (+30 more)

### Community 6 - "validation.py"
Cohesion: 0.14
Nodes (19): evaluate_case(), PacketValidationError, build_t1_payload(), _evidence_hash(), make_log_evidence(), flush(), make_metric_evidence(), validate_packet() (+11 more)

### Community 9 - "Milestone 4B.1 — tool-use feasibility"
Cohesion: 0.13
Nodes (15): calculate(), relay(), run(), choose(), setup(), final_item(), prepare(), convert() (+7 more)

### Community 10 - "AI engineering design"
Cohesion: 0.10
Nodes (24): ProviderResult, test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze(), test_fabricated_hypothesis_reference_persists_failure(), analyze(), test_fake_file_reference_is_rejected() (+16 more)

### Community 11 - "test_repair.py"
Cohesion: 0.09
Nodes (14): 4. Tests executed, MockProvider, setup(), test_abstention_requires_missing_information_and_no_primary_hypothesis(), test_completed_result_marks_model_diagnosis_source(), test_invalid_events(), test_invalid_path(), test_investigation_caching_and_new_evidence() (+6 more)

### Community 12 - "investigator.py"
Cohesion: 0.10
Nodes (9): Claim, Hypothesis, InvestigationRequest, configured_provider(), Event, record_api(), record_one(), summarize() (+1 more)

### Community 13 - "4. Tests"
Cohesion: 0.25
Nodes (8): 4. Tests, test_model_facing_schema_bounds_observation_and_step_lists(), test_oversized_evidence_reports_a_distinct_failure(), analyze(), test_truncated_completion_keeps_token_usage(), analyze(), test_truncated_json_is_a_hard_failure(), analyze()

### Community 15 - "01_RESEARCH_MASTER_PLAN.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Dependency graphs and limits, Proposed system architecture, Technology feasibility and costs, Development roadmap — proposed, Source index, Open questions and risks

### Community 16 - "m4b3_ledger.py"
Cohesion: 0.08
Nodes (25): _absolute_path(), canonical_bytes(), CommitAmbiguous, _completion_derivation_sha256(), _configure(), _derive_completion_from_response(), DispatchResponseReceipt, evaluation_id() (+17 more)

### Community 17 - "test_evidence_facts.py"
Cohesion: 0.17
Nodes (22): Findings, _dedupe(), missing_evidence_references(), normalize_abstention(), _recorded_missing_text(), validate(), validate_model_output(), abstention() (+14 more)

### Community 18 - "configuration.py"
Cohesion: 0.14
Nodes (9): Milestone 4B: bounded retrieval experiment, Cost and timing, Method and integrity, Milestone 4B paired evaluation, One approved proof of fix, separate from diagnosis, Primary results, Milestone 4B failure analysis and next test, Most informative next test (+1 more)

### Community 19 - "input_handling.py"
Cohesion: 0.12
Nodes (17): total(), parse_amount(), require_full_window(), rolling_sum(), Baseline, freeze and protocol, Ground truth and measured primary runs, Milestone 3C — Complex debugging evaluation, Post-evaluation regression (+9 more)

### Community 20 - "buggy_apps/README.md"
Cohesion: 0.13
Nodes (15): 10. Limits, 11. Recommended targeted fixes (not implemented), 12. Readiness for a restricted Proof-of-Fix prototype, 1. Objective and method, 2. Repository and regression state, 3.1 Fresh pins (equivalent but different snapshots), 3.2 Replay of the exact Milestone 2.8 snapshots, 3.3 Determinism (+7 more)

### Community 21 - "fixtures.py"
Cohesion: 0.12
Nodes (24): Eligibility, evaluate(), evidence_reference_errors(), content_pinned(), fixture_path(), get_fixture(), _git(), load_registry() (+16 more)

### Community 22 - "Investigation evaluation record"
Cohesion: 0.08
Nodes (26): Changes, Codex handoff revalidation — 2026-11-05, Confirmed cause, Deterministic tests and isolation, Investigation evaluation record, Measured cost, Milestone 2.5 — local availability check, 2026-11-04, Milestone 2.6 — measured local inference, 2026-11-04 (+18 more)

### Community 23 - "Milestone 2.9.1 — structured-output reliability fix and revalidation"
Cohesion: 0.14
Nodes (13): 1. Confirmed failure mechanism, 2. Schema fix, 3. Adaptive output budget, 5. Revalidation protocol, 6. Results, 7. Quality gate, 8. Remaining issues, 9. Readiness for a restricted Proof-of-Fix prototype (+5 more)

### Community 24 - "pytest"
Cohesion: 0.09
Nodes (8): test_invalid_text_is_rejected(), test_none_is_rejected(), test_none_is_rejected_as_invalid_argument(), test_average_still_rejects_empty(), test_average_rejects_empty_input(), test_case(), test_bad_input(), test_average_rejects_empty_input()

### Community 25 - "Open-source architecture research"
Cohesion: 0.20
Nodes (10): Architecture assessment, Benchmarks and acceptance tests, Development skills and tools, Differentiation to validate, Evidence and outstanding research, Exact first development milestone, MVP and dependencies, Research readiness audit (+2 more)

### Community 26 - "Quality and evaluation plan"
Cohesion: 0.20
Nodes (8): Baseline and diagnosis of the 3E failure, Changes, Controlled comparison and interpretation, Frozen new cases and ground truth, Milestone 3F — evidence-grounded causal reasoning, Remaining risks and next work, Final validation iteration (registered after exploratory run, before this iteration), Milestone 3F preregistration

### Community 27 - "CaseId"
Cohesion: 0.12
Nodes (44): build_parser(), _default_output(), _emit(), main(), evaluate_suite(), AbstentionScope, CaseCategory, CaseId (+36 more)

### Community 28 - "Codex handoff: repair evaluation"
Cohesion: 0.33
Nodes (5): Baseline and environment, Codex handoff: repair evaluation, Fresh live run, Handoff and provenance, Independent fixture audit

### Community 29 - "InvestigationResult"
Cohesion: 0.12
Nodes (21): Abstention, Claim, InvestigationResult, TestExecution, validate_result_contract(), _bad_causal_result_json(), _bad_not_established_result_json(), _result_json() (+13 more)

### Community 30 - "42_M4A_BLACKBOX_GAP_ANALYSIS.md"
Cohesion: 0.16
Nodes (9): Changes, Engine, image and live integration tests, Genuine model repair, Milestone 3B.1 — Docker lifecycle validation, Remaining limitations, Differences worth testing, Gap matrix, Milestone 4A — BLACKBOX gap analysis (+1 more)

### Community 31 - "Milestone 4A — experiment designs"
Cohesion: 0.22
Nodes (9): select(), limit(), A. Agent-controlled read-only evidence retrieval — recommended first, B. Bounded hypothesis-testing investigation, C. Runtime-evidence enrichment, Illustrative resource planning, not measured overhead, Interpretation and sequencing, Milestone 4A — experiment designs (+1 more)

### Community 32 - "test_ollama_adapter_sends_bounded_schema_and_adaptive_budget"
Cohesion: 0.25
Nodes (3): test_ollama_adapter_sends_bounded_schema_and_adaptive_budget(), test_ollama_adapter_uses_structured_output(), post()

### Community 33 - "start_ollama.ps1"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 34 - "Milestone 3A — restricted Proof-of-Fix engine"
Cohesion: 0.11
Nodes (17): find_index(), 10. Deterministic integration results, 11. What remains unverified, 12. Is Milestone 3B justified?, 13. Not built, 1. What this milestone is, 2. Preserved baseline, 3. Eligibility gate (+9 more)

### Community 35 - "test_repair.py"
Cohesion: 0.18
Nodes (18): hypothesis_digest(), approval_for(), approve(), attempt_for(), FakeStore, make_case(), PatchProvider, reasons() (+10 more)

### Community 36 - "investigate"
Cohesion: 0.09
Nodes (24): _FinalProvider, fallback_findings(), investigate(), sanitize_output(), _summed_usage(), ProviderError, Frame, reconcile_facts() (+16 more)

### Community 37 - "test_telemetry.py"
Cohesion: 0.15
Nodes (21): load_inventory(), prepare_t1_case(), read_inject_time(), read_logs(), read_metrics(), _require_pyarrow(), select_evenly_spaced(), select_log_rows() (+13 more)

### Community 38 - "OpenAICompatibleProvider"
Cohesion: 0.06
Nodes (43): load_approval(), _content(), _finish_reason(), FullPacketError, FullPacketRun, FullPacketRunner, _provider_input_tokens(), _usage() (+35 more)

### Community 39 - "test_ollama_adapter_sends_bounded_schema_and_adaptive_budget"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

### Community 40 - "off_by_one/tests/test_regression.py"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 41 - "extract_facts"
Cohesion: 0.16
Nodes (12): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, 1. Original Codex state (+4 more)

### Community 42 - "Store"
Cohesion: 0.19
Nodes (6): Store, main(), make_incident(), frozen(), main(), test_provider_timeout_is_failure_without_repair()

### Community 45 - "real_cases.py"
Cohesion: 0.07
Nodes (38): _ensure_evaluable(), BDB5Error, BlockedCaseError, ManifestValidationError, UnsupportedModeError, Readiness, _artifacts(), _bounded_excerpt() (+30 more)

### Community 50 - "12_COMPETITIVE_GAP_ANALYSIS.md"
Cohesion: 0.50
Nodes (3): Information architecture, Public Seer UX audit, UX hypotheses for independent design

### Community 51 - "Path"
Cohesion: 0.50
Nodes (3): Documentation-derived workflows, Observable workflow research, Public discovery observed with Playwright

### Community 52 - "Exception"
Cohesion: 0.50
Nodes (3): MCP boundary: direct source inspection, Observability pipeline, Open-source architecture research

### Community 53 - "m3c_trim_total/tests/test_regression.py"
Cohesion: 0.50
Nodes (3): Dataset and ground truth, Measurements, Quality and evaluation plan

### Community 54 - "m3c_window/tests/test_regression.py"
Cohesion: 0.50
Nodes (3): ₹0 development MVP plan, Exit checks, Scope and dependency order

### Community 102 - "repair_cli.py"
Cohesion: 0.33
Nodes (11): command_approve(), command_attempt(), command_eligibility(), command_list(), command_review(), command_show(), _investigation_or_exit(), main() (+3 more)

### Community 139 - "json"
Cohesion: 0.07
Nodes (20): investigate_with_retrieval(), _investigate_with_retrieval(), main(), _BasicLimits, _ExtendedLimits, _IOCounters, Job, run_contained() (+12 more)

### Community 141 - "Milestone 3D — repository intelligence and paired evaluation"
Cohesion: 0.22
Nodes (7): Milestone 3D paired experiment preregistration, Cost and limitations, Design and data flow, Milestone 3D — repository intelligence and paired evaluation, Pre-registered paired protocol, Primary outcomes, Testing and next milestone

### Community 142 - "test_agent_retrieval.py"
Cohesion: 0.05
Nodes (48): Dispatcher, Request, RetrievalError, report(), clean_observations(), redact(), _calls(), _git() (+40 more)

### Community 143 - "ExternalRepairError"
Cohesion: 0.12
Nodes (24): _apply_patch(), build_evaluator_workspace(), build_p1_payload(), build_workspaces(), changed_files_from_patch(), check_patch_scope(), _copy_worktree(), ExternalRepairError (+16 more)

### Community 144 - "FakeReceiver"
Cohesion: 0.13
Nodes (38): execute(), _eval_id(), FakeReceiver, _fresh_process_summary(), _history(), _open_session(), _reconcile(), _run_child() (+30 more)

### Community 145 - "json"
Cohesion: 0.17
Nodes (6): main(), head(), main(), request(), test_preparation_cli_writes_r2_packet_outside_repo(), sample()

### Community 147 - "field_validator"
Cohesion: 0.07
Nodes (11): IssueCaseConfig, IssuePreparationError, prepare_issue_case(), PreparedIssueCase, _sha(), _source_excerpt(), CaseManifest, PatchRecord (+3 more)

### Community 148 - "argparse"
Cohesion: 0.18
Nodes (5): build_parser(), build_parser(), main(), build_parser(), main()

### Community 149 - "M4B3OllamaDispatcher"
Cohesion: 0.12
Nodes (8): DispatchPermit, _http_request_hash(), M4B3OllamaDispatcher, PreparedRequest, TransportOutcome, test_forged_legacy_permit_and_dispatch_without_database_never_send(), test_pre_transport_request_construction_failure_has_no_attempt(), test_request_preparation_is_stable_and_loopback_only()

### Community 150 - "models.py"
Cohesion: 0.10
Nodes (29): CaseScore, ClaimCategory, EvaluationMode, EvidencePacket, GroundTruth, SuiteResult, TestOutcome, TestRole (+21 more)

### Community 151 - "RunLock"
Cohesion: 0.20
Nodes (4): _file_identity_from_stat(), LockUnavailable, RunLock, test_forked_child_cannot_reuse_or_release_parent_run_lock()

### Community 152 - "create_app"
Cohesion: 0.21
Nodes (6): create_app(), context(), start_investigation(), collect(), evidence_hash(), ConflictError

### Community 153 - "Milestone 2.8 handoff completion"
Cohesion: 0.22
Nodes (7): validate_frame_narrative(), 2. Freebuff changes, 3. Files modified or added, 6. Before and after, 7. Unresolved issues, 8. Final status, Milestone 2.8 handoff completion

### Community 154 - "test_real_review.py"
Cohesion: 0.46
Nodes (7): _fake_source(), _r1_payload(), _r2_payload(), test_review_accepts_r1_and_r2_boundaries(), test_review_cli_writes_machine_readable_failure(), test_review_rejects_approval_and_application_source_leak_in_r2(), test_review_rejects_top_level_manifest_and_host_path()

### Community 155 - "Milestone 3E — semantic reasoning and safe abstention"
Cohesion: 0.29
Nodes (5): Milestone 3E evaluation preregistration, Limits and next work, Milestone 3E — semantic reasoning and safe abstention, Paired experiment, Previously observed 3D cases

### Community 156 - "buggy_app.py"
Cohesion: 0.15
Nodes (11): Continuation fixes (after the interrupted Codex state), Deterministic layer, Final live evaluation, Milestone 2.8 — deterministic evidence layer and abstention reliability, 2026-11-04, Not measured, Recorded failures, kept separate, Tests, 5. Actual live model results (+3 more)

### Community 157 - "test_synthetic_scoring.py"
Cohesion: 0.20
Nodes (18): scenario(), score(), test_p1_incomplete_f2p_unexecuted_pass_and_regression_failure(), test_p1_invalid_scope_and_test_modification_are_rejected(), test_p1_patch_test_and_regression_dimensions(), test_r1_missing_reproduction_and_citation(), test_r1_patch_free_source_scoring_dimensions(), test_r1_unexecuted_pass_is_an_execution_overclaim() (+10 more)

### Community 158 - "response.py"
Cohesion: 0.12
Nodes (4): Http404, HttpResponsePermanentRedirect, HttpResponseRedirect, HttpResponseRedirectBase

### Community 160 - "bdb5/__init__.py"
Cohesion: 0.14
Nodes (11): _keys(), PacketReview, _registry_entry(), review_file(), review_payload(), _strings(), accept_prepared_result(), _case_objects() (+3 more)

### Community 161 - "HttpResponse"
Cohesion: 0.14
Nodes (6): HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseGone, HttpResponseNotFound, HttpResponseServerError

### Community 162 - "bdb5_prepare_t1.py"
Cohesion: 0.47
Nodes (3): build_parser(), _default_output(), main()

### Community 163 - "evaluate_m4b3.py"
Cohesion: 0.09
Nodes (22): M4B3TransportPhase, _assert_registered_session(), build_run_manifest(), digest(), _document_hash(), _execute_registered(), _expected_plan_matches(), initialize_experiment() (+14 more)

### Community 169 - "BLACKBOX â€” local evidence and AI investigation"
Cohesion: 0.29
Nodes (7): AI investigation (opt-in), BLACKBOX â€” local evidence and AI investigation, Limits, One-command demo, Restricted Proof-of-Fix (Milestone 3A), Run the service and tests, Setup

### Community 175 - "Milestone 4A — competitor architectures"
Cohesion: 0.33
Nodes (6): Milestone 4A — competitor architectures, OpenHands repository boundary, OpenHands / Software Agent SDK, Sentry Seer / Autofix, SWE-agent, Synthesis

## Knowledge Gaps
- **118 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evidence_hash()` connect `create_app` to `evaluate_m4b3.py`, `investigate`, `BLACKBOX â€” local evidence and AI investigation`, `investigator.py`, `json`, `buggy_apps/README.md`, `Investigation evaluation record`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `LedgerBlocked` (e.g. with `M4B3OllamaDispatcher` and `_open_fake_session()`) actually correct?**
  _`LedgerBlocked` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `pipeline.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1265597147950089 - nodes in this community are weakly interconnected._
- **Why does `Investigation evaluation record` connect `Investigation evaluation record` to `configuration.py`, `buggy_app.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `Ledger` (e.g. with `_open_fake_session()` and `RunSession`) actually correct?**
  _`Ledger` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `LedgerBlocked` be split into smaller, more focused modules?**
  _Cohesion score 0.1276595744680851 - nodes in this community are weakly interconnected._
- **Why does `investigate()` connect `investigate` to `test_repair.py`, `extract_facts`, `Store`, `json`, `investigator.py`, `Milestone 4B.1 — tool-use feasibility`, `test_agent_retrieval.py`, `test_evidence_facts.py`, `json`, `fixtures.py`, `create_app`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._