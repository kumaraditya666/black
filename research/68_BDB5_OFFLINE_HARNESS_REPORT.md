# BDB-5 Offline Harness Report

**Status:** `BDB5_OFFLINE_HARNESS_COMPLETE — SYNTHETIC_TESTS_PASSED — NO_INFERENCE`

This report describes an offline evaluation harness, not a benchmark execution. No model was called, no dataset was downloaded, no Docker container ran, no repair fixture was executed, and no RCAEval `root_cause.txt` was read. The synthetic suite verifies harness behavior and scorer wiring only. The strict-pass count below is a fixture count, not a measure of BLACKBOX diagnostic accuracy.

## 1. Architecture

The package is isolated under `blackbox/bdb5/` and does not import the M4B.3 experiment ledger, provider clients, investigator, source resolver, or repair execution modules. It reuses only the project's existing Pydantic v2 dependency and the Python standard library.

The layers are:

1. **Specification and case state** (`spec.py`): fixed case IDs, task-visible F1-F5 taxonomy, readiness facts, and T1/P1 blockers.
2. **Data models** (`models.py`): strict manifests, model-visible packets, evaluator-only truth, result claims, recorded test evidence, scores, and suite results.
3. **Validation** (`validation.py`): packet/label separation, source-revision and artifact checks, citation registration, and result overclaim checks.
4. **Scoring** (`scoring.py`): independent dimensions, N/A semantics, strict required-dimension conjunction, and deterministic per-case hashes.
5. **Engine** (`engine.py`): refuses blocked/non-synthetic cases, raises on hard leakage, and produces suite summaries without averaging dimensions.
6. **Synthetic fixtures and self-test** (`synthetic.py`): invented T1/R1/R2/R3/P1 scenarios and deterministic repeat checks.
7. **CLI** (`cli.py`, `scripts/bdb5_dry_run.py`): offline `SYNTHETIC_DRY_RUN` entry points with JSON output outside the repository by default.

Preparation is separate from evaluation. A case can have a manifest and a scorer and still be refused: `evaluate_case` requires `synthetic=True`, `readiness=APPROVED_FOR_EVALUATION`, and `SYNTHETIC_DRY_RUN`.

## 2. Files Created

| File | Purpose | Lines |
|---|---|---:|
| `blackbox/bdb5/__init__.py` | Public package exports | 43 |
| `blackbox/bdb5/errors.py` | Harness exception types | 18 |
| `blackbox/bdb5/models.py` | Pydantic v2 models and invariants | 634 |
| `blackbox/bdb5/spec.py` | Static readonly specification | 144 |
| `blackbox/bdb5/validation.py` | Packet/result validation and leakage checks | 178 |
| `blackbox/bdb5/scoring.py` | Dimension scorers and canonical hashes | 451 |
| `blackbox/bdb5/engine.py` | Case/suite orchestration and refusal gates | 93 |
| `blackbox/bdb5/synthetic.py` | Invented cases and self-test | 523 |
| `blackbox/bdb5/cli.py` | Offline JSON CLI | 65 |
| `scripts/bdb5_dry_run.py` | Repository-root CLI wrapper | 16 |
| `tests/test_bdb5/test_synthetic_scoring.py` | Scorer and edge-case tests | 188 |
| `tests/test_bdb5/test_validation_and_engine.py` | Leakage, blocked-case, determinism tests | 104 |
| `tests/test_bdb5/test_cli.py` | CLI output tests | 34 |
| `research/68_BDB5_OFFLINE_HARNESS_REPORT.md` | This report | — |

No existing tracked source, test, repair fixture, or research document was edited.

## 3. Data Models

### Case manifest

`CaseManifest` carries the case ID, dataset name and revision, repository, pinned source revision, category, required evidence types, allowed files and scope, required scoring dimensions, readiness, adapter requirements, artifact hashes, synthetic flag, and evaluation schema version.

Readiness values are `SELECTED`, `PREPARATION_BLOCKED`, `PREPARED`, `READY_FOR_REVIEW`, and `APPROVED_FOR_EVALUATION`. Model validation requires an approved manifest to have artifact hashes. No method transitions readiness; approval is only an explicit field value. The harness itself rejects every non-synthetic manifest, so approval of a real case would still not make it runnable here.

### Model-visible evidence packet

`EvidencePacket` contains only a neutral case ID, task instructions, approved evidence items, evidence IDs, source-revision references, an optional unranked candidate inventory, and artifact hashes. It has no ground-truth field. `model_visible_payload()` serializes only its public fields. The packet schema forbids unknown fields, so adding a hidden label key is rejected at construction.

