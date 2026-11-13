# BDB-5 R1 BugSwarm Image Preflight

**Date:** 2026-11-10

**Status:** `BDB5_R1_IMAGE_PREFLIGHT_PARTIAL — REPRODUCED_IN_IMAGE_3_4_2_AND_PY35_10 — NO_INFERENCE`

**Case:** BDB5-R1

**Image:** `bugswarm/images@sha256:0c915ddd2f49143477c97a24470a890d3692b57c2562b956075045447816ce86`

## Result

The pinned R1 image was pulled and inspected. The failed checkout is present at
`/home/travis/build/failed/bwhmather/verktyg` and is at
`71dc420c22fadbae064c46b426e093bec7b86f32`. The recorded suite ran and produced
the same failure signature as the CI log:

```text
ERROR: test_modified_url_encoding
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc1 in position 4:
ordinal not in range(128)
verktyg/requests.py:356 in args
Ran 247 tests
FAILED (failures=2, errors=3)
```

This is a real reproduction of the failure signature, not a model result and
not a benchmark score. It is marked partial because the image provides Python
3.4.2 while the recorded CI log says Python 3.5.0.

## Image identity

| Property | Observed |
|---|---|
| Tag | `bugswarm/images:bwhmather-verktyg-109227527` |
| Docker Hub amd64 digest | `sha256:0c915ddd2f49143477c97a24470a890d3692b57c2562b956075045447816ce86` |
| Docker Hub `full_size` | `1,911,723,658` bytes (about 1.91 GB compressed) |
| Local image size | `7,653,810,640` bytes (about 7.65 GB unpacked) |
| OS / architecture | `linux` / `amd64` |
| Docker Desktop | `29.9.2` |
| Pull result | digest matched the requested pin |

The pull was performed by digest, not by a mutable tag. The image also contains
a `passed` checkout; it was not used. Only `failed` was inspected and tested.

## Source identity

The failed checkout's Git HEAD is the pinned failed revision. The worktree is
mode-dirty (`777` file modes) and `.travis.yml` is a BugSwarm-generated overlay,
but the application and test files inspected have no content diff. Content
hashes match the local checkout at the same commit:

| File | SHA-256 |
|---|---|
| `verktyg/requests.py` | `1bbf79f3a1dc790f5585ecf0850aee53ad92db29bfbc77d0a6a49a25b4620c20` |
| `verktyg/testsuite/test_requests.py` | `e6c86feb577feae02611f5356053ce6d10d6edeef4eea8219046a44b151e0e9e` |
| `.travis.yml` | `2d30e72fabcc369f4a61fca60e5e2b49952a24a899fc1f59f5dd9b6949bd8355` |

The BugSwarm overlay rewrites `.travis.yml` to the generated job configuration
with `python: '3.5'`; that is metadata, not an application change.

The source frame is unchanged at the pinned revision:

```text
356:            encoding=self.url_charset, errors=self.encoding_errors,
```

The test that triggers it is `test_modified_url_encoding`, which constructs a
EUC-KR query string and then reads `req.args['foo']`.

## Environment

| Property | Recorded CI | Image |
|---|---|---|
| Python | `3.5.0` | `3.4.2` |
| `werkzeug` | resolved by CI | `0.10.4` |
| `coverage` | installed by CI | `4.5.4` (installed in the ephemeral container) |
| Workspace | `/home/travis/build/bwhmather/verktyg` | `/home/travis/build/failed/bwhmather/verktyg` |

No `/opt/python/3.5.0` or `python3.5` executable was found in the image's
`/opt`, `/usr/local`, or `/home/travis` trees. The image's virtualenvs cover
Python 2.6 through 3.4, not 3.5.

The exact recorded command was run in an ephemeral container:

```bash
coverage run --source=verktyg setup.py test
```

Dependencies were installed only inside that discarded container. No host
repository, test file, label, or case state was modified.

## Follow-up: Python 3.5.10

Because the BugSwarm image has no Python 3.5 interpreter, a separate standard
`python:3.5.10` container was given a copy of the same pinned source and run
with the same command. The `python:3.5.0` tag was not available from the
registry; `3.5.10` is the closest executable 3.5.x check.

| Property | Result |
|---|---|
| Image | `python:3.5.10` |
| Image digest | `sha256:42a37d6b8c00b186bdfb2b620fa8023eb775b3eb3a768fd3c2e421964eee9665` |
| Image size | `1,280,843,567` bytes |
| Python | `3.5.10` |
| Source revision | `71dc420c22fadbae064c46b426e093bec7b86f32` |
| Test count | `247` |
| Failures / errors | `2` / `3` |
| Primary failure | `test_modified_url_encoding` at `verktyg/requests.py:356` |
| Result | same `UnicodeDecodeError` signature |

The failure therefore reproduces on Python 3.5.10 as well as the image's
Python 3.4.2. Exact Python 3.5.0 was subsequently source-built and verified;
see Document 73. The exact BugSwarm image environment remains 3.4.2.

## Test result

| Dimension | Result |
|---|---|
| Test count | `247` |
| Failures | `2`: `test_base_request`, `test_form_data_ordering` |
| Errors | `3`: `test_modified_url_encoding`, `test_shallow_mode`, `test_storage_classes` |
| Primary error | `UnicodeDecodeError` at `verktyg/requests.py:356` in `args` |
| Process exit | `1` |
| Model calls | `0` |

This matches the five failing/erroring tests and the primary stack frame in the
recorded CI log. The suite also confirms that the failure is not a single
test-specific accident: the other two errors and two failures share the same
query-string/`parse_qsl` boundary.

## What this does not establish

- It does not reproduce the exact BugSwarm image environment. The image is
  3.4.2; exact Python 3.5.0 was verified separately in Document 73.
- It does not establish a counterfactual L4 cause. No fix checkout, revert, or
  restore experiment was run.
- It does not approve the case. The case remains `PREPARED`.
- It does not run a model, score a diagnosis, or prove that a future model will
  identify the mechanism.
- It does not validate R2; that separate preflight is in Document 72.
- It does not verify the `passed` checkout or use the fix to establish ground
  truth.

## Commands used

```bash
docker pull --platform linux/amd64 \
  bugswarm/images@sha256:0c915ddd2f49143477c97a24470a890d3692b57c2562b956075045447816ce86

# Inside the ephemeral container, from the failed checkout:
coverage run --source=verktyg setup.py test
```

On this Windows host, `MSYS_NO_PATHCONV=1` was required when passing
container-internal absolute paths through Git Bash.

## Next step

The automated packet review and no-provider run envelope now pass; see Document
71. Exact Python 3.5.0 is recorded in Document 73. Independent human review and
any live provider call remain. Do not approve R1 or enable live inference from
this preflight.
