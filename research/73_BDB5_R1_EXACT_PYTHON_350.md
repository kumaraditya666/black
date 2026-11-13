# BDB-5 R1 Exact Python 3.5.0 Verification

**Date:** 2026-11-10

**Status:** `R1_EXACT_PYTHON_3_5_0_REPRODUCED — NO_INFERENCE`

**Case:** BDB5-R1

**Source revision:** `71dc420c22fadbae064c46b426e093bec7b86f32`

## Result

The R1 failure reproduces on an interpreter built from the exact Python 3.5.0
source release:

```text
Ran 247 tests
FAILED (failures=2, errors=3)
ERROR: test_modified_url_encoding
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc1 in position 4:
ordinal not in range(128)
verktyg/requests.py:356 in args
```

This closes the interpreter-version gap left by the BugSwarm image, which
contains Python 3.4.2.

## Build

The `python:3.5.0` registry tag was not available. Exact 3.5.0 was compiled from
the official source archive inside the disposable `python:3.5.10` container:

```bash
curl -fsSLO https://www.python.org/ftp/python/3.5.0/Python-3.5.0.tgz
tar -xzf Python-3.5.0.tgz
cd Python-3.5.0
./configure --prefix=/opt/python/3.5.0 --without-ensurepip --without-ssl
make -j2
make install
```

| Property | Result |
|---|---|
| Interpreter | `Python 3.5.0` |
| Compiler | GCC 8.3.0 |
| Platform | `linux` |
| Prefix | `/opt/python/3.5.0` |
| SSL module | not built |
| Test dependency | `werkzeug 0.10.4` |

`--without-ssl` was used because the Python 3.5.0 source predates the
container's OpenSSL 1.1 interface. R1's test path does not use SSL. This is a
limitation of the interpreter build, not of the case.

## Source identity

The source was copied from the pinned local checkout into `/work`; no host
repository was modified.

| File | SHA-256 |
|---|---|
| `verktyg/requests.py` | `1bbf79f3a1dc790f5585ecf0850aee53ad92db29bfbc77d0a6a49a25b4620c20` |
| `verktyg/testsuite/test_requests.py` | `e6c86feb577feae02611f5356053ce6d10d6edeef4eea8219046a44b151e0e9e` |

The checkout is mode-dirty and contains the BugSwarm `.travis.yml` overlay, as
in the image preflight. Only the failed revision was used.

## Test command

```bash
cd /work
PYTHONPATH=/work:/usr/local/lib/python3.5/site-packages \
  /opt/python/3.5.0/bin/python3.5 \
  -m unittest discover -s verktyg/testsuite -p 'test_*.py'
```

This runs the same 247-test suite as the recorded CI run. The original
`coverage run --source=verktyg setup.py test` wrapper was not used because
setuptools' test command attempted to resolve `werkzeug` through pip, and this
minimal 3.5.0 build has no SSL module. The dependency was supplied locally at
the pinned version.

## Test result

| Dimension | Result |
|---|---|
| Tests | `247` |
| Failures | `2`: `test_base_request`, `test_form_data_ordering` |
| Errors | `3`: `test_modified_url_encoding`, `test_shallow_mode`, `test_storage_classes` |
| Primary error | `UnicodeDecodeError` at `verktyg/requests.py:356` in `args` |
| Exit code | `1` |
| Model calls | `0` |

## Boundary

- R1 remains `PREPARED`; this does not approve it.
- No gold patch, fixed checkout, hidden test list or passed job was used.
- No L4 counterfactual was run.
- No model, provider, scorer or repair pipeline was run.
- This does not by itself establish benchmark performance.
