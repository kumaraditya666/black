# Graph Report - black  (2026-11-14)

## Corpus Check
- 252 files · ~208,524 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .log 4, (none) 2, .example 1)

## Summary
- 2255 nodes · 6563 edges · 195 communities (77 shown, 118 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 635 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0aeca1ff`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pipeline.py
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
- investigate
- 4. Tests
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
- test_semantic_verification.py
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
- repair_cli.py
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
- investigate.py
- HttpResponseBase
- field_validator
- test_capture.py
- LedgerBlocked
- EvidencePacket
- .analyze
- Milestone 4A — competitor architectures
- Milestone 2.8 handoff completion
- test_real_review.py
- Milestone 3E — semantic reasoning and safe abstention
- buggy_app.py
- test_synthetic_scoring.py
- response.py
- StreamingHttpResponse
- bdb5/__init__.py
- HttpResponse
- test_external_repair.py
- evaluate_m4b3.py
- _ReceiverHandler
- Milestone 2.9.1 — bounded model schema and adaptive output budget, 2026-11-04
- digest
- _ResponseMutationTransport
- .__init__
- BLACKBOX â€” local evidence and AI investigation
- Milestone 2.8 — deterministic evidence layer and abstention reliability, 2026-11-04
- Milestone 4B failure analysis and next test
- test_ollama_rejects_truncated_completion
- Milestone 3A — restricted Proof-of-Fix, 2026-11-04
- test_fake_cli_defaults_lock_beside_temporary_ledger
- ._content_type_for_repr
- ._convert_to_charset
- providers.py
- capture.py
- 3. Mechanical results
- Job
- division_by_zero/tests/test_regression.py
- snapshot

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
- `Existing runner and measured controls` --references--> `run_tests()`  [INFERRED]
  research/30_M3B_DOCKER_VALIDATION.md → blackbox/repair/execution.py
- `Pinned fixture checks` --references--> `run_tests()`  [INFERRED]
  research/30_M3B_DOCKER_VALIDATION.md → blackbox/repair/execution.py
- `Milestone 2.9 — repetition and stability, 2026-11-04` --references--> `evidence_hash()`  [INFERRED]
  EVALUATION.md → blackbox/investigator.py
- `AI investigation (opt-in)` --references--> `evidence_hash()`  [INFERRED]
  README.md → blackbox/investigator.py

## Import Cycles
- None detected.

## Communities (195 total, 118 thin omitted)

### Community 0 - "pipeline.py"
Cohesion: 0.18
Nodes (7): build_prompt(), parse_proposal(), PatchFormatError, PatchRejected, validate_and_apply(), PatchChange, PatchProposal

### Community 1 - "LedgerBlocked"
Cohesion: 0.08
Nodes (17): _completion_derivation_sha256(), _derive_completion_from_response(), DispatchPermit, DispatchResponseReceipt, EvaluationState, FailureEvidence, _is_hash(), Ledger (+9 more)

### Community 2 - "test_engine.py"
Cohesion: 0.08
Nodes (33): git(), plan(), source(), validate_response(), validate_template(), verify_local_model(), verify_model_config(), Attribution (+25 more)

### Community 3 - "test_m4b3_ledger.py"
Cohesion: 0.10
Nodes (52): execute(), _eval_id(), FakeReceiver, _fresh_process_summary(), _history(), _make_experiment(), _open_fake_session(), _open_session() (+44 more)

### Community 4 - "execution.py"
Cohesion: 0.11
Nodes (25): _docker(), _docker_command(), _environment(), ExecutionResult, _inspect_owned(), Isolation, _journal_event(), recover_container() (+17 more)

### Community 5 - "test_approval_scoring.py"
Cohesion: 0.07
Nodes (32): _approval_base(), ApprovalError, ApprovalRecord, build_approval(), _manifest_and_packet(), ReviewerSignoff, validate_approval(), label_vault_hash() (+24 more)

### Community 6 - "M4B3OllamaDispatcher"
Cohesion: 0.12
Nodes (19): M4B3OllamaDispatcher, PreparedRequest, TransportOutcome, dispatcher(), _completion_metadata(), _completion_result(), _prepare_dispatch(), test_completion_is_rederived_from_receipt_and_schema() (+11 more)

### Community 8 - "pathlib"
Cohesion: 0.07
Nodes (6): _BasicLimits, _ExtendedLimits, _IOCounters, Claim, Hypothesis, InvestigationRequest

### Community 9 - "Milestone 4B.1 — tool-use feasibility"
Cohesion: 0.14
Nodes (14): calculate(), relay(), run(), choose(), setup(), final_item(), prepare(), convert() (+6 more)

### Community 10 - "AI engineering design"
Cohesion: 0.11
Nodes (25): ProviderResult, test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze(), test_fake_file_reference_is_rejected(), generate(), test_injected_text_is_not_promoted_to_verified_facts() (+17 more)

### Community 11 - "test_repair.py"
Cohesion: 0.10
Nodes (12): MockProvider, setup(), test_abstention_requires_missing_information_and_no_primary_hypothesis(), test_completed_result_marks_model_diagnosis_source(), test_invalid_events(), test_invalid_path(), test_investigation_caching_and_new_evidence(), test_mocked_scenarios() (+4 more)

### Community 12 - "investigate"
Cohesion: 0.08
Nodes (16): create_app(), context(), start_investigation(), collect(), evidence_hash(), fallback_findings(), investigate(), _summed_usage() (+8 more)

### Community 13 - "4. Tests"
Cohesion: 0.22
Nodes (9): 4. Tests, test_model_facing_schema_bounds_observation_and_step_lists(), test_output_budget_shrinks_for_large_prompts_without_dropping_evidence(), test_oversized_evidence_reports_a_distinct_failure(), analyze(), test_truncated_completion_keeps_token_usage(), analyze(), test_truncated_json_is_a_hard_failure() (+1 more)

### Community 15 - "01_RESEARCH_MASTER_PLAN.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Dependency graphs and limits, Proposed system architecture, Technology feasibility and costs, Development roadmap — proposed, Source index, Open questions and risks

### Community 16 - "RunLock"
Cohesion: 0.13
Nodes (8): _absolute_path(), _file_identity_from_stat(), LockUnavailable, RunLock, _sqlite_ro_uri(), _sqlite_rw_uri(), test_forked_child_cannot_reuse_or_release_parent_run_lock(), test_lock_ownership_detects_path_replacement_and_database_identity()

### Community 17 - "test_evidence_facts.py"
Cohesion: 0.21
Nodes (20): Findings, missing_evidence_references(), normalize_abstention(), _recorded_missing_text(), validate(), validate_model_output(), abstention(), test_abstention_maps_verbatim_missing_text_but_not_invented_text() (+12 more)

### Community 18 - "configuration.py"
Cohesion: 0.12
Nodes (12): Engine and image, Existing runner and measured controls, Milestone 3B — Docker isolation validation, Pinned fixture checks, Project regression and remaining work, Real Proof-of-Fix, Milestone 4B: bounded retrieval experiment, Cost and timing (+4 more)

### Community 19 - "input_handling.py"
Cohesion: 0.12
Nodes (18): total(), parse_amount(), require_full_window(), rolling_sum(), Baseline, freeze and protocol, Ground truth and measured primary runs, Milestone 3C — Complex debugging evaluation, Post-evaluation regression (+10 more)

### Community 20 - "buggy_apps/README.md"
Cohesion: 0.18
Nodes (11): 10. Limits, 11. Recommended targeted fixes (not implemented), 12. Readiness for a restricted Proof-of-Fix prototype, 1. Objective and method, 2. Repository and regression state, 4. Deterministic facts versus model hypotheses, 5. Contradictory explanations for identical evidence, 7. Failure mode analysis (+3 more)

### Community 21 - "fixtures.py"
Cohesion: 0.09
Nodes (32): configured_provider(), Eligibility, evaluate(), evidence_reference_errors(), hypothesis_digest(), detect_isolation(), content_pinned(), fixture_path() (+24 more)

### Community 22 - "Investigation evaluation record"
Cohesion: 0.14
Nodes (14): Codex handoff revalidation — 2026-11-05, Investigation evaluation record, Milestone 2.5 — local availability check, 2026-11-04, Milestone 2.6 — measured local inference, 2026-11-04, Milestone 2.7 — evidence and abstention, 2026-11-04, Milestone 2.9 — repetition and stability, 2026-11-04, Milestone 3B.1 Docker lifecycle — 2026-11-05, Milestone 3B Docker validation — 2026-11-05 (+6 more)

### Community 23 - "Milestone 2.9.1 — structured-output reliability fix and revalidation"
Cohesion: 0.14
Nodes (13): 1. Confirmed failure mechanism, 2. Schema fix, 3. Adaptive output budget, 5. Revalidation protocol, 6. Results, 7. Quality gate, 8. Remaining issues, 9. Readiness for a restricted Proof-of-Fix prototype (+5 more)

### Community 24 - "pytest"
Cohesion: 0.11
Nodes (7): test_invalid_text_is_rejected(), test_none_is_rejected(), test_none_is_rejected_as_invalid_argument(), test_average_rejects_empty_input(), test_case(), test_bad_input(), test_average_rejects_empty_input()

### Community 25 - "Open-source architecture research"
Cohesion: 0.20
Nodes (10): Architecture assessment, Benchmarks and acceptance tests, Development skills and tools, Differentiation to validate, Evidence and outstanding research, Exact first development milestone, MVP and dependencies, Research readiness audit (+2 more)

### Community 26 - "Quality and evaluation plan"
Cohesion: 0.20
Nodes (8): Baseline and diagnosis of the 3E failure, Changes, Controlled comparison and interpretation, Frozen new cases and ground truth, Milestone 3F — evidence-grounded causal reasoning, Remaining risks and next work, Final validation iteration (registered after exploratory run, before this iteration), Milestone 3F preregistration

### Community 27 - "CaseId"
Cohesion: 0.12
Nodes (36): build_parser(), _default_output(), _emit(), main(), evaluate_suite(), CaseCategory, CaseId, EvidenceItem (+28 more)

### Community 28 - "Codex handoff: repair evaluation"
Cohesion: 0.33
Nodes (5): Baseline and environment, Codex handoff: repair evaluation, Fresh live run, Handoff and provenance, Independent fixture audit

### Community 29 - "models.py"
Cohesion: 0.14
Nodes (34): Abstention, AbstentionScope, CaseScore, CausalStatus, Claim, ClaimCategory, EvaluationMode, InvestigationResult (+26 more)

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
Nodes (18): find_index(), 10. Deterministic integration results, 11. What remains unverified, 12. Is Milestone 3B justified?, 13. Not built, 1. What this milestone is, 2. Preserved baseline, 3. Eligibility gate (+10 more)

### Community 35 - "test_repair.py"
Cohesion: 0.20
Nodes (15): approval_for(), attempt_for(), FakeStore, make_case(), reasons(), test_approval_is_idempotent_and_review_cannot_change_status(), test_gate_blocks_failed_and_abstained_investigations(), test_gate_blocks_missing_revision_unresolved_frame_and_bad_references() (+7 more)

### Community 36 - "test_semantic_verification.py"
Cohesion: 0.11
Nodes (21): report(), clean_observations(), sanitize_output(), validate_frame_narrative(), redact(), _git(), _safe_path(), assess_snapshot() (+13 more)

### Community 37 - "test_telemetry.py"
Cohesion: 0.09
Nodes (29): build_t1_payload(), _evidence_hash(), load_inventory(), make_log_evidence(), make_metric_evidence(), prepare_t1_case(), read_inject_time(), read_logs() (+21 more)

### Community 38 - "OpenAICompatibleProvider"
Cohesion: 0.06
Nodes (50): load_approval(), _content(), _finish_reason(), FullPacketError, FullPacketRun, FullPacketRunner, _provider_input_tokens(), _usage() (+42 more)

### Community 39 - "test_ollama_adapter_sends_bounded_schema_and_adaptive_budget"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

### Community 40 - "off_by_one/tests/test_regression.py"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 41 - "extract_facts"
Cohesion: 0.16
Nodes (13): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, 1. Original Codex state (+5 more)

### Community 42 - "test_agent_retrieval.py"
Cohesion: 0.09
Nodes (21): Dispatcher, _investigate_with_retrieval(), Request, RetrievalError, main(), get_fixture(), UNDERSTAND WHAT WE JUST BUILT, oracle_excerpt() (+13 more)

### Community 45 - "real_cases.py"
Cohesion: 0.11
Nodes (28): Readiness, _artifacts(), _bounded_excerpt(), CiFailure, CiLog, ensure_not_approved(), _is_test_path(), _normalise_path() (+20 more)

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
Cohesion: 0.16
Nodes (15): _dedupe(), main(), main(), command_approve(), command_attempt(), command_eligibility(), command_list(), command_review() (+7 more)

### Community 139 - "Store"
Cohesion: 0.11
Nodes (19): investigate_with_retrieval(), run_contained(), Provider, load_registry(), Event, Frame, ConflictError, Boundary and security checks (+11 more)

### Community 141 - "Milestone 3D — repository intelligence and paired evaluation"
Cohesion: 0.25
Nodes (6): Milestone 3D paired experiment preregistration, Cost and limitations, Milestone 3D — repository intelligence and paired evaluation, Pre-registered paired protocol, Primary outcomes, Testing and next milestone

### Community 142 - "retrieve"
Cohesion: 0.15
Nodes (19): _calls(), _LimitedNotes, retrieve(), frame(), repository(), commit(), test_class_method_caller_identifies_owning_class(), test_context_limit_is_explicit() (+11 more)

### Community 143 - "ExternalRepairError"
Cohesion: 0.17
Nodes (13): _apply_patch(), build_evaluator_workspace(), build_workspaces(), changed_files_from_patch(), _copy_worktree(), ExternalRepairError, ExternalRepairSpec, _git() (+5 more)

### Community 147 - "field_validator"
Cohesion: 0.07
Nodes (6): CaseManifest, GroundTruth, PatchRecord, _relative_path(), _safe_id(), _unique()

### Community 148 - "test_capture.py"
Cohesion: 0.18
Nodes (9): build_event(), _relative_frames(), _raise_from_repo(), _raise_outside(), repo(), test_build_event_ignores_dependency_frames_inside_the_repository(), test_build_event_maps_only_repository_frames(), test_build_event_rejects_an_exception_without_repository_frames() (+1 more)

### Community 149 - "LedgerBlocked"
Cohesion: 0.12
Nodes (26): LedgerBlocked, _validate_wal_sidecar(), initialize_experiment(), _approval_manifest(), _build_run_manifest(), _seed_attempt(), test_approval_verification_fails_closed_and_test_verifier_is_isolated(), _test_approval_verifier() (+18 more)

### Community 150 - "EvidencePacket"
Cohesion: 0.11
Nodes (28): _ensure_evaluable(), evaluate_case(), BDB5Error, BlockedCaseError, ManifestValidationError, PacketValidationError, UnsupportedModeError, EvidencePacket (+20 more)

### Community 151 - ".analyze"
Cohesion: 0.22
Nodes (8): 4. Tests executed, test_fabricated_hypothesis_reference_persists_failure(), analyze(), test_likely_cause_requires_resolved_source_and_event(), analyze(), test_model_cannot_assert_verified_root_cause(), analyze(), test_unverifiable_observation_is_discarded_not_fatal()

### Community 152 - "Milestone 4A — competitor architectures"
Cohesion: 0.33
Nodes (6): Milestone 4A — competitor architectures, OpenHands repository boundary, OpenHands / Software Agent SDK, Sentry Seer / Autofix, SWE-agent, Synthesis

### Community 153 - "Milestone 2.8 handoff completion"
Cohesion: 0.33
Nodes (5): 3. Files modified or added, 6. Before and after, 7. Unresolved issues, 8. Final status, Milestone 2.8 handoff completion

### Community 154 - "test_real_review.py"
Cohesion: 0.46
Nodes (7): _fake_source(), _r1_payload(), _r2_payload(), test_review_accepts_r1_and_r2_boundaries(), test_review_cli_writes_machine_readable_failure(), test_review_rejects_approval_and_application_source_leak_in_r2(), test_review_rejects_top_level_manifest_and_host_path()

### Community 155 - "Milestone 3E — semantic reasoning and safe abstention"
Cohesion: 0.29
Nodes (5): Milestone 3E evaluation preregistration, Limits and next work, Milestone 3E — semantic reasoning and safe abstention, Paired experiment, Previously observed 3D cases

### Community 156 - "buggy_app.py"
Cohesion: 0.40
Nodes (5): Final live evaluation, 5. Actual live model results, 6. Unsupported claims and invalid evidence references, calculate_average(), main()

### Community 157 - "test_synthetic_scoring.py"
Cohesion: 0.20
Nodes (18): scenario(), score(), test_p1_incomplete_f2p_unexecuted_pass_and_regression_failure(), test_p1_invalid_scope_and_test_modification_are_rejected(), test_p1_patch_test_and_regression_dimensions(), test_r1_missing_reproduction_and_citation(), test_r1_patch_free_source_scoring_dimensions(), test_r1_unexecuted_pass_is_an_execution_overclaim() (+10 more)

### Community 158 - "response.py"
Cohesion: 0.12
Nodes (4): Http404, HttpResponsePermanentRedirect, HttpResponseRedirect, HttpResponseRedirectBase

### Community 160 - "bdb5/__init__.py"
Cohesion: 0.08
Nodes (26): _keys(), PacketReview, _registry_entry(), review_file(), review_payload(), _strings(), accept_prepared_result(), _case_objects() (+18 more)

### Community 161 - "HttpResponse"
Cohesion: 0.14
Nodes (6): HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseGone, HttpResponseNotFound, HttpResponseServerError

### Community 162 - "test_external_repair.py"
Cohesion: 0.16
Nodes (13): build_p1_payload(), check_patch_scope(), prepare_p1_case(), sha256_text(), build_parser(), main(), _payload(), test_p1_payload_is_prepared_and_review_passes() (+5 more)

### Community 163 - "evaluate_m4b3.py"
Cohesion: 0.07
Nodes (36): canonical_bytes(), CommitAmbiguous, _configure(), evaluation_id(), _event_hash(), _insert_event(), LedgerError, manifest_fingerprint() (+28 more)

### Community 165 - "Milestone 2.9.1 — bounded model schema and adaptive output budget, 2026-11-04"
Cohesion: 0.33
Nodes (6): Changes, Confirmed cause, Milestone 2.9.1 — bounded model schema and adaptive output budget, 2026-11-04, Readiness, Remaining issues, Revalidation

### Community 166 - "digest"
Cohesion: 0.13
Nodes (15): IssueCaseConfig, IssuePreparationError, prepare_issue_case(), PreparedIssueCase, _sha(), _source_excerpt(), canonical_json(), digest() (+7 more)

### Community 169 - "BLACKBOX â€” local evidence and AI investigation"
Cohesion: 0.29
Nodes (7): AI investigation (opt-in), BLACKBOX â€” local evidence and AI investigation, Limits, One-command demo, Restricted Proof-of-Fix (Milestone 3A), Run the service and tests, Setup

### Community 170 - "Milestone 2.8 — deterministic evidence layer and abstention reliability, 2026-11-04"
Cohesion: 0.33
Nodes (6): Continuation fixes (after the interrupted Codex state), Deterministic layer, Milestone 2.8 — deterministic evidence layer and abstention reliability, 2026-11-04, Not measured, Recorded failures, kept separate, Tests

### Community 172 - "Milestone 4B failure analysis and next test"
Cohesion: 0.50
Nodes (3): Milestone 4B failure analysis and next test, Most informative next test, Security and coverage status

### Community 174 - "Milestone 3A — restricted Proof-of-Fix, 2026-11-04"
Cohesion: 0.33
Nodes (6): Deterministic tests and isolation, Measured cost, Milestone 3A — restricted Proof-of-Fix, 2026-11-04, Result, The key inversion, Visible limitations

### Community 181 - "providers.py"
Cohesion: 0.12
Nodes (8): _FinalProvider, output_budget(), ProviderError, Implemented interface and limits, main(), test_ollama_local_only(), test_retry_provider_failure_keeps_both_usage_and_fails(), analyze()

### Community 182 - "capture.py"
Cohesion: 0.16
Nodes (10): _api_url(), _head_commit(), install_blackbox(), capture_exception(), _repo_path(), send_event(), calculate_average(), crash() (+2 more)

### Community 183 - "3. Mechanical results"
Cohesion: 0.50
Nodes (4): 3.1 Fresh pins (equivalent but different snapshots), 3.2 Replay of the exact Milestone 2.8 snapshots, 3.3 Determinism, 3. Mechanical results

## Knowledge Gaps
- **118 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evidence_hash()` connect `investigate` to `test_semantic_verification.py`, `repair_cli.py`, `BLACKBOX â€” local evidence and AI investigation`, `buggy_apps/README.md`, `Investigation evaluation record`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `LedgerBlocked` (e.g. with `M4B3OllamaDispatcher` and `_open_fake_session()`) actually correct?**
  _`LedgerBlocked` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `LedgerBlocked` be split into smaller, more focused modules?**
  _Cohesion score 0.07927565392354124 - nodes in this community are weakly interconnected._
- **Why does `HttpResponseBase` connect `HttpResponseBase` to `HttpResponse`, `._content_type_for_repr`, `._convert_to_charset`, `.serialize_headers`, `response.py`, `StreamingHttpResponse`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `Ledger` (e.g. with `_open_fake_session()` and `RunSession`) actually correct?**
  _`Ledger` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_engine.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08170731707317073 - nodes in this community are weakly interconnected._
- **Why does `investigate()` connect `investigate` to `test_repair.py`, `test_semantic_verification.py`, `repair_cli.py`, `extract_facts`, `test_agent_retrieval.py`, `Store`, `AI engineering design`, `test_evidence_facts.py`, `providers.py`, `fixtures.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._