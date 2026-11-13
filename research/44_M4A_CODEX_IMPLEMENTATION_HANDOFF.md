# Milestone 4A — Codex implementation handoff

## Decision

**Recommend one first experiment: A, bounded agent-selected read-only retrieval.** Do not implement it as part of 4A. The 3D pilot directly exposed the missing `rolling_sum` body and `total` caller, while also showing that more context coincided with an incorrect explanation and a validation failure. The intervention tests whether the model can select useful evidence under a strict budget; it is not assumed to improve reasoning. See [gap analysis](42_M4A_BLACKBOX_GAP_ANALYSIS.md), [full protocol and thresholds](43_M4A_EXPERIMENT_DESIGNS.md) and [source-backed research](41_M4A_COMPETITOR_ARCHITECTURES.md).

## Start from the actual state

- Preserve current uncommitted work and research artifacts. HEAD when researched: `b96840fef85585904c9348e213dbbec9c0ca521a`; it does **not** contain all working-tree 3B.1–3F changes. Inspect status and diff first. Do not reset, commit unrelated changes or replace existing modules.
- Read `blackbox/investigator.py:collect`, `blackbox/repository_intelligence.py:retrieve`, `blackbox/providers.py:Provider.analyze`, `blackbox/semantic_verification.py`, and `blackbox/repair/eligibility.py` and `pipeline.py`. Current provider has no tool channel; one reference-repair retry is not a semantic investigation loop.
- Preserve local frozen refs and evidence for 3C/3F and their Git-ignored databases. Do not use those tuned cases as the final holdout. The original small studies are unblinded; no independent reviewer was obtained for them.
- This research turn did not rerun the project suite. Before any future implementation, record current test and Docker baseline rather than inheriting historic counts.

## Proposed reviewable implementation boundary

Only after the user requests implementation, build an **evaluation-only** typed dispatcher for `search_symbols` and `read_excerpt` against the existing configured local repository and immutable full commit. Maximum two read requests, 20 lines/1,200 characters per request, 2,000 characters total and three model turns including the answer; fail with explicit unavailable/ambiguous/limit states. The dispatcher owns path and revision checks, regular Git-object checks, result redaction, call limits, provenance IDs and logs; the model cannot choose a repository, change the revision or request a shell command. If the provider cannot produce the typed action, report that rather than switching models. Never silently truncate essential evidence, widen a patch path, edit tests or automatically approve a repair.

Treat this as an experimental interface—not authorization to run external code or expand repository trust. Keep all existing `evaluate`, `content_pinned`, explicit approval, `validate_and_apply`, Docker image and lifecycle checks unchanged. Source/comments/tool outputs remain untrusted; existing best-effort redaction is insufficient for unknown secrets. Provider consent and privacy restrictions still apply. A read-only Git tool can still expose sensitive files, so scope it to exact authorized fixture paths and fail closed when identity or safe display is uncertain.

## Evaluation gate

Before fitting prompts or tool schema, commission and freeze genuinely new holdouts, independent author labels and blinded second-review scoring if available. If not available, explicitly label the run unblinded and exploratory and do not claim an independently evaluated reliability gate. Use the shared plan in [43](43_M4A_EXPERIMENT_DESIGNS.md): counterbalanced paired comparisons, two repeats, baseline plus a budget-matched fixed-read control where feasible, stable model and evidence universe, all failures in denominators, measured tokens/latency and no auto-execution. The provisional decision threshold requires security/provenance checks pass, at least two paired case improvements and at most one regression, with no new false-certainty result in the ambiguity/negative controls; even meeting it does not statistically establish safety. Stop if scope, budget or isolation is violated.

Implement deterministic tests for wrong/missing revisions, traversal and Git symlinks, file and line limits, malicious prompt text, redaction, unknown symbols, duplicate calls and no working-tree writes. Then run the full suite and evaluate on the heldout set. Report tool request traces and exact per-case evidence, outcomes and cost. Do not claim improvement from a single fixture or a passing patch; do not choose B or C in the same experiment. Leave the reliability gate open unless an independently reviewed protocol justifies closing it.

## UNDERSTAND WHAT WE LEARNED

A one-shot prompt asks a model to answer from one prepared snapshot. An **agentic** workflow lets it ask for a permitted observation, see the result and decide what to do next. A tool call is a structured request—not authority by itself: the host must validate and execute a narrow allowed operation, then return a labeled result. That distinction matters because an unrestricted shell would give the model far more power than a read-only source lookup.

**Runtime telemetry** is information observed while software runs, such as an exception, trace span or a safe, predeclared state category. It can distinguish cases that look identical in source, but it can be incomplete, misleading, sensitive or unrelated to the incident. A hypothesis is a proposed explanation; a competing hypothesis is another plausible one. A useful investigation asks what evidence would differ between them and reports uncertainty if that evidence is unavailable.

Context quality matters because the right caller or missing input can change the answer, while a large pile of irrelevant code can consume the model's limited window or obscure a contradiction. BLACKBOX's 3D example shows both the potential value and the danger: added context helped a patch pass, while the stated window diagnosis remained wrong.

Open-source code and papers reveal specific tools, control flow and measured experiments; documentation describes advertised workflows. Neither reveals inaccessible commercial internals or proves that a product's diagnosis is correct. Independent reproduction, held-out evidence, explicit uncertainty and human review are still needed.
