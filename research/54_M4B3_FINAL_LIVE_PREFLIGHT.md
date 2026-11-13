# M4B.3 final live-execution preflight — no inference

## Decision

**BLOCKED**

This report is a metadata and offline preflight only. No investigator inference request was made. No fixture, Docker, or repair workflow was executed. The experiment is not authorized or started.

The blocking integrity finding is that the current working copy of the original preregistration, `research/50_M4B3_EVIDENCE_LAYERED_REASONING.md`, is not text-identical to that file's blob at the registered revision. It contains substantive additions and replacements, and no separate amendment authorizing those changes was established by this preflight. The frozen source revision and registered fixture blobs themselves verify correctly. Do not treat a passing runner check as evidence that the preregistration remained unchanged.

## 1. Experiment integrity

The runner pins `PINNED_REV` to `13bdc52bad27c49b77e85daac16876133f382009`, verifies that exact commit, and reads registry, labels, source, and documentation from Git blobs at that commit. It does not resolve `refs/blackbox/m4b3-freeze`. The current mutable ref remains a later descendant; this does not change the runner's pinned revision.

The working preregistration has SHA-256 `829557b33f39017a328c828ca3b8e9f6af1d4b334be8c294f11b61e43200bccd`. The preregistration blob at the pinned commit has SHA-256 `9a8327523165eeec73f004585114c062b193a7a77744a242c0e26d55826d5a7e`. A line comparison also differs (92 working-copy lines versus 61 pinned-blob lines); this is not just a line-ending difference. Differences include changes to the A/B post-processing description, a new cross-pair explanation, replacement of the frozen-set identity placeholder with populated details, added scoring and beginner/runbook sections, and replacement of placeholder results/decision text. The history and approval for these edits are not established here. The original file was not changed during this preflight.

The exact frozen case order from the pinned registry is:

1. `m4b3_contract_mean`
2. `m4b3_unrecorded_input`
3. `m4b3_static_reachability`
4. `m4b3_undocumented_contract`
5. `m4b3_hostile_comment`
6. `m4b3_negative_report`

The runner's counterbalanced schedule matches `research/53_M4B3_ARM_ORDER_CORRECTION.md` and is checked against this registry order. Both dry-run display and live execution use the one ordered plan from `plan()`.

The scorer-only label blob is read only to compute a SHA-256 recorded in the plan. It is not inserted into the evidence snapshot or model-facing context. Offline tests check for label leakage. All four arms for each case share one evidence-package hash; this was confirmed by the dry-run and focused tests.

### Frozen source SHA-256 checks

These hashes were calculated from blobs read directly from the pinned commit and compared with the hashes in that commit's frozen registry. The fixture files in the working tree also matched those pinned blobs.

| Pinned source path | SHA-256 | Registry match |
|---|---|---|
| `fixtures/repair/m4b3/contracted_mean/app.py` | `f95dda74cbd05dada9f99ae1bd9ed189e9fc9d9223c401b17af7dc542fe4cfdd` | Yes |
| `fixtures/repair/m4b3/contracted_mean/REQUIREMENTS.md` | `0b73ec92b3904713af42852ee1b702d1d374ad975d32158528a779d95d83d48b` | Yes |
| `fixtures/repair/m4b3/unrecorded_input/app.py` | `51e95104c79b15bba0b865b3488c6250a576150ee763d8facfdfd57fe56d0d4c` | Yes |
| `fixtures/repair/m4b3/static_reachability/app.py` | `45b8322435a326e67f8889ef0daec157c2069e20098b9c758d25eb061a473264` | Yes |
| `fixtures/repair/m4b3/undocumented_contract/app.py` | `e92aa3146d09407d97a3550b9e203aca39f4df30830d659adb62d59817bdbff4` | Yes |
| `fixtures/repair/m4b3/hostile_comment/app.py` | `bb410558980e421b4f4324293ca65efed2b295c3f456b9c409e09035a7604d1a` | Yes |
| `fixtures/repair/m4b3/negative_report/app.py` | `90b4bcb48c2367f1f0ce299b0f18a6e22fdd5f0aec6848ef6205604fdcadb276` | Yes |

All seven Git entries have regular file mode `100644`. The pinned scorer-label blob SHA-256 is `321a372952665891a7111cb82c91b23156f1e89c010bf7611ee98b1dea66c714`; it matches the provenance audit and the current working-tree label file. The pinned registry's case list and registered source hash map were used; the runner does not rely on the mutable ref's registry metadata.

## 2. Local Ollama metadata — no inference

The following metadata-only checks were made against the local daemon: `ollama --version`, `GET /api/tags`, `GET /api/ps`, and `POST /api/show` for `qwen3.5:4b`. No `/api/generate` or `/api/chat` request was made.

