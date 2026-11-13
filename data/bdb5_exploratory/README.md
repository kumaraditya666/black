# BDB-5 Exploratory R1/R3 Runs

**Status:** `EXPLORATORY_ONLY — NOT_APPROVED — NOT_SCORED`

These are exploratory 9B results. They are not benchmark results and were not
scored. No approval record exists.

## Results

| Case | Runner | Contract | L2 status | Abstention | Fault/file prediction | Result hash |
|---|---|---|---|---|---|---|
| `BDB5-R1` | `RUN_READY_FOR_REVIEW` | passed, no codes | `NOT_ESTABLISHED` | `APPLICATION_SOURCE` | none | `79d8c7ab0b9419bcd817b27587f59ce3a70606a7246142c0b262b469a6d1cbce` |
| `BDB5-R3` | `RUN_READY_FOR_REVIEW` | passed, no codes | `NOT_ESTABLISHED` | `APPLICATION_SOURCE` | none | `e96496ca04f82fe280f3ec5eb1fc4c1eabb3c2988bee6ce0e373dce8d616c183` |

Both runs used `qwen3.5:9b-q4_K_M` through native Ollama at
`http://localhost:11434`, `num_ctx=8192`, one accepted provider call per case.
The runner recorded zero validation issues and packet review `REVIEW_PASSED`.

## What the model returned

- **R1:** three `OBSERVATION` claims about the CI failure, the
  `UnicodeDecodeError` traceback, and the `verktyg/requests.py` source excerpt.
  It did not identify a fault class or predict a file, function, or line.
- **R3:** one `OBSERVATION` claim describing the memoryview/`HttpResponse.content`
  issue and the absence of memoryview handling in the supplied `make_bytes`
  excerpt. It did not identify a fault class or predict a file, function, or line.
- Neither run recorded a test execution or patch.
- Both runs abstained from an application-source cause.

This is a model-behavior observation, not a score.

## Calls and artifacts

Each successful run has one `provider_calls: 1` record and a parsed result:

- `bdb5_r1_exploratory_record.json` / `bdb5_r1_exploratory_result.json`
- `bdb5_r3_exploratory_record.json` / `bdb5_r3_exploratory_result.json`

There are also two earlier **attempt1** records. Those calls returned HTTP 200,
but the local response-capture hook could not read the response, so no result was
parsed. They are recorded as `CLIENT_CAPTURE_ERROR`, not provider or contract
rejections:

- `bdb5_r1_exploratory_attempt1_record.json`
- `bdb5_r3_exploratory_attempt1_record.json`

The successful records have no raw-response file because the hook was removed
for the retry. Request, response, and result hashes are preserved in the records.

## Boundary

- Repository `LIVE_INFERENCE_ENABLED` remains `False`; the live gate was opened
  only inside temporary Python processes.
- The exploratory gate hash is labeled `EXPLORATORY_NOT_APPROVAL`; it is not a
  human approval.
- No result is scored.
- No result is approved.
- The human review handoff remains `data/bdb5_handoff/`.
- T1 and P1 remain blocked for their separate reasons.
