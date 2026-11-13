# M4B.3 arm-order correction

## Scope and outcome

This was an offline preparation correction. The M4B.3 investigator was not called, no fixture or repair workflow was executed, and the original preregistration was not changed. The runner continues to read the immutable preregistered revision `13bdc52bad27c49b77e85daac16876133f382009`.

## Original scheduling defect

The preregistration in `research/50_M4B3_EVIDENCE_LAYERED_REASONING.md` says that arm order rotates across cases. The original `plan()` loop iterated over the arm dictionary in the same A, B, C, D order for every case. That violated the registered protocol: if a provider or machine changes over time, or if later requests are affected by earlier requests, one arm could repeatedly receive the same relative position.

## Corrected schedule

The runner verifies that the registry at the pinned commit has exactly this case order before building the plan:

1. `m4b3_contract_mean`
2. `m4b3_unrecorded_input`
3. `m4b3_static_reachability`
4. `m4b3_undocumented_contract`
5. `m4b3_hostile_comment`
6. `m4b3_negative_report`

It applies the preregistered correction schedule:

| Case | Execution order |
|---|---|
| `m4b3_contract_mean` | A, B, C, D |
| `m4b3_unrecorded_input` | B, C, D, A |
| `m4b3_static_reachability` | C, D, A, B |
| `m4b3_undocumented_contract` | D, A, B, C |
| `m4b3_hostile_comment` | A, C, D, B |
| `m4b3_negative_report` | B, D, A, C |

This is deterministic counterbalancing, not randomization. Each arm occurs once in every case and in all four execution positions across the study.

| Arm | Position 1 | Position 2 | Position 3 | Position 4 | Total |
|---|---:|---:|---:|---:|---:|
| A | 2 | 1 | 2 | 1 | 6 |
| B | 2 | 1 | 1 | 2 | 6 |
| C | 1 | 2 | 1 | 2 | 6 |
| D | 1 | 2 | 2 | 1 | 6 |

For each arm, the difference between its most-used and least-used position is one.

## Plan and execution

`plan()` validates the frozen registry case order, then constructs one ordered list of case/arm evaluations. Dry-run prints the schedule and the individual planned evaluations from this list. The live path passes that same list to `execute()`, which iterates it in order; there is no separate live scheduling implementation. If the frozen registry case order changes, planning fails closed instead of silently assigning the schedule to different cases.

Arm definitions remain unchanged: A is current prompt/current schema; B is layered prompt/current schema; C is current prompt/layered schema; D is layered prompt/layered schema. Evidence construction, scoring, model settings, request budget, timeout, and zero-retry policy remain unchanged.

## Tests and dry-run

`python -m pytest -q tests/test_m4b3_harness.py` → **18 passed**.

The regression coverage verifies the exact case-to-order mapping, one instance of every arm per case, all arm-position combinations, position-frequency balance, deterministic repeated plans, mocked execution order, identical evidence-package hashes within each case, dry-run with no model preflight, immutable revision use, and rejection of mismatched or nonempty result templates.

`python scripts/evaluate_m4b3.py --dry-run` reports revision `13bdc52bad27c49b77e85daac16876133f382009`, six cases, four arms, 24 planned evaluations, and zero model calls. It prints the expected order for each case. The four arms within each case retain one shared evidence-package hash.

The result file `data/m4b3-results.json` remains `template_only_no_model_calls` with `results: []`. No investigator model calls were made.

## Remaining limitations and status

Offline tests and dry-run verify schedule construction and harness behavior with mocked providers; they do not establish model accuracy, live Ollama availability, live latency, or successful real structured responses. M4B.3 is ready for a separate live-execution preflight. This correction does not authorize live calls. A separate explicit instruction and passing preflight are still required before live execution.
