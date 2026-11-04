# Quality and evaluation plan

**PROPOSED**, accessed 2026-11-04. No benchmark has been run and no accuracy is claimed. [SWE-bench](https://github.com/SWE-bench/SWE-bench) offers reproducible issue/patch tasks and a container-based harness; test coverage and public solution contamination limit what a passing score proves. The project documents substantial local resource requirements. [OpenAI's Verified description](https://openai.com/index/introducing-swe-bench-verified/) describes human review and container evaluation; it is not a production-incident benchmark.

## Dataset and ground truth
Build a licensed, pinned set of bugs with immutable buggy revision, reproducible failing command, target and holdout regression tests, incident snapshot, expected causal chain, supporting and contradicting evidence, environment recipe and maintainer/adjudicator notes. Include private held-out tasks with independently audited labels and avoid exposing gold patches to the agent. Split by repository and time to limit leakage. Blind two expert raters to candidate identity, adjudicate disagreements and report uncertainty and coverage. Version fixtures; run a no-op patch and a known-good patch to detect broken tests.

Cases: missing logs; multiple concurrent changes; deliberately wrong first hypothesis; insufficient evidence; patch that fixes target test but breaks holdout; malicious instructions embedded in telemetry; missing source map; flaky baseline; and no network access. For abstention, label cases whose evidence cannot identify a unique cause and score false certainty as an error, not merely absence of a correct answer.

## Measurements
| Metric | Definition and guardrail |
|---|---|
| Diagnosis correctness | independently adjudicated correct causal chain / evaluable incidents; separately count unknown and abstentions |
| Evidence relevance | relevant cited items / cited items, plus supported-claim coverage; rate both relevance and missing evidence |
| False alerts | non-actionable alerts / reviewed alerts; sample non-alert periods to estimate misses |
| Detection latency | observed alert timestamp minus known incident onset; report distribution and misses |
| Compile and test pass | passing runs / attempted patches; report denominator, timeouts and infrastructure errors separately |
| Reproduction and repair | reproducible baseline and passing target after patch / eligible tasks; confirm holdout tests |
| Regression | independently detected regressions / assessed patches, with follow-up window |
| Unsupported claims | claims lacking supporting evidence / audited factual claims; include fabricated citations |
| Cost and latency | total model, compute, storage and egress per completed or failed investigation; report percentiles and timeouts |

Compare single-agent, deterministic and multi-agent variants on identical tasks, models and budgets. Record token usage, retries, tool traces and human review time; use paired comparisons and confidence intervals. Production outcomes require monitored rollout and cannot be inferred from offline tests.
