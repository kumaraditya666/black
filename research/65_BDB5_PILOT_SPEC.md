# BLACKBOX BDB-5 Pilot Specification

**Document:** 65  
**Status:** `BDB5_SPEC_PARTIAL — T1_PREFLIGHT_UNRESOLVED — NOT_EXECUTED — LIVE_INFERENCE_DISABLED`  
**Design date:** 2026-11-07  
**Correction date:** 2026-11-08  
**Final review date:** 2026-11-08  
**Implementation-readiness date:** 2026-11-08  
**Repository:** `C:\Users\Adi\Documents\ChatGPT\black`  
**Scope:** research and design only. No source code, tests, fixtures, labels, preregistration, Documents 50/56/57/60/61/63, benchmark results, or M4B.3 ledger were modified. No dataset was downloaded in bulk, no Docker image was pulled, no model was called, and no benchmark was run.

## Evidence labels

- **[Verified]** checked against an official repository, dataset API, commit, build log, Docker registry metadata, or the local source on 2026-11-07.
- **[Unresolved]** the primary source does not establish it, the sources conflict, or verification would require pulling/running the artifact.
- **[Recommendation]** an analyst judgment about BDB-5, not a claim about a dataset.
- **[Assessment]** an interpretation of verified evidence, with its limits stated.

---

## 1. Executive decision

BDB-5 selects five cases:

| Pilot ID | Source and exact case | Primary evidence | Ground-truth level | BLACKBOX compatibility |
|---|---|---|---|---|
| **BDB5-T1** | RCAEval RE3, `re3ss_carts_f1_1` | 80 metrics, 1,441 timesteps, 84,665 log rows, no traces, `root_cause.txt` | L1 service/fault only | **C** — telemetry ingestion not implemented |
| **BDB5-R1** | BugSwarm, `bwhmather-verktyg-109227527` | Real CI log, 5/247 failing tests, source at failed commit | L2/L3 source mechanism | **B** — CI-log-to-Event adapter |
| **BDB5-R2** | BugSwarm, `marshallward-f90nml-83523531` | Real CI log, 1/38 failing tests, fix adds only a test fixture | L0 / negative control | **B** — CI-log-to-Event adapter |
| **BDB5-R3** | SWE-bench Verified, `django__django-11133` | Issue, base commit, one hidden FAIL_TO_PASS test, 64 PASS_TO_PASS | L2/L3 source mechanism | **B** — issue-text investigation adapter |
| **BDB5-P1** | SWE-bench Verified, `sympy__sympy-20590` | Issue, base commit, one hidden FAIL_TO_PASS test, 21 PASS_TO_PASS | Patch correctness, no causal L4 | **C** — external-repository repair blocked |

### 1.1 Why the allocation changed from 2 telemetry / 2 repository / 1 repair

The requested default was two telemetry, two repository, and one repair case. I recommend **one telemetry, three repository, and one repair** for the first pilot.

The reason is not that telemetry is unimportant. It is the opposite: telemetry is the central BLACKBOX claim, and the current implementation **does not ingest metrics, logs, or traces at all**. The investigator accepts a recorded exception event with a 40-character commit and stack frames, resolves source at that commit, and asks a model for a diagnosis. A second RCAEval case would exercise the same missing telemetry adapter again, not a second implemented capability.

The third repository slot is used for a **negative control** where the CI failure is fixed by adding a missing test fixture, not by changing application source. That case directly tests the failure mode BLACKBOX must avoid: inventing a source-level cause because a test failed. It also exercises correct abstention and unsupported-claim scoring, which a second adapter-only telemetry case would not.

A second telemetry case is retained as a **reserve** for BDB-6: RCAEval `re3tt_ts-auth-service_f3_1`. It has logs, metrics, and traces, but no `root_cause.txt`; it cannot support a line-level label either.

---

## 2. Selection and verification method

Cases had to satisfy all of the following:

1. An exact dataset case ID or image tag exists.
2. An exact failed revision, base commit, or dataset revision is available.
3. The failure evidence is accessible without downloading the full benchmark where possible.
4. The label is not merely a passing patch or a service name presented as a line-level cause.
5. The case has a realistic failure record, not only a synthetic fixture.
6. The license is known or the case is explicitly marked blocked.
7. The case can be mapped to an implemented capability, a small adapter, or a clearly identified missing capability.
8. The case is not a duplicate of another selected case.

The following were checked directly:

- RCAEval case index (735 rows) through the Hugging Face datasets API; the case directory and `root_cause.txt` for `re3ss_carts_f1_1`.
- BugSwarm artifact, diff, build log, and Docker Hub metadata for both selected artifacts.
- SWE-bench Verified rows for both selected instances, including base commits, tests, patches, and test patches.
- GitHub repository metadata, commits, pull requests, and license files for the relevant upstream projects.
- The local BLACKBOX event schema, investigator, source resolver, repository retrieval, repair eligibility gate, and repair pipeline.

No model was used to establish any label. No raw telemetry was sent externally.

### 2.1 Rejected or deferred candidates

| Candidate | Why not selected |
|---|---|
| RCAEval `re3tt_ts-auth-service_f3_1` | Reserve for BDB-6. Logs/metrics/traces exist (43,517 logs, 91,004 traces), but no `root_cause.txt`; only service/fault labels; telemetry adapter required. |
| SWE-bench Verified `django__django-11099` | The issue text states the exact regex fix (`\A...\Z`), so it is a poor diagnosis case and a leaky repair case. |
| BugSwarm `wavesoft-CCLib-186770554` | The fix is test-only, which is useful, but the repository is GPL-3.0 and duplicates the f90nml negative-control role. Not selected to avoid a copyleft redistribution complication in a tiny pilot. |
| BugsInPy cases | The dataset has no license file; commercial/redistribution status is unresolved. Hard blocker. |
| Defects4J cases | Useful controlled Java repair, but no runtime telemetry and no need for a second repair track in BDB-5. Defer to cross-language BDB-10. |
| LogHub datasets | No causal labels, no source, no reproduction. Not a diagnostic ground truth. |
| AIOpsLab | Live Kubernetes testbed, not a fixed case corpus; too heavy for BDB-5. |

---

## 3. Case dossiers

### 3.1 BDB5-T1 — RCAEval Sock Shop carts F1

**Exact dataset and case.** RCAEval, suite `RE3`, dataset `RE3-SS`, case `re3ss_carts_f1_1`, repetition 1. The frozen dataset revision is Hugging Face commit `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e` (accessed 2026-11-07).

**Original system.** Sock Shop. RCAEval labels the system `ss` and the root-cause service `carts`. The upstream Sock Shop deployment repository is `microservices-demo/microservices-demo` (Apache-2.0, archived); the carts service repository is `microservices-demo/carts` (Apache-2.0, archived). RCAEval does **not** include a per-case application source snapshot or a source commit for this case. Do not claim that the selected upstream repository is byte-identical to the RCAEval deployment.

**Incident reference.** `https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re3ss_carts_f1_1`. There is no GitHub issue for the injected fault.

**Pinned evidence.** The case directory contains:

| File | Size | Content |
|---|---:|---|
| `logs.parquet` | 1,003,956 bytes | 84,665 log rows |
| `metrics.parquet` | 187,614 bytes | 80 metrics, 1,441 timesteps |
| `inject_time.txt` | 10 bytes | `1732243203` |
| `root_cause.txt` | 288 bytes | One log line, timestamped 2024-11-22 02:51:59.404 |

The case metadata reports a 24-minute window: `time_start=1732242483`, `time_end=1732243923`, with 720 normal and 721 faulty timesteps. There are **no traces** for this Sock Shop case.

**What BLACKBOX receives.** A telemetry package containing the complete 24-minute metrics table; the complete service inventory (all candidate service names, including the target, with no target marker); a deterministic log excerpt selected solely from the pinned window boundaries and a pre-registered row-selection rule; the recorded window boundaries; and a neutral task requiring a service prediction and a fault-class prediction. It does **not** receive `root_cause_service`, `fault`, `fault_description`, `root_cause.txt`, the dataset directory name, or any field asserting which service failed. The event description must not name a path, service, or cause; it may only say that an incident occurred in the window. A log line that naturally falls inside the independently selected window is ordinary evidence, even if it mentions a service or an error.