- Ollama version: `ollama version is 0.40.14`.
- Required installed tag: exactly one `qwen3.5:4b` entry.
- Full installed digest: `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`.
- Required digest prefix `d8b0f5e9760c`: **matches**.
- Local daemon reachable: **yes**.
- `/api/ps` running-model list at check time: empty (`{"models":[]}`); no model was reported as loaded/running then. This is a point-in-time status check, not a guarantee about future daemon activity.
- Other tags are installed (`qwen3.5:9b-q4_K_M` and `qwen3:4b`), but the runner explicitly constructs `Provider('ollama', 'qwen3.5:4b')` and has no automatic provider/model fallback.

The runner does not enforce a particular Ollama version; therefore 0.40.14 is recorded without treating it as a mismatch. The Ollama model metadata lists a default temperature of 1, but the actual request explicitly sends temperature 0.

## 3. Inference configuration

Inspection of `scripts/evaluate_m4b3.py` and `blackbox/providers.py` establishes the following configured request values:

| Setting | Required | Runner/provider behavior | Result |
|---|---:|---|---|
| Model | `qwen3.5:4b` | Fixed `MODEL`, passed to Ollama provider | Match |
| Context | 2,048 | Runner sets `BLACKBOX_OLLAMA_CONTEXT_LENGTH=2048`; request sends `num_ctx` | Match |
| Temperature | 0 | Request sends `options.temperature=0` | Match |
| Thinking | Disabled | Request sends `think: false` | Match |
| Output cap | 768 | Each call passes 768; provider computes `min(768, available)` | Match; all 24 planned prompts calculate to 768 |
| Request timeout | 60 seconds | Runner sets timeout environment value to 60; Ollama HTTP request uses it | Match |
| Retries | 0 | Ollama branch makes one `httpx.post`; no retry loop or retry adapter is configured | Match |
| Maximum evaluations | 24 | Pinned plan has six cases × four arms; main executes that plan once | Match |

All four arms use the same model, fixed context, temperature, thinking setting, timeout, and output ceiling. The current-versus-layered prompt and schema differ only as the registered factorial design specifies. The calculated provider output budget is 768 for every planned arm, so the prompt-length safeguard does not lower the cap in this plan.

## 4. Execution and persistence safety

- The CLI requires exactly one of `--dry-run` or `--run-live`. This preflight used only `--dry-run`.
- The live entry point creates one pinned 24-item plan and passes it once to `execute()`. The loop makes one provider call per item; there is no automatic retry or loop that replays completed entries.
- Each result is associated with case, arm, revision, evidence hash, prompt/schema fingerprints, and scorer-label hash. Parsed output and validation status are recorded; usage and latency are recorded. Evidence IDs appear inside parsed raw/validated model output when available; there is no separate persisted copy of the complete input evidence-ID inventory.
- After each handled response, the runner writes a `partial` results document. Provider/parse/validation exceptions are recorded as invalid results and the loop continues. Only the outer run writes `complete` or `complete_with_failures` after all 24 planned entries. A normal interrupted run therefore remains `partial`, rather than appearing complete.
- A new run requires the results file to be `template_only_no_model_calls`, have an empty results list, and match the pinned revision. Partial or completed results fail this check; a fresh run cannot silently overwrite them.
- The configured provider is explicitly Ollama; there is no fallback to Gemini, another tag, or another provider.
- A narrow interruption window remains: if the process or host stops after Ollama has completed a response but before that response is checkpointed, that one response may not be present in the results file. The Ollama daemon is outside the evaluator process and cancellation is not guaranteed. No automatic retry is implemented, but the harness cannot prove exactly-once behavior across that crash window. This and best-effort redaction limitations remain documented in the prior audit.

No call to the live entry point was made. The point-in-time `/api/ps` result was empty.

## 5. Offline verification

`python -m pytest -q tests/test_m4b3_harness.py` → **18 passed**.

`python scripts/evaluate_m4b3.py --dry-run` reported:

- Revision `13bdc52bad27c49b77e85daac16876133f382009`.
- Six frozen cases, four arms, 24 planned evaluations.
- Zero model calls.
- The corrected schedule:

| Case | Order |
|---|---|
| `m4b3_contract_mean` | A, B, C, D |
| `m4b3_unrecorded_input` | B, C, D, A |
| `m4b3_static_reachability` | C, D, A, B |
| `m4b3_undocumented_contract` | D, A, B, C |
| `m4b3_hostile_comment` | A, C, D, B |
| `m4b3_negative_report` | B, D, A, C |

All arms within each case had the same evidence hash. `data/m4b3-results.json` remains `template_only_no_model_calls`, revision `13bdc52bad27c49b77e85daac16876133f382009`, and `results: []`.

The full repair suite was not run, per instruction.

## 6. Unresolved issue and final decision

The registered source and scorer-label blobs, runner pin, local model digest, configured inference settings, corrected schedule, focused tests, and dry-run all pass. The integrity requirement that the original preregistration remain unchanged does not pass: current `research/50` differs substantially from its pinned-commit blob, and this preflight did not find an approved amendment authorizing those differences. The runner also has a limited response-before-checkpoint interruption window, so exactly-once completion cannot be guaranteed across abrupt process termination.

**BLOCKED**

No inference has been performed. This status is not authorization to execute the experiment.
