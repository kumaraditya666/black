# Graph Report - black  (2026-11-14)

## Corpus Check
- 258 files · ~212,758 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .log 3, (none) 2, .example 1)

## Summary
- 2374 nodes · 6895 edges · 179 communities (70 shown, 109 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 639 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `30bfde45`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- m4b3_ledger.py
- LedgerBlocked
- test_engine.py
- test_m4b3_ledger.py
- execution.py
- test_approval_scoring.py
- M4B3OllamaDispatcher
- pathlib
- cloud.py
- AI engineering design
- test_engine.py
- Store
- pipeline.py
- app.js
- 01_RESEARCH_MASTER_PLAN.md
- RunLock
- test_cloud.py
- configuration.py
- input_handling.py
- buggy_apps/README.md
- time
- Investigation evaluation record
- Milestone 2.9.1 — structured-output reliability fix and revalidation
- pytest
- Open-source architecture research
- Quality and evaluation plan
- CaseId
- Codex handoff: repair evaluation
- scoring.py
- 42_M4A_BLACKBOX_GAP_ANALYSIS.md
- Milestone 2.9.1 — bounded model schema and adaptive output budget, 2026-11-04
- Milestone 3A — restricted Proof-of-Fix, 2026-11-04
- start_ollama.ps1
- Milestone 3A — restricted Proof-of-Fix engine
- test_repair.py
- investigator.py
- test_telemetry.py
- OpenAICompatibleProvider
- test_ollama_adapter_sends_bounded_schema_and_adaptive_budget
- off_by_one/tests/test_regression.py
- test_evidence_facts.py
- test_agent_retrieval.py
- real_cases.py
- unreproducible/app.py
- 12_COMPETITIVE_GAP_ANALYSIS.md
- Path
- Exception
- m3c_trim_total/tests/test_regression.py
- m3c_window/tests/test_regression.py
- evaluate_m29.py
- .analyze
- m4b_negative/tests/test_reproduction.py
- m4b_inventory/tests/test_regression.py
- m4b_average/tests/test_reproduction.py
- m4b_negative/tests/test_regression.py
- Milestone 3B.1 — Docker lifecycle validation
- m4b1_caller/tests/test_regression.py
- m4b1_config/tests/test_regression.py
- m4b1_index/tests/test_regression.py
- m4b1_negative/tests/test_regression.py
- uuid
- Milestone 3D — repository intelligence and paired evaluation
- retrieve
- external_repair.py
- investigate.py
- HttpResponseBase
- field_validator
- test_capture.py
- test_m4b3_ledger.py
- validation.py
- json
- Milestone 4A — competitor architectures
- Milestone 2.8 handoff completion
- test_real_review.py
- Milestone 3E — semantic reasoning and safe abstention
- test_synthetic_scoring.py
- response.py
- StreamingHttpResponse
- bdb5/__init__.py
- HttpResponse
- evaluate_m4b3.py
- digest
- _ResponseMutationTransport
- .__init__
- BLACKBOX â€” local evidence and AI investigation
- limit
- ._content_type_for_repr
- test_agent_deadline.py

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
10. `EvidencePacket` - 42 edges

## Surprising Connections (you probably didn't know these)
- `4. Patch generator` --references--> `PatchProposal`  [INFERRED]
  research/27_M3A_PROOF_OF_FIX.md → blackbox/repair/schema.py
- `Existing runner and measured controls` --references--> `run_tests()`  [INFERRED]
  research/30_M3B_DOCKER_VALIDATION.md → blackbox/repair/execution.py
- `Pinned fixture checks` --references--> `run_tests()`  [INFERRED]
  research/30_M3B_DOCKER_VALIDATION.md → blackbox/repair/execution.py
- `Independent fixture audit` --references--> `content_pinned()`  [INFERRED]
  research/29_CODEX_HANDOFF_REPAIR_EVALUATION.md → blackbox/repair/fixtures.py
- `Baseline, freeze and protocol` --references--> `content_pinned()`  [INFERRED]
  research/32_M3C_COMPLEX_DEBUGGING_EVALUATION.md → blackbox/repair/fixtures.py

## Import Cycles
- None detected.

## Communities (179 total, 109 thin omitted)

### Community 0 - "m4b3_ledger.py"
Cohesion: 0.08
Nodes (22): canonical_bytes(), CommitAmbiguous, _completion_derivation_sha256(), _configure(), _derive_completion_from_response(), DispatchPermit, DispatchResponseReceipt, EvaluationState (+14 more)

### Community 1 - "LedgerBlocked"
Cohesion: 0.13
Nodes (11): FailureEvidence, Ledger, op(), op(), op(), op(), op(), op() (+3 more)

### Community 2 - "test_engine.py"
Cohesion: 0.07
Nodes (37): Credentials, Explanation, ProjectIn, FixSuggestion, git(), plan(), source(), validate_response() (+29 more)

### Community 3 - "test_m4b3_ledger.py"
Cohesion: 0.13
Nodes (41): execute(), _eval_id(), FakeReceiver, _fresh_process_summary(), _history(), _make_experiment(), _open_session(), _run_child() (+33 more)

### Community 4 - "execution.py"
Cohesion: 0.11
Nodes (24): _docker(), _docker_command(), _environment(), ExecutionResult, _inspect_owned(), Isolation, _journal_event(), recover_container() (+16 more)

### Community 5 - "test_approval_scoring.py"
Cohesion: 0.07
Nodes (35): _approval_base(), ApprovalError, ApprovalRecord, build_approval(), load_approval(), _manifest_and_packet(), ReviewerSignoff, validate_approval() (+27 more)

### Community 6 - "M4B3OllamaDispatcher"
Cohesion: 0.12
Nodes (19): M4B3OllamaDispatcher, PreparedRequest, TransportOutcome, dispatcher(), _completion_metadata(), _completion_result(), _prepare_dispatch(), test_completion_is_rederived_from_receipt_and_schema() (+11 more)

### Community 8 - "pathlib"
Cohesion: 0.07
Nodes (5): _BasicLimits, _IOCounters, record_api(), record_one(), summarize()

### Community 9 - "cloud.py"
Cohesion: 0.12
Nodes (27): Request, _connect(), create_cloud_app(), create_project(), db_dependency(), explain(), ingest(), issue() (+19 more)

### Community 10 - "AI engineering design"
Cohesion: 0.06
Nodes (44): ProviderResult, assess_execution(), Implementation, test_abstention_citing_recorded_unresolved_frame_line_is_accepted(), analyze(), test_abstention_pasting_missing_evidence_text_is_accepted(), analyze(), analyze() (+36 more)

### Community 11 - "test_engine.py"
Cohesion: 0.04
Nodes (31): _FinalProvider, output_budget(), ProviderError, 4. Tests executed, 4. Tests, Implemented interface and limits, MockProvider, test_abstention_requires_missing_information_and_no_primary_hypothesis() (+23 more)

### Community 12 - "Store"
Cohesion: 0.17
Nodes (12): Store, command_approve(), command_attempt(), command_eligibility(), command_list(), command_review(), command_show(), _investigation_or_exit() (+4 more)

### Community 13 - "pipeline.py"
Cohesion: 0.15
Nodes (15): build_prompt(), parse_proposal(), PatchFormatError, PatchRejected, validate_and_apply(), _drop(), _elapsed(), _now() (+7 more)

### Community 14 - "app.js"
Cohesion: 0.24
Nodes (19): api(), app, auth, esc(), explainIssue(), fmt(), loadProjects(), renderEmptyProject() (+11 more)

### Community 15 - "01_RESEARCH_MASTER_PLAN.md"
Cohesion: 0.12
Nodes (8): Tool readiness, Architecture hypotheses, Dependency graphs and limits, Proposed system architecture, Technology feasibility and costs, Development roadmap — proposed, Source index, Open questions and risks

### Community 16 - "RunLock"
Cohesion: 0.13
Nodes (8): _absolute_path(), _file_identity_from_stat(), LockUnavailable, RunLock, _sqlite_rw_uri(), _validate_wal_sidecar(), test_forked_child_cannot_reuse_or_release_parent_run_lock(), test_lock_ownership_detects_path_replacement_and_database_identity()

### Community 17 - "test_cloud.py"
Cohesion: 0.33
Nodes (10): client(), _event(), _project(), repo(), _signup(), test_another_account_cannot_read_the_project(), test_dashboard_and_auth_flow(), test_explain_uses_provider_and_persists_result() (+2 more)

### Community 18 - "configuration.py"
Cohesion: 0.12
Nodes (10): Engine and image, Existing runner and measured controls, Milestone 3B — Docker isolation validation, Pinned fixture checks, Project regression and remaining work, Real Proof-of-Fix, Milestone 4B: bounded retrieval experiment, Milestone 4B failure analysis and next test (+2 more)

### Community 19 - "input_handling.py"
Cohesion: 0.12
Nodes (19): total(), parse_amount(), require_full_window(), rolling_sum(), Baseline, freeze and protocol, Ground truth and measured primary runs, Milestone 3C — Complex debugging evaluation, Post-evaluation regression (+11 more)

### Community 20 - "buggy_apps/README.md"
Cohesion: 0.14
Nodes (14): 10. Limits, 11. Recommended targeted fixes (not implemented), 12. Readiness for a restricted Proof-of-Fix prototype, 2. Repository and regression state, 3.1 Fresh pins (equivalent but different snapshots), 3.2 Replay of the exact Milestone 2.8 snapshots, 3.3 Determinism, 3. Mechanical results (+6 more)

### Community 21 - "time"
Cohesion: 0.12
Nodes (18): configured_provider(), Eligibility, evaluate(), evidence_reference_errors(), hypothesis_digest(), detect_isolation(), ConflictError, head() (+10 more)

### Community 22 - "Investigation evaluation record"
Cohesion: 0.10
Nodes (20): Codex handoff revalidation — 2026-11-05, Continuation fixes (after the interrupted Codex state), Deterministic layer, Final live evaluation, Investigation evaluation record, Milestone 2.5 — local availability check, 2026-11-04, Milestone 2.6 — measured local inference, 2026-11-04, Milestone 2.7 — evidence and abstention, 2026-11-04 (+12 more)

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
Nodes (55): Abstention, AbstentionScope, CaseCategory, CaseId, CausalStatus, Claim, ClaimCategory, EvidenceItem (+47 more)

### Community 28 - "Codex handoff: repair evaluation"
Cohesion: 0.33
Nodes (5): Baseline and environment, Codex handoff: repair evaluation, Fresh live run, Handoff and provenance, Independent fixture audit

### Community 29 - "scoring.py"
Cohesion: 0.09
Nodes (28): build_parser(), _default_output(), _emit(), main(), _ensure_evaluable(), evaluate_suite(), UnsupportedModeError, CaseScore (+20 more)

### Community 30 - "42_M4A_BLACKBOX_GAP_ANALYSIS.md"
Cohesion: 0.11
Nodes (15): Changes, Engine, image and live integration tests, Genuine model repair, Milestone 3B.1 — Docker lifecycle validation, Remaining limitations, Differences worth testing, Gap matrix, Milestone 4A — BLACKBOX gap analysis (+7 more)

### Community 31 - "Milestone 2.9.1 — bounded model schema and adaptive output budget, 2026-11-04"
Cohesion: 0.33
Nodes (6): Changes, Confirmed cause, Milestone 2.9.1 — bounded model schema and adaptive output budget, 2026-11-04, Readiness, Remaining issues, Revalidation

### Community 32 - "Milestone 3A — restricted Proof-of-Fix, 2026-11-04"
Cohesion: 0.33
Nodes (6): Deterministic tests and isolation, Measured cost, Milestone 3A — restricted Proof-of-Fix, 2026-11-04, Result, The key inversion, Visible limitations

### Community 33 - "start_ollama.ps1"
Cohesion: 0.29
Nodes (5): Discovery, Issue fix (documented API workflow), Seer user journeys, Setup and agent entry, Executive research summary

### Community 34 - "Milestone 3A — restricted Proof-of-Fix engine"
Cohesion: 0.11
Nodes (17): find_index(), 10. Deterministic integration results, 11. What remains unverified, 12. Is Milestone 3B justified?, 13. Not built, 1. What this milestone is, 2. Preserved baseline, 3. Eligibility gate (+9 more)

### Community 35 - "test_repair.py"
Cohesion: 0.18
Nodes (17): approval_for(), approve(), attempt_for(), FakeStore, make_case(), PatchProvider, reasons(), test_approval_is_idempotent_and_review_cannot_change_status() (+9 more)

### Community 36 - "investigator.py"
Cohesion: 0.08
Nodes (26): create_app(), context(), report(), start_investigation(), clean_observations(), collect(), evidence_hash(), fallback_findings() (+18 more)

### Community 37 - "test_telemetry.py"
Cohesion: 0.09
Nodes (29): build_t1_payload(), _evidence_hash(), load_inventory(), make_log_evidence(), make_metric_evidence(), prepare_t1_case(), read_inject_time(), read_logs() (+21 more)

### Community 38 - "OpenAICompatibleProvider"
Cohesion: 0.07
Nodes (44): _content(), _finish_reason(), FullPacketError, FullPacketRun, FullPacketRunner, _provider_input_tokens(), _usage(), build_prompt() (+36 more)

### Community 39 - "test_ollama_adapter_sends_bounded_schema_and_adaptive_budget"
Cohesion: 0.33
Nodes (5): 1. Public page embeds separate demo origins, 2. Public state representation, 3. Explicit staged API, Limitations, Targeted inspection findings

### Community 40 - "off_by_one/tests/test_regression.py"
Cohesion: 0.33
Nodes (5): AI engineering design, Investigation, Orchestration alternatives, Repair and verification, Repository intelligence

### Community 41 - "test_evidence_facts.py"
Cohesion: 0.06
Nodes (40): AtomicClaim, check_atomic_claim(), _division_denominator(), extract_facts(), add(), provenance(), ProvenanceEntry, Claim (+32 more)

### Community 42 - "test_agent_retrieval.py"
Cohesion: 0.07
Nodes (36): Dispatcher, RetrievalError, finish(), calculate(), relay(), run(), choose(), setup() (+28 more)

### Community 45 - "real_cases.py"
Cohesion: 0.07
Nodes (37): BDB5Error, BlockedCaseError, ManifestValidationError, Readiness, _artifacts(), _bounded_excerpt(), CiCaseConfig, CiFailure (+29 more)

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

### Community 139 - "uuid"
Cohesion: 0.12
Nodes (12): Event, Frame, 6. Unsupported claims and invalid evidence references, calculate_average(), main(), make_incident(), main(), run() (+4 more)

### Community 141 - "Milestone 3D — repository intelligence and paired evaluation"
Cohesion: 0.25
Nodes (6): Milestone 3D paired experiment preregistration, Cost and limitations, Milestone 3D — repository intelligence and paired evaluation, Pre-registered paired protocol, Primary outcomes, Testing and next milestone

### Community 142 - "retrieve"
Cohesion: 0.16
Nodes (18): _calls(), _LimitedNotes, retrieve(), frame(), repository(), commit(), test_class_method_caller_identifies_owning_class(), test_context_limit_is_explicit() (+10 more)

### Community 143 - "external_repair.py"
Cohesion: 0.05
Nodes (51): _apply_patch(), build_evaluator_workspace(), build_p1_payload(), build_workspaces(), changed_files_from_patch(), check_patch_scope(), _copy_worktree(), ExternalRepairError (+43 more)

### Community 147 - "field_validator"
Cohesion: 0.07
Nodes (5): CaseManifest, GroundTruth, _relative_path(), _safe_id(), _unique()

### Community 148 - "test_capture.py"
Cohesion: 0.10
Nodes (20): _api_url(), build_event(), _head_commit(), install_blackbox(), capture_exception(), _relative_frames(), _repo_path(), send_event() (+12 more)

### Community 149 - "test_m4b3_ledger.py"
Cohesion: 0.07
Nodes (43): initialize_experiment(), main(), open_fake_session(), _open_fake_session_for_tests(), _approval_manifest(), _build_run_manifest(), _open_fake_session(), _ReceiverHandler (+35 more)

### Community 150 - "validation.py"
Cohesion: 0.14
Nodes (23): evaluate_case(), PacketValidationError, ValidationIssue, ValidationReport, ValidationSeverity, issue(), _scan_public_payload(), _strings() (+15 more)

### Community 151 - "json"
Cohesion: 0.10
Nodes (20): investigate_with_retrieval(), _investigate_with_retrieval(), main(), _fingerprint(), Provider, content_pinned(), fixture_path(), get_fixture() (+12 more)

### Community 152 - "Milestone 4A — competitor architectures"
Cohesion: 0.33
Nodes (6): Milestone 4A — competitor architectures, OpenHands repository boundary, OpenHands / Software Agent SDK, Sentry Seer / Autofix, SWE-agent, Synthesis

### Community 153 - "Milestone 2.8 handoff completion"
Cohesion: 0.29
Nodes (6): 3. Files modified or added, 5. Actual live model results, 6. Before and after, 7. Unresolved issues, 8. Final status, Milestone 2.8 handoff completion

### Community 154 - "test_real_review.py"
Cohesion: 0.46
Nodes (7): _fake_source(), _r1_payload(), _r2_payload(), test_review_accepts_r1_and_r2_boundaries(), test_review_cli_writes_machine_readable_failure(), test_review_rejects_approval_and_application_source_leak_in_r2(), test_review_rejects_top_level_manifest_and_host_path()

### Community 155 - "Milestone 3E — semantic reasoning and safe abstention"
Cohesion: 0.29
Nodes (5): Milestone 3E evaluation preregistration, Limits and next work, Milestone 3E — semantic reasoning and safe abstention, Paired experiment, Previously observed 3D cases

### Community 157 - "test_synthetic_scoring.py"
Cohesion: 0.20
Nodes (18): scenario(), score(), test_p1_incomplete_f2p_unexecuted_pass_and_regression_failure(), test_p1_invalid_scope_and_test_modification_are_rejected(), test_p1_patch_test_and_regression_dimensions(), test_r1_missing_reproduction_and_citation(), test_r1_patch_free_source_scoring_dimensions(), test_r1_unexecuted_pass_is_an_execution_overclaim() (+10 more)

### Community 158 - "response.py"
Cohesion: 0.11
Nodes (5): BadHeaderError, Http404, HttpResponsePermanentRedirect, HttpResponseRedirect, HttpResponseRedirectBase

### Community 159 - "StreamingHttpResponse"
Cohesion: 0.14
Nodes (3): index(), FileResponse, StreamingHttpResponse

### Community 160 - "bdb5/__init__.py"
Cohesion: 0.10
Nodes (18): _keys(), PacketReview, _registry_entry(), review_file(), review_payload(), _strings(), accept_prepared_result(), _case_objects() (+10 more)

### Community 161 - "HttpResponse"
Cohesion: 0.14
Nodes (6): HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseGone, HttpResponseNotFound, HttpResponseServerError

### Community 163 - "evaluate_m4b3.py"
Cohesion: 0.11
Nodes (18): evaluation_id(), M4B3TransportPhase, _assert_registered_session(), build_run_manifest(), digest(), _document_hash(), _execute_registered(), _expected_plan_matches() (+10 more)

### Community 166 - "digest"
Cohesion: 0.17
Nodes (10): IssueCaseConfig, IssuePreparationError, prepare_issue_case(), PreparedIssueCase, _sha(), _source_excerpt(), EvidencePacket, canonical_json() (+2 more)

### Community 169 - "BLACKBOX â€” local evidence and AI investigation"
Cohesion: 0.29
Nodes (7): AI investigation (opt-in), BLACKBOX â€” local evidence and AI investigation, Limits, One-command demo, Restricted Proof-of-Fix (Milestone 3A), Run the service and tests, Setup

### Community 184 - "test_agent_deadline.py"
Cohesion: 0.22
Nodes (6): _ExtendedLimits, Job, run_contained(), Boundary and security checks, test_job_terminates_blocked_git_subprocess(), test_user_cancellation_terminates_worker()

## Knowledge Gaps
- **109 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `evidence_hash()` connect `investigator.py` to `BLACKBOX â€” local evidence and AI investigation`, `Milestone 2.9.1 — structured-output reliability fix and revalidation`, `time`, `json`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `LedgerBlocked` (e.g. with `M4B3OllamaDispatcher` and `_open_fake_session()`) actually correct?**
  _`LedgerBlocked` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `m4b3_ledger.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08345428156748912 - nodes in this community are weakly interconnected._
- **Why does `investigate()` connect `investigator.py` to `test_repair.py`, `pathlib`, `test_evidence_facts.py`, `AI engineering design`, `test_engine.py`, `Store`, `uuid`, `test_agent_retrieval.py`, `time`, `json`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `Ledger` (e.g. with `_open_fake_session()` and `RunSession`) actually correct?**
  _`Ledger` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Should `LedgerBlocked` be split into smaller, more focused modules?**
  _Cohesion score 0.1276595744680851 - nodes in this community are weakly interconnected._
- **Why does `ProviderError` connect `test_engine.py` to `test_m4b3_ledger.py`, `investigator.py`, `M4B3OllamaDispatcher`, `cloud.py`, `test_evidence_facts.py`, `AI engineering design`, `Store`, `pipeline.py`, `external_repair.py`, `time`, `test_m4b3_ledger.py`, `json`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._