**Task-visible fault taxonomy.** The prompt supplies all five neutral candidates, using the definitions already recorded in Document 63:

| Code | Definition |
|---|---|
| **F1** | incorrect parameter values |
| **F2** | missing parameters |
| **F3** | missing function call |
| **F4** | incorrect return values |
| **F5** | missing exception handlers |

The model must predict exactly one service and one fault code. The taxonomy is visible; the correct target mapping (`carts` → `f1`) is not. No code is marked correct, no service is associated with a code in the model-visible package, and no example reveals the target. Document 65 and every other document containing ground truth or target mappings stay outside the model-visible environment.

**Evidence-window independence.** The excerpt is selected by a deterministic rule that uses only the pinned timestamps and a fixed row limit:

1. Set `W = [time_start, time_end]` inclusive (`1732242483`–`1732243923`).
2. Include every log row whose timestamp falls in `W`. Sort by timestamp. For equal timestamps, use a **verified** stable row ID if the immutable Parquet schema has one; otherwise use the original zero-based row ordinal from the hash-pinned Parquet file. Do not use message text, a regenerated index, or an unstable sort tie-breaker.
3. Let `N_max` be a pre-registered constant fixed before any label review (recommended: 2,000 rows). If the sorted row count exceeds `N_max`, select evenly spaced rows by index across the full sorted set; otherwise include all rows. The same rule applies to every case and is recorded in the manifest.
4. Do not filter or rank by text, service, error type, or `root_cause.txt`.

**Row-order preflight [Unresolved].** The actual `logs.parquet` schema has not been inspected. The preflight must record the schema, timestamp column and units, presence or absence of a stable row ID, total row count, file hash, and ordinal semantics. No stable ID is claimed until this is checked. If no stable ID exists, the original row ordinal is the only allowed tie-breaker. T1 cannot be frozen before this is verified.

`root_cause.txt` is never consulted to choose the window, the excerpt, or the candidate list. It stays exclusively in the scoring/label vault. If the hidden root-cause line naturally appears in the independent excerpt, it remains available as ordinary evidence; its presence is not a leak, and its absence does not invalidate the case. Scoring may use the hidden line to verify a cited line, but not to select evidence.

**Hidden ground truth.** `root_cause_service = carts`, `fault = f1` (incorrect parameter values), plus the root-cause log line. The line is a Spring `PageNotFound` warning stating that `POST` is not supported. That line is evidence associated with the case; it is **not** a source-line label and does not by itself prove that an incorrect parameter value caused the failure.

**Level-specific labels.** L1 is `IDENTIFIED`: service `carts` and fault `f1`. L2+ is `NOT_ESTABLISHED`: RCAEval supplies no source-file/function/line label. These are separate labels. A correct L1 answer is not a source-level claim, and T1 does not award L2 credit for it.

**Fault-class requirement.** The T1 prompt explicitly requires **both** a service prediction and a fault-class prediction. The fault class is not optional. `F=1` is therefore a mandatory strict-pass condition, consistent with the task instruction.

**Verification.** Two independent checks:

1. **L1 check:** exact match on service `carts` and exact match on fault class `f1`; both predictions are required. Any cited log line must exist in the independently selected window. The hidden root-cause line is not required to be present; if it is present and cited, it must match the hidden line's timestamp/content.
2. **L2+ check:** the answer makes no unsupported source-level causal claim and explicitly leaves the source cause `NOT_ESTABLISHED`. Naming a file, function, line, or source mechanism as the cause is not a T1 L2 hit; it is an unsupported L2 claim. The L1 service/fault hit neither satisfies nor violates this check.

There is no patch and no source-level verification. The service/fault hit and the L2+ abstention are scored separately; neither substitutes for the other.

**Licensing.** RCAEval dataset and code are MIT. Sock Shop and the carts service are Apache-2.0. The log line includes a pod name and an internal hostname; redact internal identifiers before any external model call. The case is suitable for internal evaluation; redistribution of the telemetry should preserve the RCAEval MIT notice and inspect the logs for sensitive content.

**Practical accessibility.** Only these four files are needed: about **1.14 MiB** total. The full RCAEval Parquet release is about 3.44 GB and is not required.

**What it measures.** L1 service identification, mandatory fault-class identification, telemetry citation correctness, and independent L2+ abstention. Identifying `carts` at L1 is expected and does not count as a source-level claim; the answer must still decline to assert an L2/L3 source cause without source/revision evidence. It does **not** measure source-file identification, patch correctness, reproduction, or regression safety.

**Compatibility.** **C.** BLACKBOX has no metrics/logs/traces ingestion path. This case needs a new telemetry case schema, a timestamp-only window selector, a neutral prompt that accepts telemetry evidence and a complete candidate inventory without a target marker, and scoring that keeps L1 identification separate from L2+ abstention. It must not be forced into the existing exception `Event` schema by inventing a stack frame.

---

### 3.2 BDB5-R1 — BugSwarm verktyg 109227527

**Exact dataset and case.** BugSwarm artifact/image tag `bwhmather-verktyg-109227527`. BugSwarm REST metadata accessed 2026-11-07.

**Original repository.** `bwhmather/verktyg`, a Python web framework built on Werkzeug. Upstream license: BSD-3-Clause-style text in `LICENSE` (copyright 2014 Ben Mather); `setup.py` declares `license='BSD'`. GitHub's license detector reports `NOASSERTION` because the text is not the standard template, so record the license text, not only GitHub metadata.

**Pinned revisions.**

- Failed job: `109227527`, trigger SHA `71dc420c22fadbae064c46b426e093bec7b86f32`, commit message "Use stdlib instead of werkzeug.url_decode".
- Passed job: `109231520`, trigger SHA `2c50fdf92f285a98badbdfa2d72ccc27f34d4b11`, commit message "Fix issues with non latin1 query strings".
- Docker image: `bugswarm/images:bwhmather-verktyg-109227527`, amd64 digest `sha256:0c915ddd2f49143477c97a24470a890d3692b57c2562b956075045447816ce86`, Docker Hub `full_size` 1,911,723,658 bytes (about 1.91 GB).

**Available evidence.** The failed Travis job log is 65,746 characters and records five failures/errors out of 247 tests. The failed tests are:

- `test_modified_url_encoding`
- `test_shallow_mode`
- `test_storage_classes`
- `test_base_request`
- `test_form_data_ordering`

The primary failure is `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc1 in position 4: ordinal not in range(128)` in `verktyg/requests.py`, line 356, inside the `args` cached property. The fix diff changes only `verktyg/requests.py` (+5/−2) and wraps the query string with `wsgi_decoding_dance` before `parse_qsl`.

**What BLACKBOX receives.** The failed CI log excerpt, the failure event normalized to `UnicodeDecodeError` with frame `verktyg/requests.py:356` and function `args`, the repository checkout at `71dc...`, and the test command from the CI config: `coverage run --source=verktyg setup.py test`. It does not receive the passed job, the fix commit, the diff, or the fixed checkout.

**Hidden ground truth.** File `verktyg/requests.py`; function `BaseRequest.args`; failure line 356; mechanism: bytes from the WSGI query string are passed to `parse_qsl`, which coerces them with ASCII and fails for a non-Latin-1 query string; the fix decodes the query string with the request's URL charset before parsing. Causal level L2/L3, status `SUPPORTED` (not `ESTABLISHED`, because BDB-5 does not perform a counterfactual L4 experiment). The hidden label includes the five failing test names and the fix diff.

**Verification.** The failing test set must fail at `71dc...` with the recorded signatures; the source line and function must match; the protected fix at `2c50...` must make the failing tests pass and preserve the remaining 247-test run. For BDB-5 diagnosis scoring, no patch is required. If a reviewer later performs a revert/restore experiment, the status may be upgraded to L4; it must not be called L4 in advance.

**Licensing.** BugSwarm infrastructure is BSD-3-Clause; the artifact contains `bwhmather/verktyg` under its BSD-style license and its dependencies under their own licenses. The Docker image is large and includes an old Python 3.5/Travis environment; review dependency licenses before redistribution.

