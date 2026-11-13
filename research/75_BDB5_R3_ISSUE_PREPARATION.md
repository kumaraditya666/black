# BDB-5 R3 Issue Preparation

**Date:** 2026-11-10

**Status:** `R3_PREPARED — NO_INFERENCE — NO_REAL_APPROVAL`

**Case:** BDB5-R3, SWE-bench Verified `django__django-11133`

## 1. Pinned evidence

| Property | Value |
|---|---|
| Dataset revision | `78f471bf655a3137b2e8a75af1501690ec009ec3` |
| Base revision | `879cc3da6249e920b8d54518a0ae06de835d7373` |
| Issue | Django ticket `#30294` |
| Source file | `django/http/response.py` |
| Source SHA-256 | `a6b41d8e9bce659f1e05ecd26142dbcb5caf94f990fd836aac6b503c8950a50c` |
| Label line | 232 |
| Label function | `make_bytes` |

The fixture contains only the original issue report and the pinned source file.
It does not contain the gold patch, the test patch, the hidden test name,
`FAIL_TO_PASS`/`PASS_TO_PASS`, or later fix comments.

## 2. Preparation

`blackbox/bdb5/issue_cases.py` builds a PREPARED packet with:

- `issue:1`, the original memoryview/HttpResponse report;
- `source:1`, a bounded excerpt around `make_bytes`;
- the pinned source revision;
- an unranked issue/source task.

`scripts/bdb5_prepare_r3.py` writes the payload outside the repository by
default.

The source excerpt shows the base behavior:

```python
if isinstance(value, bytes):
    return bytes(value)
if isinstance(value, str):
    return bytes(value.encode(self.charset))
return str(value).encode(self.charset)
```

This explains the issue's representation-string result without using the gold
patch.

## 3. Review and scoring path

`review.py` now supports R3 and checks:

- ISSUE_TEXT and SOURCE_EXCERPT evidence are present;
- `source:1` exists;
- the pinned frame is `django/http/response.py:232` in `make_bytes`;
- the source status is resolved;
- no gold-patch or hidden-test marker is visible.

`score_approved_case()` can score an R3 `InvestigationResult` after a valid
approval. The label vault adds R3 truth and mechanism terms.

An end-to-end CLI run with temporary test data produced:

```text
PREPARED
REVIEW_PASSED
APPROVAL_RECORDED
REAL_CASE_SCORED
strict_pass = true
provider_calls = 0
```

That approval was a test record, not an independent human sign-off.

## 4. Boundaries

- R3 remains `PREPARED`.
- No SWE-bench Docker image was pulled.
- No hidden test or gold patch was used.
- No model, provider or repair pipeline was run.
- No actual reviewer approved the case.
- This is issue/source preparation, not a benchmark execution.

T1 and P1 remain separate and are not made runnable by this work.
