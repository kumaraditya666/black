# BDB-5 R2 Abstention Contract Fix

**Date:** 2026-11-11

**Status:** `ARTIFACT_CONTRACT_HARDENED — 9B_RESULT_ACCEPTED_FOR_REVIEW — NOT_APPROVED — NOT_SCORED`

## 1. The failure being fixed

The first exploratory R2 result in Document 77 was schema-valid but semantically
weak:

| Field | Exploratory value |
|---|---|
| Claim categories | `SERVICE_CAUSE`, `ABSTENTION` |
| `l2_causal_status` | `NOT_ASSESSED` |
| `abstention` | `null` |
| Reproduction record | `REPRODUCTION_BEFORE` without an artifact hash |

The runner accepted it because the schema did not require a structured
abstention. That is now a provider contract violation.

## 2. Change

`blackbox/bdb5/provider.py` adds an explicit abstention contract to the prompt:

- if the evidence does not establish an application, service or source cause,
  set `l2_causal_status` to `NOT_ESTABLISHED` and fill the top-level
  `abstention` object;
- do not emit `SERVICE_CAUSE`, `SOURCE_CAUSE` or
  `APPLICATION_SOURCE_CAUSE` for a cause the evidence does not establish;
- do not put an abstention only in a `Claim`;
- do not combine a structured abstention with `SUPPORTED` or `ESTABLISHED`;
- do not record a `TestExecution` the packet does not contain, and require an
  artifact hash for `PASS`.

`blackbox/bdb5/validation.py` adds `validate_result_contract()`. It is not a
score and does not read evaluator truth. It checks only internal consistency:

- `NOT_ESTABLISHED` requires a structured abstention;
- a causal claim or `ABSTENTION` claim without one is rejected;
- a structured abstention requires `NOT_ESTABLISHED`.

The provider rejects a result that fails this contract instead of returning it
as `PROVIDER_RESULT_READY_FOR_REVIEW`.

After the reruns exposed missing fields, `provider_result_schema()` now requires
`abstention` at the top level and requires every `Abstention` field:
`scope`, `reason`, `missing_evidence`, `source_not_established` and
`application_source_not_established`. The prompt also includes a concrete
application-source abstention object. A required field may still be `false` or
`null`; the contract and Pydantic validators reject inconsistent values.

## 3. Verification against the saved bad result

The exact first exploratory result was loaded from
`%TEMP%\bdb5_r2_live_result.json` and revalidated:

```text
contract_passed = False
contract_codes = ('missing_structured_abstention',)
contract_details = ('claim category SERVICE_CAUSE requires a structured abstention',)
l2_causal_status = NOT_ASSESSED
abstention = None
claim_categories = ('SERVICE_CAUSE', 'ABSTENTION')
```

This is the desired rejection. The saved result remains unscored and is not
retroactively approved.

## 4. Tests

Focused provider tests:

```text
python -m pytest tests/test_bdb5/test_provider.py -q -p no:cacheprovider
8 passed
```

Full BDB-5 suite:

```text
python -m pytest tests/test_bdb5 -q -p no:cacheprovider
59 passed, 6 warnings
```

`test_provider_schema_requires_abstention` checks the full required abstention
shape and is also asserted on the native Ollama `format` payload.
`test_result_contract_rejects_not_established_without_abstention` covers the
second live failure shape. Two further tests cover unrecorded reproduction and
PASS executions.

## 5. Boundary

- Six exploratory live model calls have been made across Documents 77 and 79.
- No score was produced.
- No approval record was created.
- R1, R2 and R3 remain `PREPARED`.
- Repository `LIVE_INFERENCE_ENABLED` remains `False`.
- The contract fix is provider-side; it does not weaken or replace the
  independent human approval requirement.

## 6. Contract-fix rerun

The second exploratory call used local Ollama `qwen3.5:4b`, native `/api/chat`,
thinking disabled, `num_ctx=8192`, and one provider call.

| Property | Result |
|---|---|
| HTTP status | `200` |
| Ollama `done_reason` | `stop` |
| Prompt tokens | `2242` |
| Output tokens | `151` |
| Response hash | `90ecd90cf2a62c888f3a83ca90f21aa22a030a534611088b441333168f5aafb9` |
| Parsed result hash | `3c5caaef8dc1bafa208197438264265763b44fa684579906e96b25c0dfd36dd8` |
| Provider outcome | `PROVIDER_REJECTED` |
| Contract code | `missing_structured_abstention` |

The model changed its failure shape but still did not comply:

```text
l2_causal_status = NOT_ESTABLISHED
abstention = None
claim_categories = []
test_executions = [REPRODUCTION_BEFORE test_dict_write FAIL, no artifact hash]
```

The provider rejected it with:

```text
provider result violates abstention contract:
l2_causal_status NOT_ESTABLISHED requires a structured abstention
```

Raw response: `%TEMP%\bdb5_r2_live2_raw_response.json`.
Full unscored record: `%TEMP%\bdb5_r2_live2_record.json`.

## 7. Prompt and schema hardening

`provider_result_schema()` adds `abstention` to the top-level `required` list,
and adds every `Abstention` field to that definition's `required` list. The
native Ollama request uses that schema for constrained decoding. The prompt
includes this shape when `l2_causal_status` is `NOT_ESTABLISHED`:

```json
"abstention": {
  "scope": "APPLICATION_SOURCE",
  "reason": "The evidence does not establish an application-source cause.",
  "missing_evidence": ["application stack trace"],
  "source_not_established": false,
  "application_source_not_established": true
}
```