**Practical accessibility.** Public Docker Hub image, about 1.91 GB. No authentication was needed for metadata. The image was **not pulled** in this task. The old environment may fail on current Docker/host combinations; that must be tested before the pilot.

**What it measures.** Repository-scale source resolution, stack-frame/git-revision matching, L2 file/function/line localization, L3 trigger/mechanism reasoning, evidence citation, and resistance to unsupported upstream claims. It does not measure patch generation.

**Compatibility.** **B.** A small CI-log-to-`Event` adapter is required: strip the Travis path prefix, choose the innermost source frame, preserve the exact commit, and keep the log excerpt as untrusted text. Once that Event exists, the current investigator and source resolver can run.

---

### 3.3 BDB5-R2 — BugSwarm f90nml 83523531 (negative control)

**Exact dataset and case.** BugSwarm artifact/image tag `marshallward-f90nml-83523531`. BugSwarm REST metadata accessed 2026-11-07.

**Original repository.** `marshallward/f90nml`, a Python Fortran-namelist parser. Upstream license: Apache-2.0.

**Pinned revisions.**

- Failed job: `83523531`, trigger SHA `d8d88884dea251fc1d9e63b9afcf19b81a785066`, commit message "Namelist dict test; dict pre-sorting; PEP8 cleanup".
- Passed job: `83523553`, trigger SHA `048e4689bd42c0df41554e517a42301718ac8d66`, commit message "Added the dict unit test output file".
- Docker image: `bugswarm/images:marshallward-f90nml-83523531`, amd64 digest `sha256:ff328c82ecf295da3c56148ac409c7a1021720229b2e5c393d4a6eaa2741b730`, Docker Hub `full_size` 1,912,283,833 bytes (about 1.91 GB).

**Available evidence.** The failed Travis log is 30,882 characters and records 1 error out of 38 tests. The failure is:

`ERROR: test_dict_write (__main__.Test)`  
`IOError: [Errno 2] No such file or directory: 'types_dict.nml'`

The traceback goes through `test/test_f90nml.py:211` (`assert_file_equal`) and `test/test_f90nml.py:483` (`test_dict_write`). The passed commit changes **only** `test/types_dict.nml` (+7 lines); it does not change application source.

**What BLACKBOX receives.** The failed CI log excerpt, an `IOError` event with the test frame, the repository at `d8d8...`, and the test command from the CI config: `cd test && python test_f90nml.py`. It does not receive the passed job, the fix commit, or the added fixture.

**Hidden ground truth.** The immediate failure is a missing test fixture (`types_dict.nml`), not an established application-source defect. The correct outcome has two parts: abstain from an unsupported application-source cause, and optionally identify the missing fixture and its test location. Causal level L0/negative for application source: no source component is established. A model that names `f90nml/namelist.py` or `f90nml/parser.py` as the cause without evidence is making an unsupported application-source claim, even though the failed commit also changed those files. Naming `types_dict.nml` or `test/test_f90nml.py` is a test-harness/fixture claim, not an application-source claim, and must not be treated as a failure of the application-source abstention criterion.

**Verification.** The failure must reproduce as `IOError`/`FileNotFoundError` for `types_dict.nml`; the protected passed commit must add only the fixture and make the test pass; no source change may be introduced by the evaluator. This is a label/evidence control, not a repair case. The correct missing-fixture explanation is allowed and is scored separately from application-source abstention.

**Licensing.** BugSwarm infrastructure BSD-3-Clause; f90nml Apache-2.0. The image contains a Python 3.2-era environment and third-party dependencies; review before redistribution.

**Practical accessibility.** Public Docker image, about 1.91 GB. Not pulled in this task.

**What it measures.** Correct application-source abstention, resistance to the “test failed, therefore source is broken” shortcut, permitted test-harness/fixture identification, causal calibration, and unsupported-claim detection. It does not measure patch correctness or application-source localization.

**Compatibility.** **B.** Same CI-log-to-`Event` adapter as R1, but the expected application-source behavior is `INSUFFICIENT_EVIDENCE`/`NO_CLAIM`. The prompt must not force blanket silence: the answer may identify the missing fixture and test location. The current investigator can represent the test frame, but its prompt and schema must be tested for a case where the correct answer is “the test data is missing,” not “the application is faulty.”

---

### 3.4 BDB5-R3 — SWE-bench Verified django__django-11133

**Exact dataset and case.** SWE-bench Verified `django__django-11133`. Dataset revision `78f471bf655a3137b2e8a75af1501690ec009ec3` (accessed 2026-11-07).

