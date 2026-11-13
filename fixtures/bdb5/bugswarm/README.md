# BugSwarm CI log fixtures

These are raw Travis build logs fetched from the public BugSwarm REST API on
2026-11-10 for BDB-5 R1/R2 case preparation.

- `109227527.log` — R1, `bwhmather/verktyg`, failed revision
  `71dc420c22fadbae064c46b426e093bec7b86f32`.
- `83523531.log` — R2, `marshallward/f90nml`, failed revision
  `d8d88884dea251fc1d9e63b9afcf19b81a785066`.

The hashes and source references are in `registry.json`. These files are
evidence artifacts, not ground truth. They contain no gold patch, hidden test
list or target mapping. The preparation adapter creates a bounded and
host-path-sanitised CI excerpt for the model-visible packet; this full log is
evaluator/audit material and must not be pasted into a prompt unchanged.
