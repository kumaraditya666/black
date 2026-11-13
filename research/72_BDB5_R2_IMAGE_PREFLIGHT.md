# BDB-5 R2 BugSwarm Image Preflight

**Date:** 2026-11-10

**Status:** `BDB5_R2_IMAGE_PREFLIGHT_COMPLETE — REPRODUCED — NO_INFERENCE`

**Case:** BDB5-R2

**Image:** `bugswarm/images@sha256:ff328c82ecf295da3c56148ac409c7a1021720229b2e5c393d4a6eaa2741b730`

## Result

The pinned R2 image was pulled and the failed checkout was tested at the
recorded revision. The exact missing-fixture failure reproduced under the
image's Python 3.2.5:

```text
ERROR: test_dict_write
IOError: [Errno 2] No such file or directory: 'types_dict.nml'
test_f90nml.py:211 in assert_file_equal
Ran 38 tests
FAILED (errors=1)
```

The result is a real reproduction of the CI failure signature. It is not a
model result, not a score, and not an application-source diagnosis.

## Image and source identity

| Property | Observed |
|---|---|
| Tag | `bugswarm/images:marshallward-f90nml-83523531` |
| Docker Hub amd64 digest | `sha256:ff328c82ecf295da3c56148ac409c7a1021720229b2e5c393d4a6eaa2741b730` |
| Docker Hub compressed size | `1,912,283,801` bytes (about 1.91 GB) |
| Local unpacked size | `7,655,460,346` bytes (about 7.66 GB) |
| OS / architecture | `linux` / `amd64` |
| Image command | `/bin/bash` |
| Image user | `travis` |
| Failed checkout | `/home/travis/build/failed/marshallward/f90nml` |
| Git HEAD | `d8d88884dea251fc1d9e63b9afcf19b81a785066` |
| CI interpreter | Python 3.2.5 |
| Observed interpreter | Python 3.2.5 |

The `passed` checkout is present but was not used. The failed worktree is
mode-dirty and has a BugSwarm-generated `.travis.yml` overlay. The inspected
test and application files match the pinned commit content:

| File | SHA-256 |
|---|---|
| `test/test_f90nml.py` | `4cb324b5a10f06f22d2f604b98f639683316bf7d9816966a783272ca43b1b057` |
| `f90nml/namelist.py` | `bcb9f1ddda3bbad6da310144bc7803500a8bc51fc75c13486e52a824d0ec662a` |

## Exact test command

```bash
cd /home/travis/build/failed/marshallward/f90nml/test
/opt/python/3.2.5/bin/python3.2 test_f90nml.py
```

| Dimension | Result |
|---|---|
| Tests | `38` |
| Failures | `0` |
| Errors | `1` |
| Primary error | `test_dict_write` |
| Exception | `IOError: [Errno 2] No such file or directory: 'types_dict.nml'` |
| Test frame | `test_f90nml.py:211` in `assert_file_equal` |
| Process exit | `1` |
| Model calls | `0` |

## Boundary

The failure is a missing test fixture, not an established application-source
defect. The image preflight does not add a source claim and does not use the
passed checkout to infer one.

- R2's prepared packet contains CI and test-result evidence, with no source
  excerpt.
- The packet review remains `REVIEW_PASSED`.
- The case remains `PREPARED`, not approved.
- No model, provider, repair pipeline, M4B.3 ledger or scorer was run.
- No host repository or case state was modified.

## What this establishes and what it does not

Established:

- the image digest and architecture match the pin;
- the failed revision is present and correct;
- the exact runtime error and test frame reproduce;
- the observed Python version matches the CI log.

Not established:

- an application-source root cause;
- a model diagnosis or a benchmark score;
- an L4 counterfactual or a fix verification;
- independent human label review;
- any result for R3, T1 or P1.

## Next step

Independent human review of R1/R2 and a separately gated live provider adapter
remain. Do not approve R2 or enable live inference from this preflight.