**Original issue.** Django ticket `#30294` (`https://code.djangoproject.com/ticket/30294`), fixed by PR `https://github.com/django/django/pull/11133` (“Fixed #30294 -- Allowed HttpResponse to accept memoryview objects”). The issue describes writing a `memoryview` from PostgreSQL into `HttpResponse`; the response content becomes a representation string instead of the underlying bytes.

**Pinned revisions.** Base commit `879cc3da6249e920b8d54518a0ae06de835d7373`; environment setup commit `419a78300f7cd27611196e1e464d50fd0385ff27`; version 3.0. Image `swebench/sweb.eval.x86_64.django_1776_django-11133:latest`.

**Available evidence.** Issue text, full Django source at the base commit, and hidden tests. `FAIL_TO_PASS` is exactly `test_memoryview_content (httpwrappers.tests.HttpResponseTests)`. There are 64 `PASS_TO_PASS` tests. The gold patch is 581 characters and changes `django/http/response.py` at `make_bytes`: `isinstance(value, bytes)` becomes `isinstance(value, (bytes, memoryview))`. The test patch is 552 characters and adds the memoryview assertion.

**What BLACKBOX receives.** The issue text, the repository at `879cc...`, and the source retrieval tools. It does not receive the gold patch, test patch, `FAIL_TO_PASS`, `PASS_TO_PASS`, the fix PR body, or the fix commit. The issue text is permitted because it is the original problem report, but the prompt must exclude later comments that state the fix.

**Hidden ground truth.** File `django/http/response.py`; method `HttpResponse.make_bytes`; line 232 at the base commit; mechanism: `memoryview` is neither `bytes` nor `str`, so it falls through to `str(value).encode(...)`, producing a representation string rather than the underlying buffer. Causal level L2/L3, status `SUPPORTED`. The hidden test proves the behavior, but not L4 historical causation.

**Verification.** Apply the hidden test patch and gold patch to a clean base in the SWE-bench environment; run `test_memoryview_content` and the 64 PASS_TO_PASS tests; test files must remain unmodified by the candidate. For BDB-5 diagnosis scoring, the file/function/mechanism and evidence citations are scored; patch execution is optional and should not be confused with diagnosis correctness.

**Licensing.** Django is BSD-3-Clause. SWE-bench code is MIT, but the Hugging Face dataset card/API still exposes **no dataset-level license**; do not assume the data is MIT. The Docker image contains Django and test dependencies under their own licenses. Internal evaluation is reasonable; redistribution requires review.

**Practical accessibility.** Dataset metadata is 6.31 MB; the base commit is public; the evaluation image is large and was not pulled. The case is technically accessible but not lightweight.

**What it measures.** Issue-to-source investigation, file/function localization, mechanism explanation, evidence provenance, and resistance to overclaiming runtime execution from an issue report. It does not measure telemetry diagnosis, patch generation, or regression safety unless run as a separate repair case.

**Compatibility.** **B.** The current investigator accepts an exception event, not an issue statement. An issue-investigation adapter must use the same evidence/provenance rules but a different prompt and schema. It must not fabricate a stack frame to satisfy the existing `Event` validator.

---

### 3.5 BDB5-P1 — SWE-bench Verified sympy__sympy-20590

**Exact dataset and case.** SWE-bench Verified `sympy__sympy-20590`, dataset revision `78f471bf655a3137b2e8a75af1501690ec009ec3`.

**Original issue.** SymPy issue `#20567` (`https://github.com/sympy/sympy/issues/20567`), fixed by PR `#20590` (“fix(core): use `__slots__` for DefaultPrinting and Basic”). The report is that `Symbol('s').__dict__` exists in 1.7 although it did not in 1.6.2; the suspected cause is a parent class that stopped defining `__slots__`.

**Pinned revisions.** Base commit `cffd4e0f86fefd4802349a9f9b19ed70934ea354`; environment setup commit is the same; version 1.7. Image `swebench/sweb.eval.x86_64.sympy_1776_sympy-20590:latest`.

**Available evidence.** Issue text, full SymPy source at the base commit, and hidden tests. `FAIL_TO_PASS` is exactly `test_immutable`; there are 21 `PASS_TO_PASS` tests. The gold patch is 611 characters and adds `__slots__ = ()` to `Printable` in `sympy/core/_print_helpers.py`. The test patch is 460 characters and asserts that `b1` has no `__dict__` and rejects attribute assignment.

**What BLACKBOX receives.** The issue text, the base repository, the allowed file `sympy/core/_print_helpers.py`, the generated patch interface, and the hidden test command. It does not receive the gold patch, test patch, FAIL_TO_PASS/PASS_TO_PASS lists, or fix commit.

**Hidden ground truth.** Correct patch scope is `sympy/core/_print_helpers.py`; the mechanism is that a mixin without `__slots__` reintroduces `__dict__` into `Basic` instances; the patch adds an empty slots tuple. Patch correctness is verified by apply, `test_immutable`, and 21 PASS_TO_PASS tests. Causal status is **not assessed as L4**; a passing patch proves test-verified repair, not historical cause.

**Verification.** Apply the candidate patch to a clean base; reject edits to tests or files outside the allowed scope; run `test_immutable`; run the 21 PASS_TO_PASS tests; repeat at least three times or mark flaky. Compare the candidate patch to the gold patch only for analysis, not as the sole correctness criterion.

**Licensing.** SymPy's `LICENSE` is a BSD-3-Clause-style text (copyright 2006–2020 SymPy Development Team), although GitHub's detector reports `NOASSERTION`. SWE-bench dataset license is undeclared; source and dependencies retain their licenses. Internal evaluation only until legal review.

**Practical accessibility.** Metadata is small; the SWE-bench image and repository are large and were not pulled/run. This is the most expensive case to execute and should be last.

**What it measures.** External patch generation, patch scope discipline, reproduction-before/after, hidden-test success, and regression safety. It does not measure telemetry RCA or independent causal attribution.

**Compatibility.** **C.** The current repair gate is restricted to trusted, content-pinned fixtures with a registered reproduction and regression command; `blackbox/repair/eligibility.py` rejects an arbitrary repository. BDB5-P1 therefore requires a **separate, isolated external-repository repair evaluation adapter** — a new, unresolved implementation task, not an existing capability and not a prompt change. The adapter must keep the existing trusted-fixture gate intact, use a disposable isolated environment, pin the base revision and allowed file scope, keep hidden tests outside the candidate workspace, and define its own safety/approval boundary. Do not weaken, bypass, or relax `blackbox/repair/eligibility.py` for P1. No such adapter exists in this checkout.

---

## 4. What each case measures

Legend: **Y** = scored; **N** = not applicable; **A** = only as an abstention/negative control; **H** = hidden verification only.

| Capability | T1 | R1 | R2 | R3 | P1 |
|---|---|---|---|---|---|
| Faulty service identification | **Y** (L1) | N | N | N | N |
| Fault-class identification | **Y** (L1, mandatory) | N | N | N | N |
| Relevant file/function/line | N (not labelled) | **Y** (L2) | N for application source; test location optional | **Y** (L2) | **Y** (scope) |
| Failure-mechanism explanation | N (not labelled) | **Y** (L3) | **Y** (test-harness/fixture; not app source) | **Y** (L3) | **Y** (patch mechanism) |
| Test-harness/fixture identification | N | N | **Y** (`C_harness`, `H`; optional for strict pass) | N | N |
| Causal attribution | **Y** at L1 (`K_L1`); L2+ only as abstention (`K_L2+`) | **Y** at L2/L3 | **A** (`C_app=0`; app source `NOT_ESTABLISHED`; `C_harness` allowed) | **Y** at L2/L3 | N (repair only) |
| Appropriate abstention | **Y** at L2+ (`A_L2`), independent of `S1`/`F` | N | **Y** (`A_app`; fixture ID allowed) | N | N |
| Patch correctness | N | N | N | N | **Y** |
| Original failure reproduction | N | **Y** | **Y** | H | **Y** |
| Regression safety | N | N | N | H | **Y** |

### 4.1 Causal levels

- **L0:** no component/source cause established.
- **L1:** service/component identified.
- **L2:** file/function/line identified.
- **L3:** trigger/condition identified.
- **L4:** counterfactual confirmation by revert/restore in a controlled reproduction.

BDB-5 does not perform L4. T1 is L1 only. R1 and R3 are L2/L3 and may be labelled `SUPPORTED`, not `ESTABLISHED`. R2 is a negative control: the correct source-level status is `NOT_ESTABLISHED`. P1 is a repair case; its causal status is not scored.

For T1, causal status is two-dimensional rather than a single label: `K_L1 = IDENTIFIED` for service/fault and `K_L2+ = NOT_ESTABLISHED` for source level. A correct L1 identification is not a source-level claim. R2 is scored at L2+ only; there is no L1 component label. Its application-source status is `NOT_ESTABLISHED`, while `C_harness` and `H` are separate and allowed.

---

## 5. Scoring methodology

### 5.1 No aggregate score

There is no single “BDB-5 accuracy.” Each case produces a vector of dimension scores, hard-fail flags, and raw cost. Report counts and per-case tables. A system that finds the service but invents the line is not “80% correct”; it has a service hit and a source-level claim failure. Conversely, a system that correctly identifies `carts` at L1 and declines to name a source file has a service hit and a correct L2+ abstention; the service hit must not be counted as a source claim.

### 5.2 Exact metric definitions

Let `C` be the set of cited evidence IDs, `V` the valid IDs at the correct revision/type, and `R` the required evidence types for that case.

- **Citation validity:** `CV = |V| / |C|`, with `CV = 0` if `C` is empty. A citation to a real but wrong-revision file is invalid.
- **Citation coverage:** `CC = |types(V) ∩ R| / |R|`.
- **Fabricated citations:** `FC = |C \\ V| / |C|` when `C` is non-empty; if `C` is empty, `FC = N/A`, not 0. Also report the raw count. `FC=N/A` is not a perfect score.
- **Service top-1:** `S1 = 1` if the first ranked service equals the label; `S3 = 1` if the label is in the top three.
- **Fault-class accuracy:** `F = 1` if the predicted fault class equals the label; only T1 uses this, and the T1 prompt requires a fault-class prediction.
- **File exactness:** `Df = 1` if the predicted primary file set equals the label file set; otherwise 0. Report extra files separately.
- **Function exactness:** `Ds = 1` if the primary function/method equals the label; otherwise 0.
- **Line exactness:** `Dl = 1` if the primary line equals the label line; for patches, `Dl` is not used because the patch may insert lines.
- **Mechanism score:** `M ∈ {0, 0.5, 1}` using the rubric below.
- **Claim level:** each material causal claim is classified at the highest level it asserts: L1 service/component; L2 file/function/line; L3 trigger/mechanism; L4 counterfactual. A claim that `carts` is the faulty service is an L1 claim, not an L2 claim merely because it is causal.
- **Application-source claim (`C_app`):** 1 if any material claim asserts an application-source defect or cause; otherwise 0.
- **Test-harness/fixture claim (`C_harness`):** 1 if any material claim asserts a test-harness, fixture, environment, or test-data failure; otherwise 0. A missing-fixture claim may be correct even when `C_app=0`.
- **Causal status (`K`):** `K = 1` if the predicted status equals the label status; report the full confusion matrix. For T1, report `K_L1` and `K_L2+` separately:
  - `K_L1 = 1` iff the answer identifies service `carts` and the required fault class `f1` as the supported L1 conclusion; otherwise 0.
  - `K_L2+ = 1` iff the answer's source-level status matches the T1 label, `NOT_ESTABLISHED`; otherwise 0.
  Do not collapse `K_L1` and `K_L2+` into one value. For R1 and R3, `K` is the L2+ status. For R2, `K`/`K_app` is `NOT_ESTABLISHED`; `C_harness` does not change it.
- **Level-specific abstention (`A_ℓ`; `A` is shorthand for the expected source-level abstention):** `A_ℓ = 1` only if the case expects no claim at level ≥ ℓ, the answer explicitly states that the evidence is insufficient for that level and identifies the missing evidence type, and it makes no claim at ≥ ℓ. `A_ℓ = 0` for a vague “not enough information” without the right gap, or for any assertion at ≥ ℓ. For T1, `A_L2` is the required source-level abstention. It is independent of `S1` and `F`: naming `carts` at L1 neither satisfies nor violates `A_L2`; asserting a file, line, or source mechanism as the cause violates it. For R2, `A_app` is the primary abstention; a missing-fixture claim does not violate it. A global “no cause at any level” answer can have `A_L2=1` but still fails T1 because `S1=0` and `F=0`; it is not a T1 pass.
- **Application-source abstention (`A_app`):** for R2, `A_app = 1` only if the answer makes no unsupported `C_app` claim, explicitly says that no application-source cause is established, and identifies the missing test-harness/fixture evidence type. `A_app = 0` for an unsupported application-source claim or a bare “not enough information” without the harness gap. `C_harness=1` and `H=1` are allowed and do not reduce `A_app`.
- **Harness identification (`H`):** for R2, `H=1` if the answer identifies the missing `types_dict.nml` fixture and the relevant test location (`test/test_f90nml.py:211` and/or `:483`); otherwise 0. `H` is reported separately and is not required for the R2 strict pass.
- **False abstention:** `FA = 1` if an answerable level is declined. For T1, declining the L1 service/fault identification is false abstention; declining L2+ is expected and is not false abstention. For R2, declining the permitted harness explanation is not application-source false abstention.
- **Unsupported-claim rate:** `U = unsupported material claims / all material claims`; a material claim is one that asserts execution, input, contract, mechanism, or cause. If there are zero material claims, `U = N/A`, not 0. `U=N/A` does not satisfy a strict `U=0` gate.
- **Execution overclaim count:** number of claims that say code ran or a test passed without recorded execution.
- **Patch applies:** `Pa = 1` if the patch applies cleanly to the pinned base; otherwise 0.
- **Patch scope:** `Ps = 1` if only allowed files change and no test file changes; otherwise 0.
- **FAIL_TO_PASS:** `Pf = passed / total`.
- **PASS_TO_PASS:** `Pg = passed / total`.
- **Reproduction before:** `Rb = 1` if the recorded failure signature occurs at the base revision; otherwise 0.
- **Reproduction after:** `Ra = 1` if the same test passes after the patch; otherwise 0.
- **Regression safety:** `Rs = 1` if all PASS_TO_PASS tests pass without test edits; `Rs = 0` otherwise; mark `FLAKY` if repeated runs disagree.
- **Strict case pass:** `SCP = 1` only if all required dimensions for that case are 1. `SCP` is not an average.

### 5.3 Mechanism rubric

| Score | Criterion |
|---:|---|
| 1 | Names the actual mechanism, the triggering condition, and the source location; every step is supported by cited evidence. |
| 0.5 | Names a plausible mechanism/location but leaves one material link unsupported or overbroad. |
| 0 | Mechanism is incompatible with the cited code, invents execution/input, or asserts a cause without evidence. |

### 5.4 Per-case required dimensions

| Case | Required for strict pass |
|---|---|
| T1 | `S1=1`, `F=1` (mandatory), `CV≥0.9`, `CC=1`, `K_L1=1`, `K_L2+=1`, `A_L2=1`, `U=0` |
| R1 | `Df=1`, `Ds=1`, `Dl=1`, `M=1`, `K=1`, `CV≥0.9`, `Rb=1`, `U=0` |
| R2 | `K_app=NOT_ESTABLISHED`, `A_app=1`, `C_app=0`, `CV≥0.9`, `Rb=1`, `U=0`; `C_harness` and `H` are reported but not required |
| R3 | `Df=1`, `Ds=1`, `M=1`, `K=1`, `CV≥0.9`, `U=0` |
| P1 | `Pa=1`, `Ps=1`, `Pf=1`, `Pg=1`, `Rb=1`, `Ra=1`, `Rs=1`, no test edits |

### 5.5 Reporting

Report a per-case table, dimension totals, strict-pass counts, hard-fail flags, latency, tokens, and storage. Report T1 L1 service/fault identification (`K_L1`) separately from L2+ source status and abstention (`K_L2+`, `A_L2`); never average them into one score. Report R2 application-source abstention (`C_app`, `A_app`) separately from harness identification (`C_harness`, `H`); a correct fixture explanation is neither an application-source success nor an application-source failure. Do not publish a leaderboard from five cases.

---

## 6. Ground truth and leakage controls

### 6.1 Who establishes the expected answer

The **case author** assembles the evidence package, writes the label rationale, and records exact source/commit/test references. An **independent reviewer** who did not author the case reproduces the failure or checks the dataset label, reviews the source/diff, and signs the label. A third reviewer adjudicates disagreements. No model output is used to establish a label. For BDB-5, all five cases should be double-reviewed because the set is small.

Role IDs and review dates must be recorded. The report must not invent reviewer names; they are assigned when the pilot is authorized.

### 6.2 Information hidden from BLACKBOX

- T1: hidden target-label fields (`root_cause_service`, `fault`, `fault_description`, `root_cause.txt`), the case directory name, and any metadata or relational assertion that identifies `carts` as faulty. The service inventory may contain `carts` and every other candidate name; bare candidate names are not hidden-label fields and must not be treated as leaks.
- R1: passed job, fix SHA `2c50...`, fix diff, commit message after the failure, and any fixed checkout.
- R2: passed job, fix SHA `048e...`, the added fixture's content, and the fact that the fix is test-only. The missing filename `types_dict.nml` is visible in the failed CI log and is not hidden.
- R3: gold patch, test patch, FAIL_TO_PASS/PASS_TO_PASS, fix PR comments, and fix commit.
- P1: gold patch, test patch, FAIL_TO_PASS/PASS_TO_PASS, fix PR comments, and fix commit.

The issue text is visible only for R3/P1; it is the original report, not a fix description. Any later comment that names the patch is excluded.

### 6.3 Prompt allowlist

Allowed: neutral case ID, telemetry window selected by the pinned timestamps, independently selected log excerpt, full candidate service inventory with no target marker, issue statement, source excerpts at the pinned revision, approved test command, and tool descriptions. Excluded: labels, target-label fields, any assertion that a particular service failed, gold patches, test patches, added fixture content, fix commits, commit messages after the failure, diff files, failing-test lists that are not visible in the supplied CI log, and filenames containing `gold`, `fixed`, `buggy`, or the answer. For R2, the literal `types_dict.nml` in the CI log is ordinary failure evidence and is allowed.

Case IDs are opaque: `BDB5-T1` … `BDB5-P1`; no path or directory names may reveal the answer.

### 6.4 Duplicate detection

Compute a signature from `repository + base_commit + failure_type + top_frame_path/function + normalized message`. Manually compare selected cases and source repositories. The five selected cases are distinct: Sock Shop, `bwhmather/verktyg`, `marshallward/f90nml`, `django/django`, and `sympy/sympy`. No cross-dataset duplicate was found. If a future case shares a repository and fix commit, keep only one.

### 6.5 Pinned versions

Freeze:

- RCAEval HF commit `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`.
- SWE-bench Verified HF commit `78f471bf655a3137b2e8a75af1501690ec009ec3`.
- BugSwarm artifact tags and image digests listed above.
- Failed/base commits, test-file hashes, and the case manifest hash.
- Docker image digest verification before every run.

A tag alone is not a pin; record the digest and check it at run time.

**RCAEval utility code.** The dataset pin does not pin RCAEval utility or converter code. No utility package/release version is verified in this document; if a converter is used, record its package name, version or commit, and hash separately. BLACKBOX does not implement a converter, and none is assumed by BDB-5.

### 6.6 Leakage checks

Before inference, run a deterministic scan of the model-visible prompt and filesystem. The scanner must distinguish candidate names from target labels:

- **Forbidden target-label structures:** `root_cause_service`, `fault_description`, `root_cause.txt`, target mappings, `fault=f1`, fixed SHAs, gold/test patches, and gold-patch hunks. A target label or a sentence asserting that a service failed is a no-go.
- **Candidate-name allowlist:** bare service names in the `service_inventory`, including `carts`, are allowed. The scanner must not flag a name merely because it equals the hidden target. It must flag `carts` only when it is coupled to a target marker (`root_cause_service`, `faulty_service`, `root_cause`, `is_target`, or the `f1` label field) or placed in an event description that says it failed.
- **Excerpt scan:** error text that naturally appears in the independently selected window is ordinary evidence. The scanner must not require `root_cause.txt` or the hidden root-cause line to be absent from that excerpt; it must only verify that the selection rule did not consult the label vault.
- **R2 exception:** `types_dict.nml` in the CI log is visible ordinary evidence. Scan for the added fixture's content, the passed job, `048e...`, and the fixed checkout instead.

Do not rely on the model to ignore a leak.

---

## 7. Compatibility with current BLACKBOX

### A. Capabilities already implemented

- **Event ingestion:** UUID, timezone-aware timestamp, 40-character commit, exception type/message/traceback, and 1–100 frames (`blackbox/schemas.py`).
- **Revision-pinned source resolution:** reads committed Git blobs, not working-tree content; reports unresolved files/lines/commits (`blackbox/source.py`).
- **Evidence assembly:** event, occurrences, up to 10 innermost frames, source context, bounded same-file static calls, and one-hop related code (`blackbox/investigator.py`).
- **Structured investigation:** `LIKELY_CAUSE` or `INSUFFICIENT_EVIDENCE`; `ROOT_CAUSE_SUPPORTED` is rejected; hypotheses remain review-required (`blackbox/investigation_schema.py`).
- **Reference validation:** unknown evidence IDs and unknown concrete paths/SHAs are rejected; source lines are bound to the captured revision.
- **Restricted repair:** trusted fixture registry, content hashes, human approval, allowed files, reproduction before/after, regression suite, and a derived `VERIFIED_IN_TEST_ENVIRONMENT` status (`blackbox/repair/`).

These are source-verified capabilities, not claims that a live model performs them correctly. The existing evaluation record contains only small synthetic/local cases and no BDB-5 run.

### B. Capabilities requiring a small adapter

- **R1/R2 CI-log ingestion:** convert a real CI stack trace into the existing `Event` shape, strip Travis path prefixes, select the innermost source frame, and preserve the log as untrusted evidence. This is a data adapter plus tests, not a new investigator.
- **R3 issue investigation:** reuse source/evidence/provenance but add an issue-text prompt and a schema that does not require a fabricated stack frame. This is a new entry point, not a new model.
- **Case manifest/scorer:** a frozen loader, label vault, dimension scorer, and JSON report format. These do not exist yet.

### C. Capabilities not implemented — do not pretend they are

- **Telemetry ingestion:** metrics, logs, traces, time windows, and telemetry citation IDs. T1 is blocked on this.
- **General repository repair:** the current repair gate requires a registered trusted fixture; P1 is blocked on a separate isolated external-repository repair evaluation adapter. This is an unresolved implementation task; the trusted-fixture gate must remain unchanged. No such adapter exists.
- **SWE-bench/BugSwarm orchestration:** no harness, image runner, test-patch isolation, or pass/fail parser is implemented in BLACKBOX.
- **Independent claim adjudication:** current validation checks references and some narrative contradictions, not semantic entailment. Human scoring is still required.
- **L4 counterfactual verification:** no revert/restore experiment exists.

### 7.1 Per-case classification

| Case | Class | Why |
|---|---|---|
| T1 | **C** | telemetry ingestion absent |
| R1 | **B** | CI log → Event adapter; then existing investigator |
| R2 | **B** | same adapter; negative-control prompt |
| R3 | **B** | issue → investigation adapter; existing source resolver |
| P1 | **C** | external repair blocked by trusted-fixture gate |

Do not run T1 or P1 as if they were supported today. A “no result” caused by a missing adapter is not a BLACKBOX diagnosis failure.

### 7.2 Readiness taxonomy

Compatibility classes (B/C) describe how much capability is missing. They do not mean a case is prepared or runnable. BDB-5 uses four separate states:

- **Case selected:** the case is in the five-case set with an exact ID, source/revision reference, label, and evidence record. Selection alone says nothing about readiness.
- **Case preparation-ready:** the inputs, hidden label, verification path, and adapter contract are specified well enough to freeze a manifest without inventing data. This is not a claim that a manifest is frozen; no BDB-5 manifest has been frozen in this design task.
- **Case runnable using existing capabilities:** the current checkout can execute the case without a new adapter. **No selected case meets this state.**
- **Case runnable after an adapter is implemented:** a named adapter is necessary but not sufficient. The case must also pass its external repository/image/data preflight and freeze its manifest; adapter completion alone does not make it runnable.

| Case | Selected | Preparation-ready | Runnable now | Remaining before runnable |
|---|---|---|---|---|
| T1 | Yes | **No — preflight unresolved** | No | Telemetry adapter + verify actual Parquet schema, timestamp units, and stable-ID/original-ordinal tie-breaker; verify full service inventory and F1–F5 taxonomy; verify staging/model-visible/vault separation; then freeze manifest |
| R1 | Yes | Yes; Docker reproduction remains a preflight | No | CI-log-to-`Event` adapter + Docker image/repository reproduction preflight [Unresolved] |
| R2 | Yes | Yes; Docker reproduction remains a preflight | No | Same CI adapter + Docker image/repository reproduction preflight [Unresolved] |
| R3 | Yes | Yes; image/repository acquisition remains a preflight | No | Issue-investigation entry point + Django repository/image preflight [Unresolved] |
| P1 | Yes | Yes for the evidence package; external repair is not safe to run | No | Separate isolated external-repository repair evaluation adapter + SymPy repository/image preflight; adapter itself is unresolved and not implemented [Unresolved] |

“Preparation-ready” does not imply “runnable,” and “runnable after adapter” does not imply the adapter exists. R1/R2/R3 require both their adapter and a passing external repository/image preflight; no adapter alone guarantees a runnable case. No image was pulled and no harness was run in this review, so those preflights remain [Unresolved]. The P1 entry remains conditional even after its evidence package is prepared because safe external-repository repair evaluation is an unresolved implementation task.

**T1 freeze gate.** T1 cannot be frozen until the full candidate service inventory, the task-visible F1–F5 taxonomy, timestamp units, the stable-row-ID/original-ordinal tie-breaker, and the staging/model-visible/vault separation are verified against the actual pinned data. None of those checks has been executed in this review.

---

## 8. Practical execution plan

### 8.1 Implementation and execution order

The order is driven by dependency and safety, not by download size:

1. **BDB5-R1 and BDB5-R2 — first.** Implement one CI-log-to-`Event` adapter, then run R1 (source bug) and R2 (negative control). R1 validates stack normalization and source localization; R2 immediately tests whether the same path invents a source cause when the evidence points to a missing test fixture.
2. **BDB5-R3 — second.** Add the issue-investigation entry point and reuse the existing source/evidence/provenance machinery. This comes after the CI path because it shares source resolution but does not need the CI adapter.
3. **BDB5-T1 — after telemetry ingestion exists.** Do not start with T1. It needs a telemetry schema, window selection, evidence IDs, and an L1/L2+ split in the scorer; none exists today.
4. **BDB5-P1 — last.** It is the most expensive case and requires a separate, isolated external-repository repair evaluation adapter. Do not use or weaken the trusted-fixture repair path.

**Why this differs from the previous preparation order.** The earlier order was T1 → R2 → R1 → R3 → P1, chosen mainly because T1's four files are the smallest download. That order would make the first case depend on the largest missing capability, telemetry ingestion, and would confound “BLACKBOX cannot ingest this” with “BLACKBOX diagnosed this incorrectly.” The revised order starts with the smallest adapter that reuses the existing `Event` investigator, exercises the negative control early, then adds the issue entry point. T1 waits until telemetry ingestion is real; P1 waits until safe external-repository repair evaluation is real. Data size is no longer the ordering criterion.

### 8.2 Data preparation

**R1.** Pull the image, verify the digest, start the failed-job artifact, copy only the `71dc...` checkout, and extract the CI log around the tracebacks. Normalize `/home/travis/build/bwhmather/verktyg/verktyg/requests.py` to `verktyg/requests.py`. Do not expose the passed job or `2c50...`.

**R2.** Same procedure for `83523531`; copy only `d8d8...`; extract the `types_dict.nml` error; hide the passed job and fixture. Do not label the case as a source bug.

**R3.** Clone/fetch Django at `879cc...`; supply the issue text; verify the source line and test names without exposing the patch. Use the SWE-bench environment image if available; otherwise use the repo’s documented test runner and record the difference.

**T1.** Download only the four case files, not the 3.44 GB release. Parse the Parquet tables locally. Build `W` from `time_start`/`time_end` and apply the timestamp-only row rule with the pre-registered `N_max`; never read `root_cause.txt` to select or rank logs. Redact pod/host identifiers; write evidence IDs and hashes. Hide all label fields. If the hidden root-cause line naturally appears in the independent excerpt, keep it as ordinary evidence.

**T1 physical separation.** Use three physically distinct roots:

- `staging/bdb5/T1/raw/` — the four exact pinned files, their hashes, and any intermediate parsing output. This root is never model-visible.
- `model_visible/bdb5/T1/` — only the sanitized metrics, independently selected log excerpt, complete candidate service inventory, F1–F5 taxonomy, neutral prompt, and evidence IDs. It contains no `root_cause.txt`, no `root_cause_service`/`fault` fields, no target mapping, and no Document 65 or other ground-truth document.
- `label_vault/bdb5/T1/` — `root_cause.txt`, `root_cause_service`, `fault`, the hidden service-to-fault mapping, and expected citation data. Only the scorer reads this root.

A deterministic builder runs from staging and writes the two output roots; inference mounts or reads only `model_visible/bdb5/T1/`. The staging and vault roots, Document 65, and any other document containing labels or mappings must be outside the model-visible environment.

**P1.** Clone/fetch SymPy at `cffd...`; supply the issue and allowed file; hide the patch and test patch; run the reproduction only in a disposable environment. Do not enable the current trusted-fixture repair path for this repository.

### 8.3 Expected storage

| Item | Size | Status |
|---|---:|---|
| T1 four case files | ~1.14 MiB | [Verified] from HF file sizes |
| R1 Docker image | ~1.91 GB | [Verified] Docker Hub `full_size`, uncompressed |
| R2 Docker image | ~1.91 GB | [Verified] Docker Hub `full_size`, uncompressed |
| SWE-bench Verified metadata | 6.31 MB | [Verified] HF |
| SWE-bench images/repositories | not measured | [Unresolved] do not claim |
| Minimum free space | at least 10 GB | [Recommendation] for two BugSwarm images plus metadata/cache |
| Comfortable budget | 20–30 GB | [Recommendation] once SWE-bench images are included |

### 8.4 Proposed commands/pseudocode (not executed)

```text
# R1/R2 — proposed, not run
# Pull by tag, verify the recorded sha256 digest, run the failed job,
# copy only the failed checkout, normalize the stack path, and build one Event.

# R3 — proposed, not run
# Clone/fetch django/django at 879cc..., supply the issue text, and keep
# the gold/test patches outside the model-visible filesystem.

# T1 — proposed, not run
huggingface-cli download phamquiluan/RCAEval --repo-type dataset \
  --revision afeacb11bcc94dadfd1c8f483ee4377b2b8b614e \
  --include "re3ss_carts_f1_1/*" --local-dir staging/bdb5/T1/raw
# staging/ is not model-visible. A deterministic builder writes only the
# neutral metrics, excerpt, inventory, and F1-F5 taxonomy to
# model_visible/bdb5/T1; root_cause.txt and labels go only to
# label_vault/bdb5/T1. Score L1 separately from L2+ abstention.

# P1 — proposed, not run
# Clone/fetch sympy/sympy at cffd..., supply the issue and allowed-file scope,
# and do not route it through the trusted-fixture repair gate.

# BDB-5 harness — does not exist yet
case = load_frozen_case("BDB5-R1")
evidence = adapter_for(case).build()
assert case_hash(case) == expected_hash
assert not leaked(case.hidden, evidence)
result = blackbox_entrypoint(evidence)   # only after GO
vector = score(case.labels, result)      # no aggregate
```

Do not interpret these as implemented commands. `blackbox_entrypoint` is a placeholder for the future adapter; no such BDB-5 CLI exists in this checkout.

### 8.5 Output format per case

```json
{
  "case_id": "BDB5-R1",
  "status": "COMPLETED",
  "outcome": "LIKELY_CAUSE",
  "causal_status": "SUPPORTED",
  "claims": [
    {"text": "...", "evidence_ids": ["..."], "material": true}
  ],
  "citations": {"valid": 0, "invalid": 0},
  "diagnosis": {"service": null, "file": null, "function": null, "line": null, "mechanism": null},
  "abstention": {"expected": false, "correct": null, "missing_evidence": []},
  "patch": {"applied": null, "scope_ok": null, "changed_files": []},
  "reproduction": {"before": null, "after": null, "command": "..."},
  "regression": {"passed": null, "total": null, "flaky": null},
  "usage": {"latency_ms": null, "input_tokens": null, "output_tokens": null},
  "artifacts": ["..."],
  "scorer_notes": ["..."]
}
```

### 8.6 Go/no-go checklist before the first model inference

- [ ] All five case manifests frozen and hashed. (No manifest is frozen yet; this is an execution gate, not a design claim.)
- [ ] Label vault exists outside the model-visible workspace.
- [ ] R1/R2 CI-log-to-`Event` adapter passes deterministic tests without a model.
- [ ] R1/R2 failed-revision checkouts contain no passed job, fix commit, or diff.
- [ ] R3 issue-investigation entry point passes deterministic tests without a model.
- [ ] R3/P1 base commits resolve and the gold/test patches are absent from the model filesystem.
- [ ] T1 telemetry adapter passes deterministic tests without a model.
- [ ] T1 Parquet schema inspected; timestamp units and stable-ID/original-ordinal tie-breaker recorded.
- [ ] T1 full candidate inventory and F1–F5 taxonomy are verified and frozen with no target mapping in model-visible files.
- [ ] T1 staging/model-visible/label-vault separation is tested; Document 65 and other ground-truth documents are outside the model-visible root.
- [ ] T1 evidence window was selected only by pinned timestamps; `root_cause.txt` was not read during selection.
- [ ] T1 prompt contains the full candidate inventory without a target marker and requires both service and fault class.
- [ ] T1 scoring reports L1 service/fault (`K_L1`) separately from L2+ abstention (`K_L2+`, `A_L2`).
- [ ] R2 is labelled `NOT_ESTABLISHED`, not “source bug.”
- [ ] R2 scoring permits `C_harness`/`H` while enforcing `C_app=0` and `A_app=1`.
- [ ] R1/R2/R3 external repository/image preflight has passed; otherwise the case remains blocked.
- [ ] Two reviewers have signed all five labels.
- [ ] License review is complete for RCAEval, BugSwarm, Django, SymPy, and the SWE-bench data.
- [ ] Docker images are pinned by digest; no network during the model phase.
- [ ] Model, prompt, context window, temperature, and timeout are frozen.
- [ ] A dry run with mocked outputs validates the scorer and leakage scan.
- [ ] P1 external-repository repair evaluation adapter is isolated, uses a disposable environment, and passes safe-scope tests; `blackbox/repair/eligibility.py` is unchanged.
- [ ] No live inference is enabled until every item above passes.

If any item fails, status remains `BLOCKED`; do not substitute a different case after seeing results.

---

## 9. What could invalidate the evaluation

1. **Wrong label level or dependent window.** Treating RCAEval's `carts`/`f1` label as a source-line cause would invalidate T1's L2 score. Equally, treating a correct L1 service hit as satisfying L2+ abstention would invalidate T1's scoring: the service hit and `A_L2` are separate gates. Selecting the excerpt by consulting `root_cause.txt` would invalidate the evidence-window independence.
2. **Leakage.** A hidden fix SHA, test patch, `root_cause.txt`, target-label field, or added fixture content in the prompt makes the run invalid. A bare candidate name in the service inventory is not a leak.
3. **Wrong R2 interpretation.** If reviewers label the test-fixture failure as an application bug, the negative control is destroyed. If they require blanket silence and penalize a correct missing-fixture explanation, they also mis-score the negative control.
4. **R1 fix is not the source cause.** The fix commit changes source and the failing tests pass, but BDB-5 still does not establish L4; do not call it `ESTABLISHED`.
5. **Old environment failure.** BugSwarm Python 3.2/3.5 images may not reproduce on current Docker; an environment failure is not a model failure.
6. **Image drift.** A tag without digest verification can point to a different image.
7. **SWE-bench test flaws.** OpenAI's audit found flawed tests in a large share of an audited Verified subset; a pass/fail is not semantic correctness.
8. **Issue-text leakage.** R3/P1 issue text may hint at the fix; record the hint and do not add PR comments.
9. **Contamination.** Public cases may be in model training data; a high score may be familiarity, not diagnosis.
10. **Adapter bug.** A path-normalization or event-construction error can make a correct model look wrong.
11. **Context truncation.** The 2,048-token configuration may not fit a repo case; report evidence-too-large separately.
12. **Scorer bias.** The case author scoring their own case is not independent adjudication.
13. **Five-case overgeneralization.** BDB-5 can expose failure modes; it cannot establish production reliability or a general accuracy percentage.
14. **No L4.** No selected case includes a revert/restore counterfactual; causal claims remain supported, not established.

---

## 10. What could not be verified

- RCAEval's exact application source revision for `re3ss_carts_f1_1`; the dataset does not ship one. The upstream Sock Shop repositories are references, not proof of the deployed revision.
- The RCAEval utility/converter package and release version; no separate utility pin is verified, and BLACKBOX does not implement the converter.
- The exact membership/content of the T1 candidate service inventory; the design permits all candidates, but no verified inventory is claimed.
- The `logs.parquet` schema, timestamp units, presence of a stable row ID, and physical row-ordinal behavior; none were inspected.
- The final T1 excerpt selected under the timestamp-only rule; no Parquet file was parsed, so its exact row count and contents are unverified. T1 is not frozen.
- The telemetry Parquet contents beyond file size and column metadata; the log line was fetched, but the full logs/metrics were not parsed.
- Whether the `root_cause.txt` line is causally sufficient for fault F1. It is associated evidence, not a proof.
- BugSwarm image reproducibility at the current date; the API reports `Reproducible`/`5/5`, but the `reproduced` field is `false` and the images were not pulled. Treat reproduction as a required preflight.
- Current BugSwarm 1.3.1 compatibility for these 2016 artifacts; the metadata says active, but old dependencies may fail.
- SWE-bench Docker image behavior, test execution, and PASS_TO_PASS results; none were run.
- Dataset-level license for SWE-bench Verified; the API/card still exposes none.
- Legal conclusions about GPL/BSD/Apache obligations; this is an engineering report, not legal advice.
- Reviewer identities and independent adjudication; no reviewers were assigned in this design task.
- Any model accuracy, abstention rate, patch success, or latency; no model was called.

---

## 11. Git status comparison

**Before this document:** `git status --porcelain` had **454 entries**. The tree already contained the previous untracked research report, source modifications, tests, fixtures, data, and graphify files. Those were pre-existing and were not created or changed by this task.

**After creation and the final review pass:** the current sorted comparison has **457** entries against the 454-entry baseline:

```diff
+?? "research (3).zip"
+?? "research (4).zip"
+?? research/64_M4B3_AUDIT_REMEDIATION_REPORT.md
+?? research/65_BDB5_PILOT_SPEC.md
```

- Before: 454 entries.
- After: 458 entries.
- Added: 4 entries; removed: none.
- Only `research/65_BDB5_PILOT_SPEC.md` is attributable to this task.
- `research (3).zip`, `research (4).zip`, and `research/64_M4B3_AUDIT_REMEDIATION_REPORT.md` were absent from the baseline and appeared during the review; this task did not create or modify them, and they remain untouched.

The earlier 454→455 expectation was true when the document was created, but it no longer matches the current tree because three external entries appeared. The implementation-readiness review changed only `research/65_BDB5_PILOT_SPEC.md`. The 19 tracked files already shown as modified in the baseline remain modified; this task did not change them.

**No source code, tests, fixtures, labels, preregistration, Documents 50/56/57/60/61/63, benchmark results, or M4B.3 ledger were modified by this task.** No dataset was downloaded in bulk, no Docker image was pulled, no model was called, and no BDB-5 case was executed.

---

## 12. Sources

All sources accessed **2026-11-07**.

**RCAEval**

- Dataset: https://huggingface.co/datasets/phamquiluan/RCAEval
- Frozen revision: https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e
- Case T1: https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re3ss_carts_f1_1
- Root-cause line: https://huggingface.co/datasets/phamquiluan/RCAEval/blob/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re3ss_carts_f1_1/root_cause.txt
- RCAEval utility code/release: [Unresolved] — no package/release pin is recorded; BLACKBOX does not implement the converter.
- Repository: https://github.com/phamquiluan/RCAEval
- Sock Shop deployment: https://github.com/microservices-demo/microservices-demo
- Carts service: https://github.com/microservices-demo/carts

**BugSwarm**

- API documentation: https://www.bugswarm.org/docs/toolset/bugswarm-rest-api
- R1 artifact: http://www.api.bugswarm.org/v1/artifacts/bwhmather-verktyg-109227527
- R1 diff: http://www.api.bugswarm.org/v1/diffs/bwhmather-verktyg-109227527
- R1 failed log: http://www.api.bugswarm.org/v1/logs/109227527
- R2 artifact: http://www.api.bugswarm.org/v1/artifacts/marshallward-f90nml-83523531
- R2 diff: http://www.api.bugswarm.org/v1/diffs/marshallward-f90nml-83523531
- R2 failed log: http://www.api.bugswarm.org/v1/logs/83523531
- R1 image: https://hub.docker.com/r/bugswarm/images/tags?name=bwhmather-verktyg-109227527
- R2 image: https://hub.docker.com/r/bugswarm/images/tags?name=marshallward-f90nml-83523531
- Repository: https://github.com/BugSwarm/bugswarm
- Paper: https://arxiv.org/abs/1903.06725

**SWE-bench**

- Dataset: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified
- Frozen revision: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/tree/78f471bf655a3137b2e8a75af1501690ec009ec3
- Repository: https://github.com/SWE-bench/SWE-bench
- R3 instance source: https://github.com/django/django/pull/11133
- R3 issue: https://code.djangoproject.com/ticket/30294
- P1 instance source: https://github.com/sympy/sympy/pull/20590
- P1 issue: https://github.com/sympy/sympy/issues/20567
- OpenAI test audit: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/

**Local BLACKBOX**

- `README.md` — implemented event, investigation, and restricted repair behavior.
- `blackbox/schemas.py` — `Event` and `Frame`.
- `blackbox/investigator.py` — evidence collection, validation, and outcomes.
- `blackbox/source.py` — revision-pinned source resolution.
- `blackbox/repository_intelligence.py` — bounded Python relationship retrieval.
- `blackbox/repair/eligibility.py` — trusted-fixture and review gates.
- `blackbox/repair/pipeline.py` — reproduction, patch, and regression flow.
- `research/63_BLACKBOX_DIAGNOSTIC_BENCHMARK_LANDSCAPE.md` — prior landscape and BDB design.

**Method note.** API metadata, commit contents, license files, and small text artifacts were read directly. Large telemetry tables, Docker images, and SWE-bench environments were not downloaded or run. No model was used to label a case. The five cases are **selected for review**, not executed.

---

**Final status:** `BDB5_SPEC_PARTIAL — T1_PREFLIGHT_UNRESOLVED — NOT_EXECUTED — LIVE_INFERENCE_DISABLED`