The first hardened call (section 8) showed that requiring only the top-level key
was insufficient: the model emitted an abstention object but omitted the
application-source flag. All five fields are now required.

## 8. Hardened-schema rerun

The third exploratory call used the same local model and settings.

| Property | Result |
|---|---|
| HTTP status | `200` |
| Ollama `done_reason` | `stop` |
| Prompt tokens | `2393` |
| Output tokens | `211` |
| Response hash | `a00a672f3e4571aef9b789e770b5f426b4e00ebf40d5e6cf6bbc02310ca0a416` |
| Parsed result hash | unavailable; schema rejection |
| Provider outcome | `PROVIDER_REJECTED` |
| Error | `APPLICATION_SOURCE abstention must explicitly state application source is not established` |

The model got materially closer:

```text
l2_causal_status = NOT_ESTABLISHED
claims = [OBSERVATION]
abstention.scope = APPLICATION_SOURCE
abstention.reason = present
abstention.missing_evidence = present
abstention.source_not_established = false
abstention.application_source_not_established = missing
```

Pydantic treats the missing boolean as `false` and rejects the object. This is
not a valid abstention yet. Raw response:
`%TEMP%\bdb5_r2_live3_raw_response.json`; full unscored record:
`%TEMP%\bdb5_r2_live3_record.json`.

## 9. Fully required rerun

The fourth exploratory call used the same local model and the schema requiring
all five abstention fields.

| Property | Result |
|---|---|
| HTTP status | `200` |
| Ollama `done_reason` | `stop` |
| Prompt tokens | `2410` |
| Output tokens | `315` |
| Request hash | `b0bf2ee143f78516caf545bdaa5f760e8dfa57da5f4950a62e16e2a5f03fe59c` |
| Response hash | `73a7688c45020cdb14fa0622b30902603b3e702046e82000031ac5c643bd786f` |
| Parsed result hash | `5198f8c74b3d137d5f883f22a4320dd4319480a84cc0f4c4e98666017a05a426` |
| Provider outcome | `PROVIDER_ACCEPTED` |
| Contract (pre-artifact rule) | passed, no codes |
| Runner status | `RUN_READY_FOR_REVIEW` |
| Validation issues | none |

The accepted shape was:

```text
l2_causal_status = NOT_ESTABLISHED
claims = [OBSERVATION]
abstention.scope = APPLICATION_SOURCE
abstention.reason = "The evidence does not establish an application-source cause."
abstention.missing_evidence = ["application stack trace", "source code modification evidence"]
abstention.source_not_established = false
abstention.application_source_not_established = true
```

The result still includes a `REPRODUCTION_BEFORE` test execution without an
artifact hash, so it is not a clean strict-dimension answer. It is not scored,
and it is not an approved benchmark result. Raw response:
`%TEMP%\bdb5_r2_live4_raw_response.json`; full unscored record:
`%TEMP%\bdb5_r2_live4_record.json`.

This historical acceptance does **not** survive the later execution-artifact
rule. Revalidating this exact result now yields `missing_execution_artifact`
for `REPRODUCTION_BEFORE test_dict_write`.

## 10. Execution artifact rule

`validate_result_contract()` now rejects any execution with a reproduction role
(`REPRODUCTION_BEFORE` or `REPRODUCTION_AFTER`) or a `PASS` outcome when
`artifact_sha256` is absent. The prompt states the same rule. This prevents a
model from claiming an execution it cannot evidence.

The prior accepted result fails this rule:

```text
contract_codes = ('missing_execution_artifact',)
detail = "test execution REPRODUCTION_BEFORE 'test_dict_write' requires artifact_sha256"
```

It remains a historical exploratory output, not a current accepted result.

## 11. Fresh 4B run and 9B comparison

A fresh 4B run under the artifact rule still emitted an unrecorded
`REPRODUCTION_BEFORE test_dict_write` and was rejected with
`missing_execution_artifact` (response hash
`4b1f6c466169935e6f68150b05f1146991d967abe86ca229775b33391bb4272c`).

The 9B comparison used the same packet and contract.

| Property | Result |
|---|---|
| Model | `qwen3.5:9b-q4_K_M` |
| HTTP status | `200` |
| Ollama `done_reason` | `stop` |
| Prompt tokens | `2454` |
| Output tokens | `281` |
| Request hash | `9c4a55ade43ae64e88fcb83a3dcf6533b4b098af87d18e6f9a040248d51a739d` |
| Response hash | `0c810422207debdf2ea79e80d826f52daa3931d5434cc1401999e98cfcbb64fd` |
| Parsed result hash | `2658e475d5388778803a399cc188aae0ee177de75260ebf0723bf5b265166fde` |
| Provider outcome | `PROVIDER_ACCEPTED` |
| Contract | passed, no codes |
| Runner status | `RUN_READY_FOR_REVIEW` |
| Validation issues | none |

The accepted shape was `NOT_ESTABLISHED`, an `APPLICATION_SOURCE` abstention
with `application_source_not_established = true`, `OBSERVATION` and
`HARNESS_CAUSE` claims, and `test_executions = []`. It remains unapproved and
unscored. Record: `data/bdb5_handoff/bdb5_r2_live6_record.json`; standalone result:
`data/bdb5_handoff/bdb5_r2_live6_result.json`.

## 12. Next step

Approval is deferred by the owner. When two real reviewers are available, use
Document 78 and then score `data/bdb5_handoff/bdb5_r2_live6_result.json` with the resulting
approval. No automated substitute for that approval is valid.
