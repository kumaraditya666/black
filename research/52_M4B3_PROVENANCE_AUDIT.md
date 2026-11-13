# M4B.3 frozen revision provenance audit and harness correction

## Revision identities

The preregistered source revision is `13bdc52bad27c49b77e85daac16876133f382009` (2026-11-07 00:06:38 +05:30, “Freeze M4B.3 layered reasoning cases and harness”, parent `b96840fef85585904c9348e213dbbec9c0ca521a`). Its descendant `9b5d444209a92776ee9e2fd2063135518d3c921a` was created at 00:10:57 +05:30 with message “Finalize M4B.3 frozen registry ref” and parent `13bdc52bad27c49b77e85daac16876133f382009`.

Both commits exist; `13bdc52` is an ancestor of `9b5d444`. The conversation command history records that `refs/blackbox/m4b3-freeze` was first set to `13bdc52` and later updated to `9b5d444`. The current ref resolves to `9b5d444`. No reflog entry for this custom ref was available. The later commit changes only a registry metadata field; no source fixture or label blob changed.

## Frozen source comparison

Each SHA-256 below was calculated from the Git blob at each revision (not the working tree). All paths are mode `100644` at both revisions.

| File | SHA-256 at `13bdc52` | SHA-256 at `9b5d444` | Identical? |
|---|---|---|---|
| `contracted_mean/app.py` | `f95dda74cbd05dada9f99ae1bd9ed189e9fc9d9223c401b17af7dc542fe4cfdd` | `f95dda74cbd05dada9f99ae1bd9ed189e9fc9d9223c401b17af7dc542fe4cfdd` | Yes |
| `contracted_mean/REQUIREMENTS.md` | `0b73ec92b3904713af42852ee1b702d1d374ad975d32158528a779d95d83d48b` | `0b73ec92b3904713af42852ee1b702d1d374ad975d32158528a779d95d83d48b` | Yes |
| `unrecorded_input/app.py` | `51e95104c79b15bba0b865b3488c6250a576150ee763d8facfdfd57fe56d0d4c` | `51e95104c79b15bba0b865b3488c6250a576150ee763d8facfdfd57fe56d0d4c` | Yes |
| `static_reachability/app.py` | `45b8322435a326e67f8889ef0daec157c2069e20098b9c758d25eb061a473264` | `45b8322435a326e67f8889ef0daec157c2069e20098b9c758d25eb061a473264` | Yes |
| `undocumented_contract/app.py` | `e92aa3146d09407d97a3550b9e203aca39f4df30830d659adb62d59817bdbff4` | `e92aa3146d09407d97a3550b9e203aca39f4df30830d659adb62d59817bdbff4` | Yes |
| `hostile_comment/app.py` | `bb410558980e421b4f4324293ca65efed2b295c3f456b9c409e09035a7604d1a` | `bb410558980e421b4f4324293ca65efed2b295c3f456b9c409e09035a7604d1a` | Yes |
| `negative_report/app.py` | `90b4bcb48c2367f1f0ce299b0f18a6e22fdd5f0aec6848ef6205604fdcadb276` | `90b4bcb48c2367f1f0ce299b0f18a6e22fdd5f0aec6848ef6205604fdcadb276` | Yes |

The ground-truth blob is identical at both revisions (SHA-256 `321a372952665891a7111cb82c91b23156f1e89c010bf7611ee98b1dea66c714`). The registry differs only in its first field: the preregistered commit has `revision: TO_BE_FILLED_BEFORE_FREEZE`; its descendant has `freeze_ref: refs/blackbox/m4b3-freeze`. The registry hashes are respectively `072b9a68a11ba04a09da88651da8f5385c6d2506483777fe0816d949a70bb75d` and `2c03defe1d938d23e6b7ada8e63b2cdbcfeded7ac2f65fa464e0ce39ce5c7ed8`. Its case list and registered source hash map are otherwise the same.

## Runner correction

The original runner resolved a mutable ref and did not compare it to the preregistration or the results-template revision. It now pins `PINNED_REV` to `13bdc52bad27c49b77e85daac16876133f382009`, resolves that exact commit with `git rev-parse --verify`, and reads registry, labels, source, and documentation blobs directly from that revision. It accepts the original registry metadata without rewriting it and still checks every registered source SHA-256. Source paths and regular Git modes are checked before reading. The commit ID is included in evidence records and therefore in each evidence-package hash.

The results template now names `13bdc52`. Before dry-run or live planning, it must have template-only status, an empty results list, and a revision matching the selected revision. Existing non-template results are never overwritten.

## Model and timeout configuration

The preregistered M4B.3 settings remain Ollama `qwen3.5:4b`, context 2048, temperature 0, thinking disabled, output cap 768, timeout 60 seconds, and zero retries. Historical M4B.2 records establish the model tag, context, temperature and thinking setting, but not the timeout environment value or full immutable model digest; timeout parity with M4B.2 is therefore unknown.

Before a future live run, the runner queries the local Ollama `/api/tags` endpoint and `ollama --version`. It requires exactly the preregistered model tag and a full digest beginning with recorded prefix `d8b0f5e9760c`; mismatch or unavailable local metadata fails closed. It does not pull or substitute a model. The full available digest and Ollama version are written to each result and the result envelope. Offline tests exercise this verification with mocked metadata; no live Ollama inference or live daemon query was performed for this correction.

## Validation and changed files

Offline validation: `python -m pytest -q tests/test_m4b3_harness.py` → **14 passed**. `python scripts/evaluate_m4b3.py --help` lists `--dry-run` and `--run-live`. Dry-run reports the original revision, six cases, four arms, 24 planned evaluations, and zero model calls; all four arms share the same evidence-package hash within each case. No real investigator calls have been made.

The broader `python -m pytest -q` suite reported **135 passed, 8 skipped, 8 failed** in 53.62 seconds with one existing Starlette deprecation warning. The eight failures were in existing `tests/test_repair.py` expectations: seven expected verified/failed/rejected repair statuses but received `UNVERIFIED`; one expected the unreproducible fixture reproduction to return 0 but got 1. No repair code or security controls were changed as part of this harness correction.

Files changed by this correction: `scripts/evaluate_m4b3.py`, `tests/test_m4b3_harness.py`, `data/m4b3-results.json`, `EVALUATION.md`, and this audit. The original preregistration, frozen fixtures and labels, prompts, schemas, production investigator, Docker controls, and repair approvals were not changed. `graphify-out/` was refreshed code-only as required by the repository instructions.
