# Graph Report - black  (2026-11-14)

## Corpus Check
- 254 files · ~209,696 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .log 2, .example 1)

## Summary
- 2295 nodes · 6681 edges · 189 communities (73 shown, 116 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 637 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `66a74563`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- codebase_audit.py
- LedgerBlocked
- test_engine.py
- test_m4b3_ledger.py
- execution.py
- test_approval_scoring.py
- M4B3OllamaDispatcher
- pathlib
- Milestone 4B.1 — tool-use feasibility
- AI engineering design
- test_repair.py
- Store
- scan_codebase.py
- MalformedAbstention
- 01_RESEARCH_MASTER_PLAN.md
- RunLock
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
- models.py
- 42_M4A_BLACKBOX_GAP_ANALYSIS.md
- Milestone 4A — experiment designs
- test_ollama_adapter_sends_bounded_schema_and_adaptive_budget
- start_ollama.ps1
- Milestone 3A — restricted Proof-of-Fix engine
- test_repair.py
- investigator.py
- test_telemetry.py
- OpenAICompatibleProvider
- test_ollama_adapter_sends_bounded_schema_and_adaptive_budget
- off_by_one/tests/test_regression.py
- extract_facts
- test_agent_retrieval.py
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
- hashlib
- m4b_negative/tests/test_regression.py
- Milestone 3B.1 — Docker lifecycle validation
- m4b1_caller/tests/test_regression.py
- m4b1_config/tests/test_regression.py
- m4b1_index/tests/test_regression.py
- m4b1_negative/tests/test_regression.py
- Store
- Milestone 3D — repository intelligence and paired evaluation
- retrieve
- ExternalRepairError
- test_session_registry_rejects_forgery_substitution_and_closed_sessions
- argparse
- HttpResponseBase
- field_validator
- test_capture.py
- _approval_manifest
- EvidencePacket
- fixtures.py
- Milestone 4A — competitor architectures
- Milestone 2.8 handoff completion
- test_real_review.py
- Milestone 3E — semantic reasoning and safe abstention
- cli.py
- test_synthetic_scoring.py
- response.py
- StreamingHttpResponse
- bdb5/__init__.py
- HttpResponse
- test_external_repair.py
- evaluate_m4b3.py
- _ReceiverHandler
- output_budget
- digest
- _ResponseMutationTransport
- .__init__
- BLACKBOX â€” local evidence and AI investigation
- limit
- test_fake_cli_defaults_lock_beside_temporary_ledger
- ._content_type_for_repr
- ._convert_to_charset
- ProviderError
- fastapi_capture_demo.py
- Job
- Findings

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

## Communities (189 total, 116 thin omitted)

### Community 0 - "codebase_audit.py"
Cohesion: 0.17
Nodes (12): _add(), _ast_findings(), add(), _candidate_files(), _commit(), Finding, _git(), _is_test() (+4 more)

### Community 1 - "LedgerBlocked"
Cohesion: 0.09
Nodes (18): _completion_derivation_sha256(), _derive_completion_from_response(), DispatchPermit, DispatchResponseReceipt, EvaluationState, FailureEvidence, _is_hash(), Ledger (+10 more)

### Community 2 - "test_engine.py"
Cohesion: 0.08
Nodes (34): FixSuggestion, git(), plan(), source(), validate_response(), validate_template(), verify_local_model(), verify_model_config() (+26 more)

### Community 3 - "test_m4b3_ledger.py"
Cohesion: 0.11
Nodes (51): execute(), _eval_id(), FakeReceiver, _fresh_process_summary(), _history(), _make_experiment(), _open_fake_session(), _open_session() (+43 more)

### Community 4 - "execution.py"
Cohesion: 0.09
Nodes (30): clean_observations(), _docker(), _docker_command(), _environment(), ExecutionResult, _inspect_owned(), Isolation, _journal_event() (+22 more)

### Community 5 - "test_approval_scoring.py"
Cohesion: 0.07
Nodes (35): _approval_base(), ApprovalError, ApprovalRecord, build_approval(), load_approval(), _manifest_and_packet(), ReviewerSignoff, validate_approval() (+27 more)

### Community 6 - "M4B3OllamaDispatcher"
Cohesion: 0.12
Nodes (23): _http_request_hash(), M4B3OllamaDispatcher, PreparedRequest, TransportOutcome, dispatcher(), _completion_metadata(), _completion_result(), _prepare_dispatch() (+15 more)

### Community 9 - "Milestone 4B.1 — tool-use feasibility"
Cohesion: 0.13
Nodes (15): calculate(), relay(), run(), choose(), setup(), final_item(), prepare(), convert() (+7 more)

### Community 10 - "AI engineering design"
Cohesion: 0.10
Nodes (24): ProviderResult, test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze(), analyze(), test_fake_file_reference_is_rejected(), generate() (+16 more)

### Community 11 - "test_repair.py"
Cohesion: 0.10
Nodes (14): 4. Tests executed, MockProvider, setup(), test_abstention_requires_missing_information_and_no_primary_hypothesis(), test_completed_result_marks_model_diagnosis_source(), test_fabricated_hypothesis_reference_persists_failure(), test_invalid_events(), test_invalid_path() (+6 more)

### Community 12 - "Store"
Cohesion: 0.08
Nodes (26): fallback_findings(), investigate(), _summed_usage(), assess_snapshot(), add(), reconcile_facts(), review_hypotheses(), Store (+18 more)

### Community 13 - "scan_codebase.py"
Cohesion: 0.21
Nodes (12): AuditResult, explain_findings(), scan_codebase(), main(), _print_finding(), _print_header(), test_ai_explanation_is_attached(), test_scan_finds_pyflakes_and_ast_errors() (+4 more)

### Community 15 - "01_RESEARCH_MASTER_PLAN.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Dependency graphs and limits, Proposed system architecture, Technology feasibility and costs, Development roadmap — proposed, Source index, Open questions and risks

### Community 16 - "RunLock"
Cohesion: 0.08
Nodes (19): _absolute_path(), _file_identity_from_stat(), LockUnavailable, RunLock, _sqlite_rw_uri(), _validate_wal_sidecar(), _seed_attempt(), test_corrupt_database_and_bad_sidecar_fail_closed() (+11 more)

### Community 17 - "test_evidence_facts.py"
Cohesion: 0.25
Nodes (13): validate(), validate_model_output(), abstention(), snapshot(), test_abstention_with_empty_optional_fields_is_completed(), test_correct_frame_description_is_accepted(), test_evidence_id_placeholders_in_missing_evidence_are_replaced(), test_invented_source_line_is_still_rejected() (+5 more)

### Community 18 - "configuration.py"
Cohesion: 0.14
Nodes (9): Milestone 4B: bounded retrieval experiment, Cost and timing, Method and integrity, Milestone 4B paired evaluation, One approved proof of fix, separate from diagnosis, Primary results, Milestone 4B failure analysis and next test, Most informative next test (+1 more)

### Community 19 - "input_handling.py"
Cohesion: 0.12
Nodes (18): total(), parse_amount(), require_full_window(), rolling_sum(), Baseline, freeze and protocol, Ground truth and measured primary runs, Milestone 3C — Complex debugging evaluation, Post-evaluation regression (+10 more)

### Community 20 - "buggy_apps/README.md"
Cohesion: 0.13
Nodes (15): 10. Limits, 11. Recommended targeted fixes (not implemented), 12. Readiness for a restricted Proof-of-Fix prototype, 1. Objective and method, 2. Repository and regression state, 3.1 Fresh pins (equivalent but different snapshots), 3.2 Replay of the exact Milestone 2.8 snapshots, 3.3 Determinism (+7 more)

### Community 21 - "fixtures.py"
Cohesion: 0.07
Nodes (43): configured_provider(), Eligibility, evaluate(), evidence_reference_errors(), hypothesis_digest(), detect_isolation(), build_prompt(), parse_proposal() (+35 more)

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
Cohesion: 0.23
Nodes (27): CaseCategory, CaseId, EvidenceItem, EvidenceType, PatchExpectation, SyntheticScenario, CiCaseConfig, _artifacts() (+19 more)

### Community 28 - "Codex handoff: repair evaluation"
Cohesion: 0.33
Nodes (5): Baseline and environment, Codex handoff: repair evaluation, Fresh live run, Handoff and provenance, Independent fixture audit

### Community 29 - "models.py"
Cohesion: 0.11
Nodes (45): Abstention, AbstentionScope, CaseScore, CausalStatus, Claim, ClaimCategory, EvaluationMode, InvestigationResult (+37 more)

### Community 30 - "42_M4A_BLACKBOX_GAP_ANALYSIS.md"
Cohesion: 0.16
Nodes (9): Changes, Engine, image and live integration tests, Genuine model repair, Milestone 3B.1 — Docker lifecycle validation, Remaining limitations, Differences worth testing, Gap matrix, Milestone 4A — BLACKBOX gap analysis (+1 more)

### Community 31 - "Milestone 4A — experiment designs"
Cohesion: 0.33
Nodes (6): B. Bounded hypothesis-testing investigation, C. Runtime-evidence enrichment, Illustrative resource planning, not measured overhead, Interpretation and sequencing, Milestone 4A — experiment designs, Shared evaluation contract

### Community 32 - "test_ollama_adapter_sends_bounded_schema_and_adaptive_budget"
Cohesion: 0.15
Nodes (8): 4. Tests, test_model_facing_schema_bounds_observation_and_step_lists(), test_ollama_adapter_sends_bounded_schema_and_adaptive_budget(), test_ollama_adapter_uses_structured_output(), post(), test_output_budget_shrinks_for_large_prompts_without_dropping_evidence(), test_truncated_json_is_a_hard_failure(), analyze()

### Community 33 - "start_ollama.ps1"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 34 - "Milestone 3A — restricted Proof-of-Fix engine"
Cohesion: 0.11
Nodes (17): find_index(), 10. Deterministic integration results, 11. What remains unverified, 12. Is Milestone 3B justified?, 13. Not built, 1. What this milestone is, 2. Preserved baseline, 3. Eligibility gate (+9 more)

### Community 35 - "test_repair.py"
Cohesion: 0.19
Nodes (16): approval_for(), approve(), attempt_for(), FakeStore, make_case(), reasons(), test_approval_is_idempotent_and_review_cannot_change_status(), test_gate_blocks_failed_and_abstained_investigations() (+8 more)

### Community 36 - "investigator.py"
Cohesion: 0.13
Nodes (13): create_app(), context(), report(), start_investigation(), collect(), _dedupe(), evidence_hash(), sanitize_output() (+5 more)

### Community 37 - "test_telemetry.py"
Cohesion: 0.10
Nodes (29): build_t1_payload(), _evidence_hash(), load_inventory(), make_log_evidence(), make_metric_evidence(), prepare_t1_case(), read_inject_time(), read_logs() (+21 more)

### Community 38 - "OpenAICompatibleProvider"
Cohesion: 0.07
Nodes (41): _content(), _finish_reason(), FullPacketError, FullPacketRun, FullPacketRunner, _provider_input_tokens(), _usage(), build_prompt() (+33 more)

### Community 39 - "test_ollama_adapter_sends_bounded_schema_and_adaptive_budget"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

### Community 40 - "off_by_one/tests/test_regression.py"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 41 - "extract_facts"
Cohesion: 0.14
Nodes (14): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, validate_frame_narrative() (+6 more)

### Community 42 - "test_agent_retrieval.py"
Cohesion: 0.12
Nodes (22): Dispatcher, _investigate_with_retrieval(), Request, RetrievalError, main(), get_fixture(), _git(), _check_source() (+14 more)

### Community 45 - "real_cases.py"
Cohesion: 0.09
Nodes (33): Readiness, _artifacts(), _bounded_excerpt(), CiFailure, CiLog, ensure_not_approved(), _is_test_path(), _normalise_path() (+25 more)

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

### Community 102 - "hashlib"
Cohesion: 0.22
Nodes (6): record_api(), record_one(), summarize(), frozen(), main(), main()

### Community 139 - "Store"
Cohesion: 0.10
Nodes (21): investigate_with_retrieval(), _BasicLimits, _ExtendedLimits, _IOCounters, run_contained(), Provider, load_registry(), Event (+13 more)

### Community 141 - "Milestone 3D — repository intelligence and paired evaluation"
Cohesion: 0.22
Nodes (7): Milestone 3D paired experiment preregistration, Cost and limitations, Design and data flow, Milestone 3D — repository intelligence and paired evaluation, Pre-registered paired protocol, Primary outcomes, Testing and next milestone

### Community 142 - "retrieve"
Cohesion: 0.16
Nodes (18): _calls(), _LimitedNotes, retrieve(), frame(), repository(), commit(), test_class_method_caller_identifies_owning_class(), test_context_limit_is_explicit() (+10 more)

### Community 143 - "ExternalRepairError"
Cohesion: 0.15
Nodes (16): _apply_patch(), build_evaluator_workspace(), build_workspaces(), changed_files_from_patch(), check_patch_scope(), _copy_worktree(), ExternalRepairError, ExternalRepairSpec (+8 more)

### Community 145 - "argparse"
Cohesion: 0.13
Nodes (10): prepare_p1_case(), review_file(), build_parser(), main(), build_parser(), main(), build_parser(), main() (+2 more)

### Community 147 - "field_validator"
Cohesion: 0.07
Nodes (5): GroundTruth, PatchRecord, _relative_path(), _safe_id(), _unique()

### Community 148 - "test_capture.py"
Cohesion: 0.12
Nodes (17): _api_url(), build_event(), _head_commit(), install_blackbox(), capture_exception(), _relative_frames(), _repo_path(), send_event() (+9 more)

### Community 149 - "_approval_manifest"
Cohesion: 0.19
Nodes (12): initialize_experiment(), _approval_manifest(), _build_run_manifest(), _template_bytes(), test_approval_verification_fails_closed_and_test_verifier_is_isolated(), _test_approval_verifier(), test_individual_fingerprint_inputs_are_resume_blocking(), test_initialization_crash_is_atomic_and_never_calls_receiver() (+4 more)

### Community 150 - "EvidencePacket"
Cohesion: 0.09
Nodes (26): _ensure_evaluable(), evaluate_case(), evaluate_suite(), BDB5Error, BlockedCaseError, ManifestValidationError, PacketValidationError, UnsupportedModeError (+18 more)

### Community 151 - "fixtures.py"
Cohesion: 0.23
Nodes (8): content_pinned(), fixture_path(), _git(), materialize(), revision_available(), trusted(), Engineering lessons and next gate, workspace()

### Community 152 - "Milestone 4A — competitor architectures"
Cohesion: 0.33
Nodes (6): Milestone 4A — competitor architectures, OpenHands repository boundary, OpenHands / Software Agent SDK, Sentry Seer / Autofix, SWE-agent, Synthesis

### Community 153 - "Milestone 2.8 handoff completion"
Cohesion: 0.12
Nodes (16): Continuation fixes (after the interrupted Codex state), Deterministic layer, Final live evaluation, Milestone 2.8 — deterministic evidence layer and abstention reliability, 2026-11-04, Not measured, Recorded failures, kept separate, Tests, 3. Files modified or added (+8 more)

### Community 154 - "test_real_review.py"
Cohesion: 0.46
Nodes (7): _fake_source(), _r1_payload(), _r2_payload(), test_review_accepts_r1_and_r2_boundaries(), test_review_cli_writes_machine_readable_failure(), test_review_rejects_approval_and_application_source_leak_in_r2(), test_review_rejects_top_level_manifest_and_host_path()

### Community 155 - "Milestone 3E — semantic reasoning and safe abstention"
Cohesion: 0.29
Nodes (5): Milestone 3E evaluation preregistration, Limits and next work, Milestone 3E — semantic reasoning and safe abstention, Paired experiment, Previously observed 3D cases

### Community 156 - "cli.py"
Cohesion: 0.24
Nodes (7): build_parser(), _default_output(), _emit(), main(), run_spec_checks(), test_cli_synthetic_case_and_suite_are_read_only_and_classified(), test_spec_checks_and_cli_self_test()

### Community 157 - "test_synthetic_scoring.py"
Cohesion: 0.19
Nodes (19): scenario(), score(), test_every_synthetic_scenario_matches_its_expected_classification(), test_p1_incomplete_f2p_unexecuted_pass_and_regression_failure(), test_p1_invalid_scope_and_test_modification_are_rejected(), test_p1_patch_test_and_regression_dimensions(), test_r1_missing_reproduction_and_citation(), test_r1_patch_free_source_scoring_dimensions() (+11 more)

### Community 158 - "response.py"
Cohesion: 0.12
Nodes (4): Http404, HttpResponsePermanentRedirect, HttpResponseRedirect, HttpResponseRedirectBase

### Community 160 - "bdb5/__init__.py"
Cohesion: 0.09
Nodes (24): CaseManifest, _keys(), PacketReview, _registry_entry(), review_payload(), _strings(), accept_prepared_result(), _case_objects() (+16 more)

### Community 161 - "HttpResponse"
Cohesion: 0.14
Nodes (6): HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseGone, HttpResponseNotFound, HttpResponseServerError

### Community 162 - "test_external_repair.py"
Cohesion: 0.38
Nodes (6): _payload(), test_p1_payload_is_prepared_and_review_passes(), test_p1_scope_accepts_only_the_allowed_file(), test_p1_source_must_be_pinned(), test_p1_vault_is_separate_and_loads(), test_p1_visible_packet_contains_only_issue_and_source()

### Community 163 - "evaluate_m4b3.py"
Cohesion: 0.07
Nodes (35): canonical_bytes(), CommitAmbiguous, _configure(), evaluation_id(), _event_hash(), _insert_event(), LedgerError, manifest_fingerprint() (+27 more)

### Community 166 - "digest"
Cohesion: 0.18
Nodes (8): IssueCaseConfig, IssuePreparationError, prepare_issue_case(), PreparedIssueCase, _sha(), _source_excerpt(), build_parser(), main()

### Community 169 - "BLACKBOX â€” local evidence and AI investigation"
Cohesion: 0.29
Nodes (7): AI investigation (opt-in), BLACKBOX â€” local evidence and AI investigation, Limits, One-command demo, Restricted Proof-of-Fix (Milestone 3A), Run the service and tests, Setup

### Community 181 - "ProviderError"
Cohesion: 0.12
Nodes (11): _FinalProvider, ProviderError, test_ollama_rejects_truncated_completion(), test_oversized_evidence_reports_a_distinct_failure(), analyze(), test_provider_unavailable_is_reported_separately(), analyze(), test_truncated_completion_keeps_token_usage() (+3 more)

### Community 182 - "fastapi_capture_demo.py"
Cohesion: 0.47
Nodes (3): calculate_average(), crash(), health()

### Community 196 - "Findings"
Cohesion: 0.15
Nodes (11): Claim, Findings, Hypothesis, InvestigationRequest, missing_evidence_references(), normalize_abstention(), _recorded_missing_text(), test_abstention_maps_verbatim_missing_text_but_not_invented_text() (+3 more)

## Knowledge Gaps
- **116 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `investigate()` connect `Store` to `test_repair.py`, `investigator.py`, `hashlib`, `extract_facts`, `test_agent_retrieval.py`, `Store`, `Milestone 4B.1 — tool-use feasibility`, `test_evidence_facts.py`, `ProviderError`, `fixtures.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `LedgerBlocked` (e.g. with `M4B3OllamaDispatcher` and `_open_fake_session()`) actually correct?**
  _`LedgerBlocked` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `LedgerBlocked` be split into smaller, more focused modules?**
  _Cohesion score 0.0880281690140845 - nodes in this community are weakly interconnected._
- **Why does `evidence_hash()` connect `investigator.py` to `hashlib`, `BLACKBOX â€” local evidence and AI investigation`, `Store`, `buggy_apps/README.md`, `fixtures.py`, `Investigation evaluation record`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `Ledger` (e.g. with `_open_fake_session()` and `RunSession`) actually correct?**
  _`Ledger` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08170731707317073 - nodes in this community are weakly interconnected._
- **Why does `content_pinned()` connect `fixtures.py` to `investigator.py`, `hashlib`, `Store`, `input_handling.py`, `fixtures.py`, `Codex handoff: repair evaluation`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._