# BDB-5 R1/R2 Real-Case Preparation Report

**Date:** 2026-11-10

**Status:** `BDB5_R1_R2_PREPARATION_COMPLETE — OFFLINE — NO_INFERENCE`

## Outcome

The BDB-5 harness now has a preparation path for the two BugSwarm cases. It
turns a recorded CI log into a deterministic `CaseManifest` and
`EvidencePacket`, verifies the R1 source frame at the pinned Git revision, and
leaves the case at `PREPARED`.

The preparation layer does not approve a case, score a real submission, call a
model, execute a test, or enter the synthetic evaluation engine. A separate R1
image preflight was subsequently run; its result is recorded in
`research/70_BDB5_R1_IMAGE_PREFLIGHT.md`. R1 is not a completed benchmark
result: it is a reviewed-by-nobody preparation artifact waiting for independent
review. The image preflight is complete with a documented interpreter mismatch.

## Files

| Path | Purpose |
|---|---|
| `blackbox/bdb5/real_cases.py` | BugSwarm log parser, R1/R2 case configs, source-frame selection, packet/manifest construction |
| `scripts/bdb5_prepare_ci.py` | Offline preparation CLI; writes outside the repository by default |
| `tests/test_bdb5/test_real_cases.py` | Parser, source, leakage, engine-refusal and CLI tests |
| `fixtures/bdb5/bugswarm/109227527.log` | Recorded R1 Travis build log, 77,938 bytes |
| `fixtures/bdb5/bugswarm/83523531.log` | Recorded R2 Travis build log, 31,468 bytes |
| `fixtures/bdb5/bugswarm/registry.json` | Job/log hashes and pinned source revisions; no gold patch or hidden test list |
| `blackbox/bdb5/__init__.py` | Exports the preparation API |

## Recorded artifacts

The logs were fetched from the public BugSwarm REST API during this task. The
registry records their exact hashes:

| Case | Job | Log SHA-256 | Source revision |
|---|---:|---|---|
| BDB5-R1 | 109227527 | `a3364ac52bd4c9e5deba4963fcf4a7d4676ce400444a59ddb4593b9735c11910` | `71dc420c22fadbae064c46b426e093bec7b86f32` |
| BDB5-R2 | 83523531 | `06025a335c23376a1f8acba1eb12cb27cdda88601df7378deeddbc17ccdc6f94` | `d8d88884dea251fc1d9e63b9afcf19b81a785066` |

The R1 checkout was verified in a temporary clone at the full recorded SHA.
The working repository was not cloned into the project.

## R1 result

The parser extracted five failures from 247 tests. The selected primary
failure is:

- `ERROR: test_modified_url_encoding`
- exception `UnicodeDecodeError: 'ascii' codec can't decode byte 0xc1 ...`
- source frame `verktyg/requests.py:356` in `args`

The source reader verified the same path, line and function from the exact
commit. The packet contains:

1. `ci:1` — a bounded, host-path-sanitised CI excerpt.
2. `test:1` — the recorded test count, result and primary failure.
3. `source:1` — the resolved source excerpt and exact revision.

Preparation hash: `0e940779081d1fda071f4acec3c2847227a7480056bc46d1d4d897c3806b6c8c`.

## R2 result

The parser extracted one error from 38 tests. The selected failure is:

- `ERROR: test_dict_write`
- exception `IOError: [Errno 2] No such file or directory: 'types_dict.nml'`
- test frame `test_f90nml.py:211` in `assert_file_equal`

No application source frame was selected, and the packet does not claim one.
The `TEST_RESULT` evidence identifies the missing fixture as a recorded CI
observation; the evaluator must still keep application-source and harness
claims separate.

Preparation hash: `5b72f085d22f9ae0d38ffde44142e6b5e6206d1e640cc5b62d386f715f82b735`.

## Output separation

The CLI output deliberately separates:

- `model_visible_packet`: the only object intended for a future prompt;
- `evaluator_only`: the manifest, primary-frame diagnostics, source status and
  validation report.

The manifest contains `allowed_files`, so it must not be pasted into a model
prompt. The model-visible packet contains no `root_cause`, `gold_patch`,
`fix_commit`, target mapping or hidden label. Raw host paths are removed from
model-visible CI text; the full raw log remains a hashed artifact only.

## Verification

```text
python -m pytest tests/test_bdb5 -q -p no:cacheprovider
36 passed
```

The two real preparation commands both returned `PREPARED` with
`model_calls: 0` and empty packet-validation issues. The BDB-5 synthetic
self-test still returns 29 cases, 5 expected strict passes, deterministic hash
`1815cedf6619d3632e535cd36e1462d49776935c8b3873c194a33d728981e050`.

The preparation tests also confirm:

- R1 resolves `verktyg/requests.py:356` and R2 resolves only the test frame;
- R1 refuses a missing or unresolved source reader;
- prepared cases remain `PREPARED`, not `APPROVED_FOR_EVALUATION`;
- the synthetic engine still raises `BlockedCaseError` for a real case;
- model-visible output contains no `/home/travis`, `/opt/python` or drive paths;
- the CLI writes a packet with no top-level manifest and no hidden labels.

No provider was imported by the preparation module or CLI. This preparation
run made no Docker calls. A separate preflight (Document 70) pulled and ran the
R1 image without a model provider. No repair pipeline, M4B.3 ledger or
benchmark scorer was run.

## What remains blocked

1. **R1 image preflight:** completed in Document 70. The pinned image was
   pulled, the failed checkout's content matched the pinned revision, and the
   recorded failure reproduced. The image contains Python 3.4.2, not the
   Python 3.5.0 recorded in CI, so this is a reproduced signature with an
   interpreter mismatch, not an exact environment pass.
2. **Real scoring:** an evaluator-only label vault, approval record and real
   scorer now exist (Document 74). No approved real-case model result exists,
   so no real score has been produced.
3. **Live runner:** a no-provider run envelope exists (Document 71), and a
   provider adapter now exists behind an explicit closed gate (Document 74).
   No live call was made during preparation; one exploratory R2 call is
   recorded in Document 77.
4. **Independent review:** the packet and manifest are `PREPARED`; automated
   boundary review passes, but independent human review and approval do not.
5. **R2 negative-control execution:** the image preflight reproduced the
   missing-fixture error (Document 72); the exploratory live result is in
   Document 77 but is not approved or scored.
6. **R3 and T1:** R3 now has an issue-to-source preparation and scoring path
   (Document 75); T1 still needs `N_max`, a complete inventory, telemetry
   ingestion and physical isolation.
7. **P1:** external-repository repair remains blocked behind a separate
   disposable adapter.

## Next step

The R1 image preflight, R2 image preflight and exact Python 3.5.0 check are
complete (Documents 70, 72 and 73). Automated review, gated provider, approval
record and real scoring are implemented (Documents 71 and 74). Independent
human review of the R1/R2/R3 packet and label boundaries remains. Do not
enable live inference or approve any case as part of that work.