### Evaluator-only ground truth

`GroundTruth` supports expected service, fault class, source file/function/line, expected mechanism terms, causal level, L1/L2 statuses, abstention state and scope, harness explanation terms, reproduction/regression requirements, and patch expectations. `model_visible()` deliberately raises. This is Python-level separation, not a security boundary against arbitrary same-process code. Live evaluation would need a separate process/OS boundary between the evaluator and any untrusted model-generated code.

### Investigation result

`InvestigationResult` contains structured claims, claim categories, evidence citations, ranked services, fault prediction, source predictions, mechanism, causal statuses, abstention, patch record, claimed source revision, and recorded test executions.

A test execution has a role (`FAIL_TO_PASS`, `PASS_TO_PASS`, `REPRODUCTION_BEFORE`, `REPRODUCTION_AFTER`, `REGRESSION`), an outcome, and an optional execution artifact SHA-256. A `PASS` without an artifact is counted as an execution overclaim and never satisfies a test-pass dimension. Claims that assert execution without any recorded execution artifact are also overclaims.

`CaseScore` holds a dimension vector, per-dimension explanations, required dimensions, failures, citation audit, validation issues, and a canonical result hash. `SuiteResult` holds the ordered case score list, a count-based dimension summary, the strict-pass count, and a canonical suite hash. Both use `result_class = "SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT"`.

## 4. Per-Case Scoring Behavior

The F1-F5 taxonomy is a candidate class set, not a target mapping:

- F1: incorrect parameter values
- F2: missing parameters
- F3: missing function call
- F4: incorrect return values
- F5: missing exception handlers

### BDB5-T1 (RCAEval telemetry)

Separate dimensions cover service top-1, service top-3, fault-class accuracy, citation validity/coverage, L1 causal status, L2 causal status, L2 abstention, false abstention, and unsupported claims.

A correct service and fault at L1 does not count as a source-level cause. The correct synthetic result has L1 supported and L2 not established with a source-scope abstention; both dimensions are evaluated independently. A source-level claim fails the L2 abstention dimension even if the service ranking is correct. The candidate inventory may contain the correct service; a bare candidate name is not leakage.

### BDB5-R1 (BugSwarm CI/source)

Dimensions cover file, function, and line exactness; mechanism; causal status; citation validity; reproduction-before evidence; and unsupported-claim rate.

Exact source localization is separate from causal support. Reproduction requires a recorded `REPRODUCTION_BEFORE` failure and a matched failure signature. A claimed reproduction pass without an artifact is an execution overclaim.

### BDB5-R2 (negative control)

Dimensions separate `C_app` (`app_source_claim`), `C_harness` (`harness_claim`), `K_app` (`app_causal_status`), `A_app` (`app_abstention`), and `H` (`harness_identification`).

A missing-fixture explanation is a valid harness claim. It must not be converted into an application-source cause. A source-blame claim sets `app_source_claim=1`, makes `app_causal_status=0`, fails `app_abstention`, and fails the strict case. The synthetic fixture uses invented names rather than a real dataset target.

### BDB5-R3 (Django issue/source)

Dimensions cover file and method localization, mechanism, causal status, citation validity, and unsupported claims. A passing hidden test is not treated as proof of historical causation; causal status is scored from the submitted evidence and claim status, not from test success alone.

### BDB5-P1 (SymPy repair)

Dimensions cover patch applicability, patch scope, test-file modification prohibition, FAIL_TO_PASS, PASS_TO_PASS, reproduction before/after, and regression safety.

The scorer consumes recorded synthetic patch and test evidence only. It never calls the repair pipeline or eligibility gate. A changed path outside `allowed_files`, a changed test path, `tests_modified=True`, a missing recorded test pass, or a reproduction/regression artifact gap fails the corresponding dimension. The external-repository repair adapter does not exist, so P1 remains blocked in real evaluation.

## 5. Dimension Rules

The implementation has no single aggregate accuracy score. `CaseScore.dimensions` contains independent values and `SuiteResult.dimension_summary` contains counts of `PASS`, `FAIL`, `N/A`, and observed values; it never averages failures away.

Key rules:

1. **Zero citations:** citation validity is `0.0`; fabricated-citation rate is `None` (N/A), not zero.
2. **Zero material claims:** unsupported-claim rate is `None` (N/A).
3. **N/A required dimension:** strict pass is false. A missing measurement is not a perfect score.
4. **Citations:** validity is valid citations divided by all cited IDs; coverage is the fraction of required evidence types represented by valid citations; fabricated rate is invalid citations divided by all citations, or N/A when none were made.
5. **Unsupported claims:** a material claim is unsupported if it has no citations, any unknown citation, or an execution assertion without a recorded execution artifact.
6. **Execution overclaims:** unrecorded test passes and unrecorded execution assertions are counted separately from ordinary claim support.
7. **Strict pass:** conjunction of the manifest's required rules plus the absence of hard validation errors. Warning-only unknown citations remain visible but are also reflected in unsupported claims.
8. **Traceability:** every dimension has an explanation string, and every validation issue has a code, severity, and detail.

## 6. Evidence and Label Separation

`EvidencePacket.model_visible_payload()` excludes ground truth and all evaluator-only fields. `GroundTruth.model_visible()` raises instead of returning a redacted dictionary. The validator scans the public payload recursively.

Checks include:

- forbidden hidden-label keys (`root_cause`, `gold_patch`, `fix_commit`, `expected_answer`, scorer notes, target mappings, and related keys);
- gold-patch/diff markers;
- private or staging paths, including drive-letter paths, `/tmp`, `/home`, `/Users`, label-vault names, parent traversal, and UNC-style paths;
- evaluator-only literals declared by the truth object;
- target-marker coupling with the hidden service or fault class;
- packet/evidence source-revision mismatches;
- unregistered or altered artifact hashes;
- missing required evidence types;
- duplicate evidence IDs (schema validation);
- result case mismatch and wrong claimed source revision;
- unknown citations (warning, then unsupported-claim scoring);
- claimed test passes without execution artifacts.

A bare target name in an ordinary unranked candidate inventory is allowed. Leakage requires a target marker coupled to the name, such as an explicit root-cause mapping. This false-positive prevention is tested.

## 7. Synthetic Attack Tests

The suite has 29 invented scenarios: five positive cases (one per scorer) and 24 expected-failure cases. The positive fixtures pass their strict required dimensions; failure fixtures exercise the intended refusal or dimension failure.

Coverage includes:

- T1 correct L1 plus L2 abstention;
- T1 wrong fault, source overclaim, fabricated citation, missing citation, and zero material claims;
- R1 correct localization, wrong file, wrong source revision, fabricated citation, missing citation, wrong causal status, missing reproduction, and unexecuted pass;
- R2 correct harness explanation with application-source abstention, false source blame, missing abstention, and missing reproduction;
- R3 correct, wrong file, wrong mechanism, and fabricated citation;
- P1 correct, invalid patch scope, test-file modification, incomplete FAIL_TO_PASS, unexecuted pass, regression failure, and unattempted patch;
- candidate name matching the hidden synthetic service without failing packet validation;
- target-marker leakage, gold-patch leakage, private-path leakage, hidden-label-field schema rejection, duplicate evidence IDs, altered artifact hash, wrong packet revision, unknown citation visibility, blocked readiness, and non-synthetic refusal;
- deterministic repeated hashes and synthetic output classification.

All names, evidence, services, patches, and fixture paths in these cases are invented for this harness.

## 8. Test Results

Executed from the repository root with bytecode caching disabled and pytest caching disabled:

```text
python -m pytest tests/test_bdb5 -q -p no:cacheprovider
28 passed
```

CLI checks:

```text
python scripts/bdb5_dry_run.py --validate-spec
  spec status: PASS

python scripts/bdb5_dry_run.py --self-test
  self-test status: PASS
  case count: 29
  strict-pass count: 5
  deterministic: true
  suite hash: 1815cedf6619d3632e535cd36e1462d49776935c8b3873c194a33d728981e050

python scripts/bdb5_dry_run.py --synthetic-suite
  case count: 29
  strict-pass count: 5
  result class: SYNTHETIC_DRY_RUN_NOT_BENCHMARK_RESULT
  suite hash: 1815cedf6619d3632e535cd36e1462d49776935c8b3873c194a33d728981e050

python scripts/bdb5_dry_run.py --synthetic-case BDB5-R2
  case count: 4
```

A second independent `--synthetic-suite` invocation produced the same suite hash. `PYTHONPYCACHEPREFIX` was set outside the repository and `compileall` completed with exit status 0 for the package, CLI wrapper, and tests. A scan of all new Python files found no CRLF, trailing whitespace, or tab characters. Generated JSON was written under the system temporary directory, not the repository.

The full application test suite was not run. It was not required for this isolated addition and would mix pre-existing working-tree state with the new harness. No check was skipped to make a failing check pass.

## 9. CLI Usage

