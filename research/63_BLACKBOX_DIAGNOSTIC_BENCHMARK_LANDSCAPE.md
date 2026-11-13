# BLACKBOX Real-World Diagnostic Benchmark Landscape

**Document:** 63
**Status:** Research and design only. No benchmark has been implemented, no dataset has been downloaded, no model inference has been run, and no Docker, repair, source, test, fixture, label, preregistration, or existing research document has been modified.
**Research access date:** 2026-11-07
**Repository examined:** `C:/Users/Adi/Documents/ChatGPT/black`
**Scope:** public datasets and testbeds relevant to telemetry-based root-cause analysis (RCA), repository-level debugging, and test-verified repair.

## Evidence labels used in this report

- **[Confirmed]** stated by the official repository, paper, dataset card, license file, or official project documentation.
- **[Unclear]** sources conflict, the information is absent, or the exact current value could not be verified without downloading or executing the project.
- **[Assessment]** an analyst judgment about BLACKBOX suitability, not a claim about the dataset.

The brief reports that M4B.3 found extra source context did not automatically produce correct causal diagnoses. That finding is treated here as the starting point. In the repository snapshot examined, the visible M4B.2 oracle-context diagnostic changed **0/6** outcomes, and M4B.3 is recorded in `EVALUATION.md` as offline preparation with no live investigator calls. Those local records are consistent with the brief's conclusion but are not used as a substitute for a completed multi-case benchmark. Six synthetic cases cannot establish diagnostic accuracy, regardless of how the M4B.3 live-run discrepancy is resolved.

---

## 1. Executive research conclusion

**No single public dataset validates all of BLACKBOX's intended abilities.** The field supplies three different kinds of ground truth, and they must not be collapsed:

1. **Telemetry RCA labels** answer "which service or indicator was faulty?" Examples: RCAEval, AIOpsLab.
2. **Repository bug labels** answer "what source change fixes this issue?" Examples: SWE-bench, BugsInPy, Defects4J, BugSwarm, QuixBugs.
3. **Log anomaly labels** answer "is this log sequence abnormal?" Example: LogHub.

BLACKBOX needs a fourth, stronger object that none of these supplies uniformly: **an incident-specific causal package** containing the observed event, authenticated runtime evidence, the exact source revision, the behavioral contract, the triggering condition, and a counterfactual reproduction. Service-level labels do not prove source-line causation. A passing patch does not prove that the proposed mechanism caused the incident. A normal/abnormal log label does not identify a cause.

**Recommended first real evaluation dataset: RCAEval, specifically a frozen RE3 subset.** It is the closest public match to BLACKBOX's input (multi-source telemetry from realistic microservice failures), has per-case service and fault labels, includes code-level fault scenarios, is openly downloadable, and is MIT-licensed at the dataset and repository level. It is suitable for **diagnosis**, not for repair verification. Its labels are mostly service/fault-level; it does not ship a uniform faulty source snapshot or a reproduction test for every case.

**Recommended repair track, kept separate: SWE-bench Verified and BugSwarm.** SWE-bench provides base commits, issue text, FAIL_TO_PASS/PASS_TO_PASS tests, and Docker execution. BugSwarm provides real CI fail/pass pairs, Docker images, build logs, failed-test names, and fix revisions. Both can verify a patch; neither supplies an incident-grade causal explanation. SWE-bench's own "Verified" label is not absolute: OpenAI's later audit found material test problems in a large share of the audited subset.

**Recommended live testbed for later: AIOpsLab.** It is a framework, not a static dataset. It can deploy microservices, inject faults, generate workloads, export telemetry, and evaluate an agent interactively. It is excellent for Stage 3–4 realism, but it is a poor first dataset because it requires Kubernetes/Helm or Azure and does not provide a fixed, instantly downloadable case corpus with immutable labels.

**Do not use LogHub, QuixBugs, Defects4J, or BugsInPy as the primary diagnostic benchmark.** LogHub has no causal labels. QuixBugs is too small and algorithmic. Defects4J and BugsInPy are controlled repair/localization benchmarks with isolated bugs, not production telemetry incidents. BugsInPy currently has **no license file**, which is a commercial-use blocker.

**Recommended architecture:** a staged BLACKBOX Diagnostic Benchmark (BDB) that wraps public sources rather than pretending they are one benchmark. Stage 1 calibrates reasoning primitives. Stage 2 uses realistic telemetry-only cases. Stage 3 adds repository-level investigations. Stage 4 verifies repairs. Each stage has its own labels, scoring dimensions, and leakage controls.

**Critical conclusion:** the first real evaluation should be designed to **expose where BLACKBOX is wrong**, not to produce an impressive single accuracy number. A 25-case study can reveal failure modes and instrumentation bugs. It cannot establish production reliability, and neither can 100 cases.

---

## 2. Dataset landscape

### 2.1 RCAEval (highest priority for diagnosis)