```text
python scripts/bdb5_dry_run.py --self-test
python scripts/bdb5_dry_run.py --validate-spec
python scripts/bdb5_dry_run.py --synthetic-case BDB5-R2
python scripts/bdb5_dry_run.py --synthetic-suite
```

All modes default to `SYNTHETIC_DRY_RUN`. Each writes canonical JSON to a `bdb5_offline` directory under the operating system temporary directory and prints the same JSON. `--output PATH` selects another path. There is no live-provider import and no network operation in the CLI.

## 10. What Remains Unimplemented

- No real T1, R1, R2, R3, or P1 manifest is created or approved.
- No RCAEval or BugSwarm data adapter or downloader exists.
- No live model inference, prompt runner, provider client, or network path exists.
- No Docker, worktree, container, or external-repository repair execution exists.
- No real patch application or eligibility-gate invocation exists.
- No OS-level sandbox separates evaluator truth from model-generated code. Python module separation is only a code-organization boundary and is not safe against arbitrary malicious in-process code.
- No real hidden-test execution or benchmark accuracy measurement has occurred.

## 11. Why T1 Remains Blocked

`REAL_CASE_READINESS[BDB5-T1]` is `PREPARATION_BLOCKED`. The preflight gates remain unresolved:

- `N_max` is not a frozen numeric constant;
- candidate service inventory completeness is not established;
- the physical inference/staging/label-vault access boundary is not enforced;
- the telemetry adapter is not implemented;
- no frozen approved T1 manifest or final evidence excerpt exists.

Creating a scorer for T1 does not authorize a real T1 run. The harness has no real T1 manifest and would reject one even if marked approved because it is not synthetic.

## 12. Why P1 Remains Blocked

`REAL_CASE_READINESS[BDB5-P1]` is `PREPARATION_BLOCKED`. The external-repository repair adapter does not exist, isolated external repository/image execution is unavailable, and the trusted-fixture eligibility gate must remain unchanged. P1 scoring uses recorded synthetic patch/test evidence only. It does not import, call, or bypass `blackbox/repair/eligibility.py` or the repair pipeline.

## 13. Why Live Inference Remains Disabled

`EvaluationMode` contains only `SYNTHETIC_DRY_RUN`. The engine refuses any other mode before scoring. `LIVE_INFERENCE_ENABLED` is `False`. The package and CLI have no provider imports, model client, API key handling, network call, Ollama invocation, Gemini invocation, or Docker path. The default CLI mode is explicitly synthetic.

## 14. Exact Git Delta

The pre-edit status was recorded at `/tmp/bdb5_harness_status_before.txt` (also available as `$TEMP/bdb5_harness_status_before.txt`):

- before: 460 entries — 19 tracked modifications (`M`) and 441 untracked entries (`??`);
- after: 553 entries — 19 tracked modifications and 534 untracked entries.

The 19 tracked `M` entries are pre-existing and were not edited by this task. `git diff --stat` still reports those same 19 files.

`comm` against the sorted before/after status shows 116 additions and 23 removals in raw status lines. Fourteen additions are the task files listed in Section 2. The other 102 additions are files inside pre-existing untracked `fixtures/repair/` directories; the 23 removals are the old directory-placeholder lines that `git status -uall` expanded. Those fixture files were already present in the working tree at baseline and were not created or modified by this task. The net task delta is therefore 14 new files, no modified existing files, and no deletions.

No `git add`, commit, push, reset, clean, or stash command was run. No `__pycache__`, `.pytest_cache`, or `.pyc` entries remain in the repository status.

## 15. Remaining Risks and Limitations

1. **Synthetic-only evidence:** the suite validates the harness, not any real benchmark case.
2. **No security boundary:** same-process Python cannot contain arbitrary malicious model code. Future live evaluation requires process/OS isolation, capability restriction, and a separate label vault.
3. **No real adapters:** T1 telemetry, BugSwarm artifacts, Django issue/source packages, and SymPy repair environments remain unimplemented.
4. **No real patch execution:** P1 dimensions are exercised against recorded synthetic artifacts only.
5. **Strict rule calibration:** thresholds such as citation validity `>= 0.9` and all-or-nothing exactness are implementation choices for review, not empirically validated benchmark policy.
6. **R2 naming:** the synthetic missing-fixture case uses invented paths. It tests the no-blame behavior, not the real `types_dict.nml` incident.
7. **No aggregate conclusion:** 5 strict passes in a 29-case synthetic suite must never be reported as model accuracy, benchmark success, or evidence that BLACKBOX diagnoses real incidents.