**Official sources:** [GitHub repository](https://github.com/phamquiluan/RCAEval) · [Hugging Face dataset](https://huggingface.co/datasets/phamquiluan/RCAEval) · [paper, arXiv 2412.17015](https://arxiv.org/abs/2412.17015) · [WWW '25 Companion record](https://dl.acm.org/doi/10.1145/3701716.3715290)

**Publication:** WWW '25 Companion, pages 777–780 (2025); arXiv v5 dated 2025-02-03. The dataset and code are actively maintained; the PyPI package reached 1.6.0 in August 2026 and the Hugging Face card was updated in 2026. **[Confirmed]**

**Contents and size. [Confirmed]** RCAEval contains **735 failure cases** from three microservice systems: Online Boutique, Sock Shop, and Train Ticket. It reports **11 fault types** across resource, network, and code-level categories.

| Suite | Cases | Telemetry | Faults | Notes |
|---|---:|---|---|---|
| RE1 | 375 | Metrics only | CPU, memory, disk, delay, loss | No logs or traces |
| RE2 | 270 | Metrics, logs, traces | RE1 faults plus socket | Multi-source; Sock Shop has logs but no traces |
| RE3 | 90 | Metrics, logs, traces | F1–F5 code-level faults | Code-level focus; Sock Shop has logs but no traces |

RE3 has 30 cases per system. The five code-level fault classes are incorrect parameter values (F1), missing parameters (F2), missing function call (F3), incorrect return values (F4), and missing exception handlers (F5). The RE3 grid is not uniform: F5 appears only in Online Boutique, Train Ticket covers two root-cause services, Online Boutique covers four, and repetitions vary from three to six. **[Confirmed by the dataset card.]**

**Ground truth. [Confirmed with an important qualification]** Each case has an annotated **root-cause service** and an injected **fault type**. The paper says the root cause of a code-level fault is determined from stack traces that indicate the faulty line; when stack traces are unavailable, error logs or response codes may indicate the affected service. The published case index exposes `root_cause_service` and `fault`; only eight RE3-SS cases include an extra `root_cause.txt` with a root-cause log line. **There is no uniform source-line label, no per-case patch, and no reproduction test.** A service/fault label is sufficient to score coarse RCA; it is not sufficient to prove that BLACKBOX identified the actual source-level causal mechanism.

**Reproduction and source. [Confirmed]** RCAEval is a telemetry replay/evaluation benchmark, not a repair benchmark. It provides metrics, logs, traces, injection timestamps, and an evaluation library with **15 baselines** and AC@k/Avg@k metrics. It does not package the faulty application source or a one-command reproduction for each case. Its systems are open-source, so a separate source snapshot could be assembled, but that would be a new benchmark construction, not a property of RCAEval.

**License. [Confirmed]** The top-level RCAEval repository is MIT (Copyright 2024 Luan Pham), and the Hugging Face dataset is tagged MIT. The PyPI package documents that bundled baseline code carries different licenses; for example, BARO is MIT and CausalRCA has no license. **The MIT top-level license therefore does not automatically clear every bundled baseline for commercial reuse.** Verify the `LICENSES` directory before shipping baseline code.

**Download and privacy. [Confirmed]** Hugging Face provides a 3.44 GB Parquet conversion, downloadable by suite or single case; the original Zenodo/figshare copies are much larger. No authentication is required. The data is from lab microservice deployments, not customers, but logs should still be inspected for secrets or personal data before sending any excerpt to a model.

**Main limitations. [Assessment]** (a) labels are service/fault-level, not full causal chains; (b) faults are injected, so they may be cleaner and more separable than production incidents; (c) telemetry volume is enormous (millions of log lines and traces in RE2); (d) only three systems and a handful of services; (e) no source/test/repair package; (f) public cases may be in model training data; (g) the benchmark's own baselines perform only moderately, which is useful but does not validate an LLM investigator.

### 2.2 Microsoft AIOpsLab (framework and live testbed)

**Official sources:** [GitHub repository](https://github.com/microsoft/AIOpsLab) · [project site](https://microsoft.github.io/AIOpsLab/) · [MLSys 2025 paper record](https://proceedings.mlsys.org/paper_files/paper/2025/hash/d1f9e4a9f109b6e8b75ed362736f22ec-Abstract-Conference.html)

**Publication:** MLSys 2025; preprint dated 2024-10-09. Repository actively developed (646 commits at access). **[Confirmed]**

**Contents. [Confirmed]** AIOpsLab is not a static dataset. It is an orchestrator plus problem registry, workload generator (wrk2), fault generators (including Chaos Mesh and virtualization faults), observer/telemetry APIs (Prometheus, logs, traces), and an assessment layer. It supports four task types: **detection, localization, analysis, and mitigation**. The paper describes a benchmark suite of **100 problems**; the repository's own agent documentation says "60+ problems." The exact current registry count was not executed or downloaded, so treat the count as **[Unclear]**.

**Ground truth. [Confirmed]** Each problem defines an application, task, injected fault, workload, and evaluator. The ground truth is the injected fault and the evaluator's expected solution, not a naturally occurring incident with an independently reconstructed causal chain. Some evaluation is quantitative; the repository also includes qualitative and LLM-as-judge evaluators.

**Reproduction. [Confirmed]** Yes, but it is infrastructure-heavy: Python 3.11, Helm, a Kubernetes cluster via `kind` or Azure Terraform, and optional Docker for some fault injectors. The orchestrator can start a problem, inject a fault, collect telemetry, and evaluate an agent's actions.

**Source and tests. [Confirmed]** Application source and deployment metadata are in the repository/submodules, but there is no single frozen archive of every case's source, test, and expected patch. The agent interacts with a live service, so reproducibility depends on the cluster and environment.

**License. [Confirmed]** MIT (Microsoft Corporation). Third-party applications and chaos tools retain their own licenses.

**Privacy. [Assessment]** Lab/synthetic deployments; lower privacy risk than production telemetry, but cluster logs and cloud credentials must be handled carefully.

**Main limitations. [Assessment]** Not a first dataset: it requires substantial infrastructure, is dynamic rather than a fixed corpus, and its labels test injected-fault recovery rather than historical causal attribution. It is the best candidate for later interactive evaluation, especially mitigation and tool use.

### 2.3 SWE-bench (repository-level issue resolution and repair)

**Official sources:** [GitHub repository](https://github.com/SWE-bench/SWE-bench) · [official site](https://www.swebench.com/) · [ICLR 2024 paper](https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html) · [Verified dataset](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)

**Publication:** ICLR 2024 (oral); arXiv 2310.06770, October 2023. Actively maintained. **[Confirmed]**

**Contents. [Confirmed]** The full benchmark has **2,294** issue–pull-request instances from **12 popular Python repositories**. Each instance includes a repository, base commit, problem statement, gold patch, test patch, FAIL_TO_PASS tests, PASS_TO_PASS tests, and a Docker evaluation environment. The **Verified** subset has **500** human-validated instances. The official pages disagree on SWE-bench Lite (300 on the leaderboard/FAQ versus 534 in the dataset guide); do not rely on the Lite count without checking the exact revision.

**Ground truth. [Confirmed]** The gold patch and tests are the reference. Evaluation applies the candidate patch and runs FAIL_TO_PASS and PASS_TO_PASS tests in Docker. This is **repair correctness**, not root-cause diagnosis. The issue text is a problem report, not authenticated runtime telemetry.

**Source and tests. [Confirmed]** Yes: repository at a base commit, test patch, and executable test commands are part of the harness. This is the strongest public machinery for "failure before patch, pass after patch, regressions still pass."

**License. [Confirmed and unclear]** The SWE-bench code repository is MIT. The Hugging Face dataset card/API accessed on 2026-11-07 did **not** expose a dataset-level license field. The underlying repositories have their own licenses. Do not assume the data is MIT merely because the harness is MIT; verify per repository before redistribution or commercial use.

**Download. [Confirmed]** The Verified dataset metadata is 6.31 MB on Hugging Face; evaluation images are much larger and require Docker. No authentication was required for the dataset card/API at access.

**Main limitations. [Assessment]** (a) no metrics, traces, or production incident context; (b) the public dataset contains the gold patch and test patch, so leakage is easy; (c) issue text can reveal the fix; (d) tests can reject correct alternative solutions; (e) full benchmark is Python-only; (f) benchmark contamination is likely for frontier models. OpenAI's later analysis (accessed 2026-11-07) reports that, in an audited 27.6% subset (138 problems), **at least 59.4% had flawed tests that reject functionally correct submissions**. That does not invalidate SWE-bench as a repair stress test, but it invalidates treating "Verified resolved" as ground-truth semantic correctness.

### 2.4 BugSwarm (real CI failures and fixes)

**Official sources:** [GitHub repository](https://github.com/BugSwarm/bugswarm) · [dataset site](https://www.bugswarm.org/) · [releases](https://www.bugswarm.org/releases) · [statistics](https://www.bugswarm.org/statistics/) · [ICSE 2019 paper, arXiv 1903.06725](https://arxiv.org/abs/1903.06725)

**Publication:** ICSE 2019. Dataset version 1.3.1 released 2026-05-27; actively maintained. **[Confirmed]**

**Contents. [Confirmed]** BugSwarm mines real GitHub Actions/Travis CI fail–pass pairs and packages them as Docker artifacts. At access, the statistics page reports **3,835 reproducible artifacts, 528 flaky artifacts, and 22 unreproducible artifacts** (4,385 total); the original 2019 dataset had 3,091. Languages are Java and Python. Artifact metadata includes repository, failed and passed job IDs, base/trigger SHAs, failed-test names, exception classes, test counts, build system, diff size, reproduction attempts/successes, and CI service.

**Ground truth. [Confirmed with qualification]** The fail/pass pair and the code difference between the jobs are the reference. The "fix" is a real commit, not an independently authored causal explanation. A commit may contain unrelated changes; BugSwarm records diff size and changed-file counts but does not label the causal line.

**Reproduction. [Confirmed]** Strong: each artifact is a Docker image with buggy and fixed versions; the reproducer runs tests at least three times and compares failing-test names and build outcome with the historical log. Current reported reproducibility is 99% under that definition. Flaky artifacts are explicitly retained and labeled.

**Source and tests. [Confirmed]** Yes, inside the Docker images. This is a realistic CI failure benchmark, closer to BLACKBOX's "application error plus repository" shape than SWE-bench's clean issue text.

**License. [Confirmed with caveat]** The BugSwarm infrastructure is BSD-3-Clause (University of California). The artifacts contain third-party open-source projects under their own licenses; commercial use of an artifact requires checking that project's license, not just BugSwarm's.

**Download. [Confirmed]** Public website/API and Docker Hub images; no authentication described. Some images are large. Old artifacts can be deprecated when upstream package repositories disappear.

**Main limitations. [Assessment]** (a) no service/metric/trace RCA labels; (b) CI logs are not a complete incident record; (c) flakiness and environment decay; (d) Java/Python only; (e) the fix commit is not proof of the cause; (f) some artifacts have large or noisy diffs. Best for Stage 3–4, not for first-pass telemetry diagnosis.

### 2.5 LogHub (log corpora, not root-cause labels)

**Official sources:** [GitHub repository](https://github.com/logpai/loghub) · [Zenodo record v8](https://zenodo.org/records/8196385) · [ISSRE 2023 paper, arXiv 2008.06448](https://arxiv.org/abs/2008.06448)

**Publication:** ISSRE 2023; Zenodo v8 published 2023-07-31. Actively used; the project reports downloads by 450+ organizations. **[Confirmed]**

**Contents. [Confirmed]** LogHub provides **19 real-world log datasets** spanning distributed systems, supercomputers, operating systems, mobile systems, server applications, and standalone software. Six are labeled for anomaly detection; 13 are unlabeled. HDFS-v1 has about 11.2 million lines and 575,000 block-level sequences; BGL has about 4.7 million lines and 43 alert categories. Other datasets include Hadoop, Spark, OpenStack, Thunderbird, Zookeeper, HealthApp, Android, and OpenSSH.

**Ground truth. [Confirmed]** Labels are task-specific: HDFS labels a block sequence normal/abnormal; BGL labels an event's alert category; other datasets may label duplicate issues or anomalies. **There is no root-cause service, source line, or patch label.** Some labels are generated by handcrafted rules, and label quality varies by dataset.

**Reproduction and source. [Confirmed]** No application source and no per-incident reproduction. Logs are raw text, sometimes with structured templates.

**License. [Confirmed but conflicting]** The GitHub README says the datasets are "freely available for research or academic work" and requires attribution/citation. The Zenodo record is tagged CC BY 4.0. These are not the same grant. **Treat LogHub as research/academic-only unless counsel resolves the conflict**, especially for commercial redistribution. Some logs are explicitly unsanitized production data.

**Privacy. [Confirmed risk]** The project states that, wherever possible, logs are not sanitized or anonymized. Raw logs can contain hostnames, paths, tokens, or personal data. Never send raw public telemetry to an external model without inspection and redaction.

**Main limitations. [Assessment]** No causal labels, no source, no reproduction, variable formats, and label noise. Useful for testing log parsing, anomaly triage, evidence citation, and runtime-observation fidelity. Not a standalone BLACKBOX diagnostic benchmark.

### 2.6 BugsInPy (Python bug repair)

**Official sources:** [GitHub repository](https://github.com/soarsmu/BugsInPy) · [ESEC/FSE 2020 tool-demo paper](https://dl.acm.org/doi/10.1145/3368089.3417943) · [arXiv 2401.15481](https://arxiv.org/abs/2401.15481)

**Publication:** ESEC/FSE 2020 tool demo. Repository created 2020; maintenance is limited and the license is unresolved. **[Confirmed/Unclear]**

**Contents. [Confirmed]** **493 real bugs from 17 Python projects**, with buggy and fixed revisions, isolated fix patches, developer tests, and checkout/compile/test commands. The framework supports coverage, mutation, fuzzing, and Docker. Projects are popular Python 3 repositories.

**Ground truth. [Confirmed with qualification]** The fix patch and test suite are the reference. Tests expose the bug. There is no causal narrative, no telemetry, and no service-level label.

**Reproduction. [Confirmed, with a quality caveat]** The framework provides `bugsinpy-checkout`, `bugsinpy-compile`, and `bugsinpy-test`. An independent 2023 reproduction study found that the original scripts allowed only **67%** of bugs to be reproduced before fixes; the authors improved the tooling. Treat per-case reproducibility as something to verify, not a guaranteed property.

**Source and tests. [Confirmed]** Yes.

**License. [Confirmed absence]** As of access, the repository had **no license file**, and an open issue (#94, October 2025) explicitly asks for license information. The paper is CC BY-NC-ND 4.0. **Do not redistribute or commercially use the dataset until the maintainers add a license and the status of the included projects is clarified.** This is a hard blocker, not a minor caveat.

**Main limitations. [Assessment]** No telemetry, isolated bugs, Python-only, license-blocked, aging dependencies. Good controlled repair benchmark; not a realistic incident benchmark.

### 2.7 Defects4J (Java bug localization and repair)

**Official sources:** [GitHub repository](https://github.com/rjust/defects4j) · [project site](https://defects4j.org/) · [ISSTA 2014 paper](https://dl.acm.org/doi/10.1145/2610384.2628055)

**Publication:** ISSTA 2014; current version 3.0.1. Actively maintained (1,090 commits). **[Confirmed]**

**Contents. [Confirmed]** The current repository lists **854 active bugs plus 10 deprecated bugs** from **17 Java projects**. Each bug has a buggy and fixed revision, developer-written trigger tests, a stack trace for each trigger, modified/relevant classes, and test metadata. Java 11 is required for the current version.

**Ground truth. [Confirmed with qualification]** The fix patch, modified classes, and trigger tests are the reference. Stack traces provide partial causal evidence. Bugs are isolated and minimized; there is no production telemetry, and most cases are single-fault.

**Reproduction and source. [Confirmed]** Yes: checkout, compile, test, coverage, mutation, and export commands. Project repositories are downloaded during `init.sh`.

**License. [Confirmed]** The Defects4J framework is MIT. The 17 upstream projects retain their own licenses. Java 11, Git, Subversion, Perl, and `cpanm` are required.

**Main limitations. [Assessment]** Java-only, isolated/minimal bugs, no runtime telemetry, test suites may be narrow, and the benchmark is old enough to have contamination risk. Better for localization/repair than for incident RCA.

### 2.8 QuixBugs (small program-repair calibration)

**Official sources:** [GitHub repository](https://github.com/jkoppel/QuixBugs) · [project page](https://jkoppel.github.io/QuixBugs) · [SPLASH 2017 paper](https://dl.acm.org/doi/10.1145/3135932.3135941)

**Publication:** SPLASH Companion 2017. Stable, low activity. **[Confirmed]**

**Contents. [Confirmed]** **40 programs**, each translated into Python and Java, each with a one-line defect, passing/failing tests, and corrected versions. Defects span 14 classes. The programs are algorithmic exercises from the Quixey Challenge, not production systems.

**Ground truth. [Confirmed]** The one-line corrected program and tests are the reference. The defect is known at line level, but the setting is synthetic and tiny.

**Reproduction. [Confirmed]** `pytest` for Python; compiled Java classes are included. Tests run in under a second except two slow cases.

**License. [Confirmed]** MIT.

**Main limitations. [Assessment]** Too small and too simple for realism; one-line bugs encourage overfitting; tests are narrow. One repair study found 16/40 programs repairable by test-suite-adequate patches, and 53.3% of candidate patches were overfitting under manual assessment. Use only for Stage 1 calibration and test-harness smoke checks.

### 2.9 OpenTelemetry Demo (live microservice testbed, not a dataset)

**Official sources:** [GitHub repository](https://github.com/open-telemetry/opentelemetry-demo) · [architecture](https://opentelemetry.io/docs/demo/architecture/) · [feature flags](https://opentelemetry.io/docs/demo/feature-flags/)

**Publication:** General availability announced in 2022; continuously maintained (2,431 commits at access). **[Confirmed]**

**Contents. [Confirmed]** The Astronomy Shop is a microservice application with services in multiple languages (including Go, Java, .NET, Python, Node.js, and C++), communicating over gRPC/HTTP, instrumented with OpenTelemetry traces, metrics, and logs. It includes a load generator and feature flags for failure scenarios (for example ad failure, high CPU, slow image load, Kafka consumer death).

**Ground truth. [Confirmed absence]** There is no built-in case corpus, causal label, or repair test for a BLACKBOX-style incident. You must define the scenario, record telemetry, establish the intended behavior, and build the reproduction. The feature flags simulate faults; they do not provide ground-truth causal explanations.

**Reproduction. [Confirmed]** Docker Compose or Kubernetes/Helm. The full stack is resource-heavy; one secondary guide recommends about 6 GB of RAM, but that figure is not an official guarantee.

**License. [Confirmed]** Apache-2.0. This is the most commercial-friendly testbed in the set.

**Main limitations. [Assessment]** No labels, no fixed cases, no repair harness, and operational complexity. Excellent for generating new, non-public incidents and for testing telemetry ingestion; not a benchmark by itself.

---

## 3. Official sources and license verification

| Dataset | Official source | Original publication | Code license | Data license | Commercial note |
|---|---|---|---|---|---|
| RCAEval | [GitHub](https://github.com/phamquiluan/RCAEval), [HF](https://huggingface.co/datasets/phamquiluan/RCAEval) | WWW '25 Companion; arXiv 2412.17015 | MIT | MIT (HF) | Bundled baselines have mixed/no licenses; inspect `LICENSES` |
| AIOpsLab | [GitHub](https://github.com/microsoft/AIOpsLab) | MLSys 2025 | MIT | N/A (framework) | MIT; third-party apps/tools separate |
| SWE-bench | [GitHub](https://github.com/SWE-bench/SWE-bench), [HF](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified) | ICLR 2024; arXiv 2310.06770 | MIT | Not declared in HF card/API at access | Verify each source repository; do not assume data is MIT |
| BugSwarm | [GitHub](https://github.com/BugSwarm/bugswarm), [site](https://www.bugswarm.org/) | ICSE 2019; arXiv 1903.06725 | BSD-3-Clause | Artifact metadata/infrastructure BSD-3; code inside images varies | Check each upstream project |
| LogHub | [GitHub](https://github.com/logpai/loghub), [Zenodo](https://zenodo.org/records/8196385) | ISSRE 2023; arXiv 2008.06448 | Repository code not the dataset | GitHub: research/academic only; Zenodo: CC BY 4.0 | Conflict; treat as research-only |
| BugsInPy | [GitHub](https://github.com/soarsmu/BugsInPy) | ESEC/FSE 2020 tool demo; arXiv 2401.15481 | **No license file** | No explicit license | **Blocked for commercial/redistribution** |
| Defects4J | [GitHub](https://github.com/rjust/defects4j), [site](https://defects4j.org/) | ISSTA 2014 | MIT | Framework MIT; upstream projects separate | Check project licenses |
| QuixBugs | [GitHub](https://github.com/jkoppel/QuixBugs) | SPLASH Companion 2017 | MIT | MIT | Permissive |
| OpenTelemetry Demo | [GitHub](https://github.com/open-telemetry/opentelemetry-demo) | GA 2022; no research paper | Apache-2.0 | N/A (application) | Permissive |

**License verification notes.**

- **[Confirmed]** RCAEval's top-level `LICENSE` is MIT (Copyright 2024 Luan Pham). Its PyPI documentation says the repository includes code from multiple sources with different licenses and that at least one baseline (CausalRCA) has no license. A top-level MIT file is not a blanket clearance for those files.
- **[Confirmed]** AIOpsLab's `LICENSE.txt` is MIT (Microsoft Corporation). Its applications and Chaos Mesh are separate dependencies.
- **[Confirmed]** SWE-bench's GitHub repository is MIT. The Hugging Face dataset API returned no `license` field in `cardData` at access; the dataset card description also did not state one. This report therefore does **not** claim that the dataset is MIT.
- **[Confirmed]** BugSwarm's repository `LICENSE` is BSD-3-Clause (Copyright 2019, University of California). The artifacts package upstream source; those projects' licenses govern their code.
- **[Confirmed conflict]** LogHub's GitHub README says "freely available for research or academic work"; its Zenodo record is CC BY 4.0. The safest operational interpretation is the narrower research-only grant. The logs are often unsanitized.
- **[Confirmed absence]** BugsInPy has no license file, and an open issue explicitly requests one. The paper's CC BY-NC-ND license covers the paper, not automatically the dataset. This is a legal blocker, not a reason to guess.
- **[Confirmed]** Defects4J's framework is MIT; the README explicitly separates the framework from the upstream projects.
- **[Confirmed]** QuixBugs is MIT; OpenTelemetry Demo is Apache-2.0.

**Access and privacy summary.** RCAEval (3.44 GB Parquet; no auth), SWE-bench Verified metadata (6.31 MB; Docker images large), BugSwarm (public site/Docker Hub), LogHub (about 6 GB on Zenodo, public), Defects4J/BugsInPy/QuixBugs/OTel Demo (public Git repositories; heavy initialization/containers). None of this research downloaded the datasets. No raw telemetry was sent to an external model.

---

## 4. Dataset suitability ranking

The requested comparison uses the dimensions that matter for BLACKBOX, not popularity. "Diagnosis suitability" means ability to test root-cause reasoning from runtime evidence. "Repair verification" means ability to prove failure-before, pass-after, and regression safety. A dataset can be strong on one and weak on the other.

| Dataset | Data type | Diagnosis suitability | Reproduction support | Repair verification | License | Main limitations |
|---|---|---|---|---|---|---|
| **RCAEval** | Microservice metrics/logs/traces, 735 cases | **High** for service/indicator RCA; code-level subset | Telemetry replay; no per-case app/test package | **None** | MIT (dataset/code); mixed baselines | Service/fault labels, no source/repair, synthetic injection, huge telemetry |
| **BugSwarm** | Real CI fail/pass Docker artifacts, Java/Python | **Medium** (CI logs, stack traces; no service/metric labels) | **High**; 3× reproduction, Docker | **High** for patch tests; noisy commits | BSD-3 infra; upstream varies | No causal labels, flakiness, environment decay |
| **SWE-bench Verified** | GitHub issues + base commits + tests | **Low** for runtime RCA; issue text only | **High**; Docker FAIL_TO_PASS/PASS_TO_PASS | **High**, but test-quality caveats | Code MIT; data license unclear | No telemetry; gold/test leakage; flawed tests found |
| **AIOpsLab** | Live microservice testbed + injected faults | **High** interactive, low static reproducibility | **High** but needs K8s/Helm | **Medium** (mitigation, not code patch) | MIT | Infrastructure-heavy; no fixed corpus; exact problem count unclear |
| **Defects4J** | Java buggy/fixed revisions, tests, stack traces | **Medium** for code localization; no runtime telemetry | **High**; checkout/test | **High** for controlled Java patches | MIT framework; upstream separate | Isolated single bugs, Java-only, no ops context |
| **BugsInPy** | Python buggy/fixed revisions, tests, patches | **Medium** code localization; no telemetry | **Medium–High**; 67% historical reproduction | **High** if reproduced | **No license** | Legal blocker, aging deps, Python-only |
| **LogHub** | Raw system logs, 19 datasets | **Low** for causation; medium for anomaly triage | **None** | **None** | Research-only / CC BY conflict | No causal labels, no source, unsanitized |
| **QuixBugs** | 40 one-line bug programs, Java/Python | **Low** realism; high control | **High**; pytest | **High** for tiny patches | MIT | Too small/simple; overfitting |
| **OpenTelemetry Demo** | Live multi-language microservices + OTel | **Testbed only**; no labels | **High** for generating incidents | **None built in** | Apache-2.0 | No cases, labels, or repair harness |

### Ranked recommendation

1. **RCAEval RE3 — first real diagnostic dataset.** Best match for multi-source telemetry, code-level faults, service/fault labels, and a permissive dataset license. Use 25 frozen cases first. Score service/indicator attribution and mechanism hypotheses; do not claim repair.
2. **BugSwarm — first realistic CI failure/fix track.** Best combination of real failures, real fixes, Docker reproducibility, and CI evidence. Use for Stage 3/4, not as a service-level RCA label set.
3. **SWE-bench Verified — strongest clean repair-verification harness.** Use after a diagnosis stage, with gold/test patches withheld and test-quality caveats reported. Do not use it to validate telemetry RCA.
4. **AIOpsLab — later interactive testbed.** Best for live detection/localization/mitigation and tool use; too heavy for the first 25-case study.
5. **Defects4J — controlled Java localization/repair.** Good for cross-language and minimal-bug controls, not realistic incident diagnosis.
6. **BugsInPy — Python repair, legally blocked.** Technically useful; do not integrate until licensing is resolved.
7. **LogHub — observation-layer stress test.** Useful for log parsing, anomaly triage, and citation fidelity; not a diagnostic ground truth.
8. **QuixBugs — Stage 1 calibration only.** Cheap, deterministic, but too simple to support any generalization claim.
9. **OpenTelemetry Demo — incident generator, not a ranked dataset.** Use to create private, non-public cases after the public benchmark is stable.

**Why RCAEval ranks above SWE-bench for BLACKBOX's first real evaluation:** BLACKBOX's differentiator is not issue-to-patch generation; it is evidence-based diagnosis. RCAEval tests whether the system can use runtime evidence to locate a faulty service and indicator. SWE-bench tests whether a system can produce a patch that passes tests, which is a different capability and is already well served by existing coding agents. Ranking SWE-bench first would optimize for a capability BLACKBOX does not uniquely claim.

**Why RCAEval is not sufficient by itself:** its labels do not prove source-line causation, and it has no repair tests. A system could score well by learning service/fault correlations without understanding code. That is exactly the kind of shortcut a BLACKBOX benchmark must expose, so pair every RCAEval score with a source-grounded subset and negative controls.

---

## 5. Proposed BLACKBOX Diagnostic Benchmark (BDB)

### 5.1 Design principles

1. **Diagnosis and repair are separate tracks.** A diagnosis score cannot be rescued by a passing patch, and a patch cannot prove the diagnosis.
2. **Evidence is packaged, not dumped.** Every case has an allowlisted evidence package with explicit IDs, types, timestamps, revisions, and hashes. The investigator sees only that package.
3. **Ground truth is in a label vault.** Labels, gold patches, test patches, and intended fixes are never in the repository snapshot, retrieval corpus, prompt, or model-visible working directory.
4. **Every case is reproducible and negative-controlled.** The harness must show the failure before a patch and the expected result after; at least one negative or unanswerable control accompanies each batch.
5. **The benchmark must be able to mark BLACKBOX wrong.** Cases include ambiguous provenance, missing contracts, false reports, and service-level labels that do not identify a line. Unsupported confidence is a scored failure, not a tie.
6. **Freeze before inference.** Case files, prompts, model digest, context, and scoring rubric are hashed before the first call. No case is edited in response to a result.
7. **Do not claim implementation.** This document designs BDB; it does not create fixtures, run models, or establish accuracy.

### 5.2 Stage 1 — controlled synthetic reasoning probes

**Purpose:** isolate individual reasoning capabilities, not realism.

**Cases:** 12–20 deterministic micro-cases, separate from the headline 25/50/100 count. Retain the existing six cases as smoke tests but do not reuse them as evidence of generalization.

**Coverage:** static source fact vs runtime claim; stack-frame provenance and revision pinning; documented contract vs invented contract; possible mechanism vs established cause; a misleading or hostile source comment; a false client report that contradicts the code; a true symptom with multiple plausible mechanisms; a correct abstention when the input value is unavailable; an unsupported causal assertion that must be penalized; a case where the immediate frame is visible but the upstream caller is not.

**Ground truth:** authored, reviewed, and frozen; labels include the acceptable mechanism(s), the acceptable causal status, and the acceptable abstention reason.

**What it can prove:** the harness detects citation errors, contract invention, execution overclaiming, and false certainty. **What it cannot prove:** realism, repository-scale retrieval, or production reliability.

### 5.3 Stage 2 — realistic failure scenarios (telemetry-first)

**Purpose:** test diagnosis from realistic, multi-source observations without giving the model the answer through source/test artifacts.

**Source:** RCAEval RE3, plus a small number of locally authored multi-file scenarios that include a behavioral contract and an actual reproduction.

**Case shape:** 3–8 interacting files or services; logs, metrics, and traces; a recorded error event; a time window; a deployment revision; a behavioral contract or an explicit "no contract supplied" marker.

**First batch:** 10 cases at the 25-case milestone; 20 at 50; 40 at 100. Stratify by fault class, system, and evidence availability. Keep a held-out system entirely out of prompt development.

**RCAEval adapter:** hide `root_cause_service`, `fault`, directory names, and `root_cause.txt`. Give the model the telemetry window and the event description. Ask for a ranked set of services and root-cause indicators plus a mechanism hypothesis and an explicit causal status. Score at the label level the dataset actually supports: service/indicator. Do not award line-level causal credit unless the case has a verified line label.

**Local multi-file cases:** include a real failing test, an approved contract, and source at a pinned revision. Hide the fix. The model may inspect only allowlisted source and telemetry. This is the bridge between RCAEval's service labels and BLACKBOX's source-level claims.

**What it can prove:** whether the system can localize a faulty service/indicator, avoid unsupported causal claims, and use contracts correctly under realistic noise. **What it cannot prove:** repair correctness, production causality, or generalization beyond the selected systems.

### 5.4 Stage 3 — repository-level investigations

**Purpose:** test whether the system can investigate a real codebase at a recorded revision, not just a small fixture.

**Sources:** BugSwarm artifacts and SWE-bench base commits, with a preference for BugSwarm when a real CI log is needed and SWE-bench when a clean issue statement and FAIL_TO_PASS tests are needed.

**Case shape:** one repository per case; base commit; issue or CI failure record; build/test command; full source tree (or a bounded, hash-pinned subset); logs/stack traces; no gold patch; no test patch; no post-fix commit messages.

**First batch:** 8 cases at 25; 18 at 50; 35 at 100. At least 30% must be negative/ambiguous controls where the report is insufficient or the repository does not contain the claimed cause.

**Evidence policy:** the agent may request files/symbols through a trusted retriever. Every returned excerpt carries a blob hash, commit, and path. Requests outside the repository or outside the allowlist fail closed.

**What it can prove:** repository-scale retrieval, cross-file reasoning, build/test navigation, and resistance to irrelevant code. **What it cannot prove:** production causality, because the issue/CI record is still a report and the fix commit is still a patch, not an independently verified causal chain.

### 5.5 Stage 4 — verified repair

**Purpose:** test the full claim "failure before patch, patch applied, failure no longer reproduced, regressions still pass" without confusing test passage with semantic correctness.

**Sources:** BugSwarm fail/pass artifacts first; SWE-bench Verified second; BugsInPy only after licensing is resolved.

**Case shape:** pinned buggy revision; reproduction command; observed failure signature; hidden regression set; patch application in a disposable container; pre/post execution; test-file integrity check; no network.

**First batch:** 7 cases at 25; 12 at 50; 25 at 100. Include at least two cases where the obvious patch passes the reproduction but fails a hidden regression, and two where the reproduction is flaky and must be repeated.

**Required evidence:** the original failure occurs before the patch; the patch applies cleanly to the pinned revision; the same failure no longer occurs; the designated regression tests pass; test files were not modified; the patch is within allowed files and size; the result is reproducible at least three times, or explicitly marked flaky.

**What it can prove:** test-verified repair under a controlled environment. **What it cannot prove:** that the patch is the best fix, that the diagnosis was correct, that hidden production behavior is safe, or that the tests are adequate.

### 5.6 Case-count matrix

| Milestone | Stage 2 telemetry | Stage 3 repository | Stage 4 repair | Total scored | Stage 1 calibration |
|---|---:|---:|---:|---:|---:|
| BDB-25 | 10 | 8 | 7 | 25 | 12–20 (separate) |
| BDB-50 | 20 | 18 | 12 | 50 | 12–20 (separate) |
| BDB-100 | 40 | 35 | 25 | 100 | 20–30 (separate) |

The totals are deliberately not "100 diagnosis cases." They cover different capabilities. A single aggregate "BDB score" would be misleading and is prohibited.

### 5.7 Recommended first experiment

Run **BDB-25** with 10 RCAEval RE3 cases (stratified across systems and fault classes where possible), 8 repository cases (4 BugSwarm, 4 SWE-bench, with negative controls), 7 repair cases (4 BugSwarm, 3 SWE-bench), and 12 Stage 1 probes as a harness gate, not a headline result. Use a frozen label vault, a frozen prompt, and one local model configuration.

Run it once as a **pilot**, then repeat the same frozen cases three times to measure output variability. Do not tune the prompt on the scored cases and report the tuned result as generalization. If the pilot reveals a harness bug, version the benchmark and disclose the change.

---

## 6. Scoring framework

### 6.1 Dimension-specific scoring

Do not combine these into one accuracy percentage. Each case produces a vector; report distributions and confidence intervals, not a single leaderboard number.

| Dimension | Question | Evidence allowed | Scoring |
|---|---|---|---|
| Runtime observation fidelity | Did the system report what the event/log/trace actually says, without treating it as authenticated execution? | Event record, logs, traces, metrics | correct / partly correct / incorrect / unsupported / N/A |
| Static code fact accuracy | Are source claims true at the pinned revision? | Pinned blobs with hashes | claim-level correct/incorrect/unsupported |
| Contract interpretation | Did it use only supplied approved requirements and recognize absent contracts? | Documentation records only | correct / overbroad / invented / N/A |
| Mechanism hypothesis quality | Could the cited code produce the symptom under the stated condition? | Source + explicit hypothetical trigger | supported / partly supported / incompatible / unsupported |
| Causal attribution | Did the evidence establish that this mechanism caused this incident? | Authenticated runtime linkage, counterfactual reproduction | ESTABLISHED / SUPPORTED / NOT_ESTABLISHED / CONTRADICTED / NO_CLAIM |
| Correct abstention | Did it name the missing evidence and refrain from asserting the unresolved point? | Case answer key | correct / vague / incorrect / unsupported |
| Unsupported claims | Did it assert execution, input, contract, mechanism, or cause without support? | Claim-level audit | count by type; materiality |
| Evidence provenance | Do cited IDs exist, have the right type, and point to the right revision/hash? | Evidence manifest | valid / mixed / invalid / fabricated |
| Patch correctness | Does the patch apply, fix the reproduction, and preserve behavior? | Reproduction + hidden tests + review | verified / partial / failed / rejected |
| Regression safety | Do PASS_TO_PASS and hidden tests still pass, without test edits? | Clean test run | pass / fail / flaky / not run |
| Operational cost | Latency, tokens, tool calls, container time | Harness telemetry | raw values, not a quality score |

### 6.2 Causal attribution levels

Use an explicit level so a service label is not mistaken for a line-level cause:

- **L0 — no attribution:** evidence does not identify a component.
- **L1 — service/component:** the faulty service or module is identified.
- **L2 — file/function/line:** the specific code location is identified.
- **L3 — trigger/condition:** the input, configuration, timing, or environmental condition that activated the defect is identified.
- **L4 — counterfactual confirmation:** reverting or changing the identified cause in a controlled reproduction removes the incident, and restoring it recreates the incident.

RCAEval mostly supports **L1**, with partial L2/L3 evidence in stack traces. SWE-bench and BugSwarm support patch verification but not L4 causal confirmation. A system that says "checkoutservice" on an RCAEval case may be correct at L1 and still wrong about the line, mechanism, or trigger. Report the level.

### 6.3 Why a correct mechanism hypothesis is not the incident's actual cause

A mechanism is a **conditional statement about code**: "if `values` is empty, this function raises `IndexError`." The incident cause is a **historical statement about this event**: "this request supplied an empty list because the upstream cache returned `[]` after a miss, and that path executed at 14:32:07." The first can be true while the second is false.

At least five things can break the inference: (1) multiple mechanisms produce the same symptom; (2) the code may not have executed; (3) the input/condition may be unknown; (4) the deployed revision may differ; (5) the causal chain may be upstream. A benchmark that rewards "the code could fail this way" as "root cause" will overcredit plausible storytelling. BDB therefore scores mechanism and causal attribution separately.

### 6.4 Reporting rules

- Report per-dimension results, per-stage results, and per-case appendices.
- Report **claim-level precision** for factual/causal claims, not just case-level pass/fail.
- Report **abstention rate** on unanswerable cases and **false-confidence rate** on answerable cases separately.
- Report **unsupported-claim counts by type** (execution, input, contract, mechanism, cause).
- Report **patch verification** only for cases that reached Stage 4, with attempts and flaky reruns.
- Report latency/tokens/cost separately; never trade them into a quality score.
- Include confidence intervals and cluster by repository/system. Cases from the same repository are not independent.
- Publish negative results and harness failures. A skipped case is not a pass.

### 6.5 Suggested headline table (illustrative, not results)

| Capability | BDB-25 report | BDB-100 report |
|---|---|---|
| L1 service/indicator top-1 | count / n, Wilson CI | stratified by system/fault |
| L2 line/function accuracy | count / n, only cases with line labels | + per-language |
| Causal status accuracy | confusion matrix by level | + calibration by evidence sufficiency |
| Justified abstention | count / unanswerable | + false-abstention on answerable |
| Unsupported claims | count per 100 claims, by type | trend across stages |
| Repair verified | count / attempted, with failures listed | + hidden-regression failures |
| Regression safety | pass/fail/flaky counts | + test-integrity audit |

No row is combined into "BLACKBOX is X% accurate."

---

## 7. Data quality and leakage prevention

### 7.1 Required metadata per case

Every case must have a machine-readable record with at least:

| Field | Requirement |
|---|---|
| `case_id` | Opaque, stable, non-semantic; never encodes the answer |
| `benchmark_version` | SemVer plus content hash |
| `repository_url` | Canonical source URL |
| `base_commit` | Exact 40-character revision for the buggy state |
| `fixed_commit` | Optional; never shown to the investigator |
| `environment` | OS, runtime version, dependency lock, container digest, CPU/memory limits |
| `error_event` | Type, message, stack frames, timestamp, source (client report vs telemetry) |
| `logs` | Schema, time window, source, row count, hash |
| `traces` | Schema, time window, service/span mapping, hash |
| `metrics` | Schema, time window, metric names, hash |
| `source_files` | Paths, blob hashes, language, line ranges |
| `behavioral_contract` | Approved document path/hash, or explicit `NONE_SUPPLIED` |
| `reproduction_command` | Exact command, working directory, timeout, network policy |
| `expected_before` | Failure signature and exit status |
| `expected_after` | Pass signature and regression result |
| `ground_truth` | L0–L4 level, service, file/line if known, trigger, mechanism, confidence, rationale |
| `acceptable_abstention` | Whether abstention is correct, and which missing evidence must be named |
| `patch_verification` | Allowed files, test command, hidden regression set, flake policy |
| `label_author` | Author/reviewer IDs and adjudication record |
| `license` | Dataset and upstream code licenses |
| `privacy` | PII/secret review status and redaction notes |
| `known_flakiness` | Reproduction attempts/successes, known nondeterminism |

### 7.2 Quality gates

A case is admissible only if:

1. The buggy revision is exact and the source hash matches.
2. The failure reproduces at least three times, or is explicitly labeled flaky.
3. The fixed/reference behavior passes the designated tests.
4. The reproduction does not require network access or unrecorded credentials.
5. The test files are hash-pinned and cannot be edited by the patch.
6. The ground-truth label has a written rationale and, for L2+, a source/test citation.
7. At least one person other than the case author reviews the label and reproduction.
8. The case has a negative, ambiguous, or unanswerable control where appropriate.
9. The license permits the intended use; otherwise the case is excluded.
10. The evidence package contains no gold patch, test patch, fix commit message, or answer-bearing filename.

### 7.3 Leakage prevention

**Ground truth isolation.** Labels live outside the repository snapshot and outside the model-visible filesystem. The prompt builder reads only an allowlisted evidence manifest. The scorer runs in a separate process with a separate label store.

**Prompt allowlist.** The prompt may include only: event record, telemetry excerpts, source excerpts with hashes, approved contract documents, and tool descriptions. It must exclude: `patch`, `test_patch`, `FAIL_TO_PASS`/`PASS_TO_PASS`, `fixed_commit`, PR comments after the fix, commit messages, changelogs, issue comments that state the fix, file names containing `buggy`, `fixed`, `gold`, or the answer, and the label rationale.

**Repository isolation.** Use a shallow checkout at `base_commit`; remove `.git` history after that commit; deny access to branches/tags containing the fix; deny network access during investigation and testing. Opaque case IDs and neutral working directories prevent path-name hints.

**Public vs held-out.** Split by repository/system and time, not by random row. A random split leaks near-duplicate issues and style. Keep a private held-out set that is never used for prompt development, threshold selection, or example selection. Freeze it before evaluation.

**Contamination.** Public benchmarks are likely present in training data. Do not claim a model "generalizes" from SWE-bench or RCAEval alone. Mitigations: newly mined post-cutoff cases, private repositories, renamed/perturbed cases, canary strings, and reporting that contamination cannot be ruled out. A canary is a detection aid, not proof of cleanliness.

**Test integrity.** For repair, apply the patch to a clean base, verify test-file hashes, run FAIL_TO_PASS and PASS_TO_PASS, and add hidden regression tests that the investigator never sees. If the patch edits tests or the harness, reject it.

**Evaluator independence.** The person who authored the case should not be the only scorer. At least 20% of cases should be double-scored, with disagreements adjudicated. Publish inter-rater agreement.

**No external telemetry.** Do not send raw LogHub/BugSwarm/RCAEval telemetry to a hosted model. Redact secrets and PII first; prefer local inference for the pilot.

---

## 8. Roadmap from six cases to 25, 50, 100, and beyond

### 8.1 BDB-25 (pilot)

**Composition:** 10 Stage 2 + 8 Stage 3 + 7 Stage 4; 12 Stage 1 probes as a harness gate.

**What can be assessed:** whether the harness works; whether the model can separate mechanism from cause; whether it invents contracts; whether it can localize a service/indicator; whether a patch can be verified; where the first systematic failures occur.

**What cannot be assessed:** stable accuracy, per-language performance, production reliability, or superiority over another model. With 25 cases, a 95% Wilson interval around an observed 80% is roughly 61–91% (illustrative, assuming independence; repository clustering widens it).

**Exit criteria:** all cases reproduce; zero label leakage; every failure is attributable to the model or a documented harness limitation; at least one negative control behaves correctly.

### 8.2 BDB-50

**Composition:** 20 Stage 2 + 18 Stage 3 + 12 Stage 4.

**What can be assessed:** coarse per-dimension rates with intervals; whether failures cluster by evidence type (missing contract, no runtime input, retrieval miss); whether repair failures are patch-quality or test-quality; whether prompt changes generalize beyond the pilot.

**What cannot be assessed:** fine-grained subgroup claims (for example, "Go concurrency is 20 points worse"), production reliability, or leaderboard-style ranking. An observed 80% at n=50 has an approximate 95% interval of 67–89%.

**Exit criteria:** at least 20% double-scored; contamination audit completed; license review completed for every source; hidden regression tests added to repair cases.

### 8.3 BDB-100

**Composition:** 40 Stage 2 + 35 Stage 3 + 25 Stage 4.

**What can be assessed:** coarse subgroup differences by language, fault class, and evidence availability; calibration of causal confidence; stability across three repeats; cost per verified diagnosis/repair. An observed 80% at n=100 has an approximate 95% interval of 71–87%.

**What cannot be assessed:** production-level reliability, rare-failure performance, or claims that 100 examples represent all software systems. A 100-case benchmark can expose systematic errors; it cannot certify a product.

**Exit criteria:** private held-out set frozen; no prompt tuning on test; per-case provenance published; failure taxonomy stable; independent adjudication for at least 30%.

### 8.4 Larger held-out evaluation

**Target:** 300–500+ cases, with a private test set and a public development set. Include multiple languages, repositories, deployment styles, and failure classes. Maintain a rolling "fresh" set mined after the model's training cutoff.

**What can be assessed:** per-dimension estimates with useful precision; drift over time; regression after model/prompt changes; subgroup performance with adequate samples. An observed 80% at n=500 has an approximate 95% interval of 76–83%, still not a production guarantee.

**What still cannot be assessed:** behavior on the user's actual systems, unknown failure modes, adversarial production conditions, or long-term reliability. Those require field telemetry, incident review, and operational monitoring—not a static benchmark.

### 8.5 Stage gates

Do not advance on a single aggregate score. Advance only when the harness reproduces every case and reports failures honestly; labels are independently reviewed; leakage tests pass; the failure taxonomy is stable; and the next stage adds a capability the previous stage could not test. If BDB-25 shows that most errors are label/harness artifacts, fix the benchmark before adding cases. More cases do not fix bad labels.

---

## 9. Risks and limitations

1. **Label validity.** RCAEval labels are service/fault-level, not full causal chains. SWE-bench/BugSwarm labels are patches/tests, not causes. Treating either as causal ground truth would overcredit BLACKBOX.
2. **Synthetic injection artifacts.** RCAEval and AIOpsLab inject faults; injected faults may be cleaner and more separable than production incidents.
3. **Test overfitting and false negatives.** OpenAI's audit found flawed tests that reject correct solutions. A patch that fails tests is not automatically wrong; a patch that passes is not automatically correct.
4. **Flakiness and decay.** BugSwarm retains 528 flaky artifacts; BugsInPy's historical reproduction was 67%; old dependencies break. Reproduce before scoring.
5. **Licensing.** BugsInPy has no license; LogHub's terms conflict; SWE-bench's data license is undeclared; upstream repositories vary. Legal review is part of benchmark construction.
6. **Privacy.** LogHub logs are often unsanitized. RCAEval/BugSwarm/SWE-bench data may contain paths, tokens, or personal data. Never send raw telemetry externally.
7. **Contamination.** Public benchmarks are likely in training data. A high score may measure familiarity, not diagnosis.
8. **Benchmark overfitting.** Once a benchmark is public and used for tuning, it stops being a clean test. Keep a private holdout and refresh cases.
9. **Small samples and clustering.** Cases from one repository/system are correlated. Wilson intervals assuming independence are optimistic; use cluster-aware analysis.
10. **Scorer bias.** The case author may unconsciously accept the intended answer. Use blinded scoring and adjudication.
11. **Missing source/telemetry linkage.** RCAEval has no source snapshot; BugSwarm has no metrics/traces; SWE-bench has no runtime incident. No single source provides the full causal package.
12. **Model context and cost.** Repository-scale cases may exceed a 2,048-token context; retrieval and truncation can hide the causal file. Report retrieval misses separately from reasoning errors.
13. **Patch correctness is not semantic correctness.** A patch can pass the visible tests and still be wrong. Stage 4 must include hidden regressions and human review.
14. **Operational cost.** AIOpsLab/Kubernetes and Docker images are expensive; the benchmark must report cost and not silently drop hard cases.
15. **Commercial restrictions.** Some datasets are research-only or unlicensed. A benchmark that cannot be used commercially has limited product value.
16. **No production causality.** Even a perfect BDB score does not prove that BLACKBOX will find the cause of a customer's incident.
17. **Single-model risk.** Results from `qwen3.5:4b` at 2,048 context do not generalize to larger models or other providers.
18. **False confidence.** A system that always says `LIKELY_CAUSE` can look good on answerable cases while being dangerous on ambiguous ones. Score abstention and unsupported claims separately.
19. **Benchmark gaming.** If the score is public, systems may learn shortcuts (service names, file names, test names). Opaque IDs and held-out cases reduce this.
20. **Implementation gap.** This document is a design. No BDB case, harness, label, or result exists yet.

---

## 10. Beginner-friendly explanation

Imagine a hospital. A patient arrives with a fever and a cough. The **event** is what the patient reports. **Logs** are the vital-sign monitor. **Traces** show how the patient moved through the hospital. **Source code** is the anatomy. A **behavioral contract** is the discharge instruction that says what "healthy" means. A **reproduction** is a controlled test that makes the symptom happen on purpose.

A **mechanism** is "this broken valve could cause a fever." The **cause** is "this patient's valve is broken, and that is why the fever started at 2 a.m." The first is a possibility; the second is a historical fact. A doctor who lists every possible valve problem has not diagnosed the patient. A benchmark that gives credit for the list is measuring storytelling, not diagnosis.

Public datasets usually label only part of the story. RCAEval says "the checkout service had a code-level fault." That is like saying "the heart had a problem." It does not say which artery, which blockage, or what the patient ate. SWE-bench says "this patch makes the tests pass." That is like saying "the patient feels better after this pill." It does not prove the pill treated the cause.

The staged benchmark is like a driving test:

- **Stage 1** is the cone course: can the system cite source, respect a contract, and say "I don't know"?
- **Stage 2** is city driving: noisy telemetry, multiple services, missing inputs.
- **Stage 3** is the highway: a real repository, many files, a real issue or CI failure.
- **Stage 4** is the repair shop: make the failure happen, apply a patch, prove it is gone, and prove nothing else broke.

Twenty-five cases are like twenty-five patients. They can reveal that the thermometer is broken or that the doctor always guesses "heart." They cannot prove the hospital is safe. One hundred cases give a better estimate, but the hospital still needs real-world follow-up.

The most important rule is simple: **do not reward confidence.** Reward claims that cite the right evidence, at the right revision, with the right scope—and reward a clear "the evidence does not establish this" when that is the truth.

---

## 11. Final Git status comparison

**Before writing this document:** `git status --porcelain` reported **452 entries**. The working tree already contained 19 tracked modifications (including `.env.example`, `EVALUATION.md`, `README.md`, `blackbox/investigator.py`, repair modules, and `tests/test_repair.py`) plus untracked source, fixtures, data, and graphify cache files. These were pre-existing and were not created, reverted, staged, or cleaned by this research task.

**After writing this document:** the only intentional addition is `?? research/63_BLACKBOX_DIAGNOSTIC_BENCHMARK_LANDSCAPE.md`. The final verification compares the sorted before/after status lists. Expected result: exactly one added line, zero removed lines, and no change to any tracked file. The document itself is untracked because the repository's existing research documents 29–61 are also untracked in this working tree.

**No source code, tests, fixtures, labels, preregistration, Documents 56–57, Documents 50–62, M4B.3 artifacts, or graph files were modified.** No dataset was downloaded, no model inference was run, no Docker/repair command was executed, and no external telemetry was sent anywhere.

---

## 12. Sources and research method

All sources were accessed on **2026-11-07**. Facts were taken from official repositories, dataset cards, license files, papers, or project documentation. Secondary sources were used only where noted, and uncertain values are marked.

**RCAEval**

- Repository: https://github.com/phamquiluan/RCAEval
- Dataset: https://huggingface.co/datasets/phamquiluan/RCAEval
- Paper: https://arxiv.org/abs/2412.17015 (WWW '25 Companion, pp. 777–780)
- ACM record: https://dl.acm.org/doi/10.1145/3701716.3715290
- PyPI/license notes: https://pypi.org/project/RCAEval/

**AIOpsLab**

- Repository: https://github.com/microsoft/AIOpsLab
- Project site: https://microsoft.github.io/AIOpsLab/
- MLSys 2025 record: https://proceedings.mlsys.org/paper_files/paper/2025/hash/d1f9e4a9f109b6e8b75ed362736f22ec-Abstract-Conference.html

**SWE-bench**

- Repository: https://github.com/SWE-bench/SWE-bench
- Verified dataset: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified
- ICLR 2024 record: https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html
- Paper: https://arxiv.org/abs/2310.06770
- OpenAI critique: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/

**BugSwarm**

- Repository: https://github.com/BugSwarm/bugswarm
- Dataset site: https://www.bugswarm.org/
- Releases: https://www.bugswarm.org/releases
- Statistics: https://www.bugswarm.org/statistics/
- Paper: https://arxiv.org/abs/1903.06725 (ICSE 2019)

**LogHub**

- Repository: https://github.com/logpai/loghub
- Zenodo v8: https://zenodo.org/records/8196385
- Paper: https://arxiv.org/abs/2008.06448 (ISSRE 2023)

**BugsInPy**

- Repository: https://github.com/soarsmu/BugsInPy
- Paper: https://arxiv.org/abs/2401.15481 (ESEC/FSE 2020 tool demo)
- License issue: https://github.com/soarsmu/BugsInPy/issues/94
- Independent reproduction study: https://conferences.computer.org/icsmepub/pdfs/SCAM2023-ZPjMN85ZMA4HQwAsawf3H/050600a260/050600a260.pdf

**Defects4J**

- Repository: https://github.com/rjust/defects4j
- Project site: https://defects4j.org/
- Paper: https://dl.acm.org/doi/10.1145/2610384.2628055 (ISSTA 2014)

**QuixBugs**

- Repository: https://github.com/jkoppel/QuixBugs
- Project page: https://jkoppel.github.io/QuixBugs
- Paper: https://dl.acm.org/doi/10.1145/3135932.3135941 (SPLASH Companion 2017)

**OpenTelemetry Demo**

- Repository: https://github.com/open-telemetry/opentelemetry-demo
- Architecture: https://opentelemetry.io/docs/demo/architecture/
- Feature flags: https://opentelemetry.io/docs/demo/feature-flags/

**Local BLACKBOX context**

- `research/49_M4B2_ORACLE_CONTEXT_DIAGNOSTIC.md`: oracle context changed 0/6 outcomes.
- `EVALUATION.md`: M4B.3 recorded as offline preparation with no live calls in this checkout.
- `research/32_M3C_COMPLEX_DEBUGGING_EVALUATION.md`: five locally authored cases, 2/3 immediate causes, 1/2 verified repair, no independent adjudication.
- `research/27_M3A_PROOF_OF_FIX.md`: three verified repairs on trusted fixtures, process-jail isolation, no production claim.

**Method note.** Dataset sizes, labels, and license statements were checked against the official source listed. Where the official pages conflicted (SWE-bench Lite count, LogHub license, AIOpsLab problem count), the conflict is reported rather than resolved by guesswork. No dataset was downloaded or executed, so counts that would require enumerating a live registry are marked uncertain. The ranking is an analyst judgment about BLACKBOX suitability, not a claim that any dataset has been integrated.
