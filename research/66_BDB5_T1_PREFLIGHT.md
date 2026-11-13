# BLACKBOX BDB5-T1 Real-Data Preflight

**Document:** 66  
**Date:** 2026-11-09  
**Dataset:** `phamquiluan/RCAEval`  
**Pinned revision:** `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`  
**Case:** BDB5-T1  
**Status:** `T1_PREFLIGHT_BLOCKED — NOT_EXECUTED — LIVE_INFERENCE_DISABLED`

## 1. Scope and non-actions

This was a limited data inspection, not a benchmark execution. I downloaded only the three permitted T1 artifacts: `logs.parquet`, `metrics.parquet`, and `inject_time.txt`. I did not download `root_cause.txt`, `cases.parquet`, the complete RCAEval dataset, or any other case directory.

I did not create a benchmark prompt, invoke a model, run Docker, initialize M4B.3, modify source code, modify tests, modify Documents 50/56/57/60/61/63/65, or execute a repair workflow. The hidden label file was not opened, parsed, inspected, or copied. The HF tree API exposed its filename and byte size; no content request was made.

The source case-directory slug is deliberately not repeated in this report because it is target-bearing. The artifacts are identified below by the pinned dataset revision, exact filenames, byte sizes, and SHA-256 values, which are sufficient to identify the files without restating the target-bearing slug.

## 2. Artifact identity

All artifacts were stored outside the Git repository under:

`%TEMP%\BLACKBOX_BDB5_T1_PREFLIGHT\staging\T1\raw\<case>\`

| Artifact | Exact bytes | SHA-256 | HF LFS SHA-256 match |
|---|---:|---|---|
| `logs.parquet` | 1,003,956 | `eea9d351ff71dbd1eb2bf77a39db60dc8dc1cead962d8672ffb41627dae9bfbb` | Yes |
| `metrics.parquet` | 187,614 | `8a20a7caba8f268e725d4921ccae887ab1b30c1741019ccd06992ea784e7ff32` | Yes |
| `inject_time.txt` | 10 | `a130a8d9d14b547fe9a14b4858f82958380ce8a796bf7bc4fa8b482a14316ed8` | N/A; ordinary Git blob |

Verification details:

- The Hugging Face dataset revision endpoint returned `sha = afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`, matching the requested pin.
- The pinned case-tree endpoint returned exactly `logs.parquet`, `metrics.parquet`, `inject_time.txt`, and the forbidden `root_cause.txt`.
- The two Parquet sizes and SHA-256 values above match the Hugging Face LFS metadata exactly.
- `inject_time.txt` contains the ten bytes `1732243203` and has no trailing newline.
- The forbidden file was not downloaded. A recursive filename check under the preflight root found **0** files matching `*root*cause*`.

## 3. Parquet findings

Both files were written by `parquet-cpp-arrow` version 25.0.0 with pandas 3.0.5 metadata. Neither schema declares an explicit row ID or a Parquet timestamp logical type; both time fields are plain `int64`.

### 3.1 `logs.parquet`

| Property | Finding |
|---|---|
| Row groups | 1 |
| Rows | 84,665 |
| Row-group row count | 84,665 |
| Columns | 3 |
| Schema | `timestamp: int64`, `container_name: large_string`, `message: large_string` |
| Nulls | `timestamp`: 0; `container_name`: 0; `message`: 1 |
| Timestamp column | `timestamp` |
| Unique timestamps | 1,441 |
| Minimum timestamp | `1732242483` (`2024-11-22T02:28:03Z`) |
| Maximum timestamp | `1732243923` (`2024-11-22T02:52:03Z`) |
| Rows inside inclusive window | 84,665 |
| Rows before / after window | 0 / 0 |
| Original order | Nondecreasing; zero descending adjacent pairs |
| Equal-timestamp ties | 83,224 adjacent ties; maximum 228 rows at one timestamp |
| Explicit stable row ID | No |
| Single-column uniqueness | `timestamp`: no; `container_name`: no; `message`: no |
| Composite `(timestamp, container_name, message)` | 74,706 unique values for 84,665 rows, so not a unique row key |

The entire log table lies inside `[1732242483, 1732243923]`. The logs are already in nondecreasing timestamp order, but many rows share each timestamp. There is no declared or verified stable row identifier.

### 3.2 `metrics.parquet`

| Property | Finding |
|---|---|
| Row groups | 1 |
| Rows | 1,441 |
| Row-group row count | 1,441 |
| Columns | 81 |
| Schema | `time: int64` plus 80 `double` metric columns |
| Nulls | `time`: 0; four metric columns have nulls (below) |
| Timestamp column | `time` |
| Unique timestamps | 1,441 |
| Minimum timestamp | `1732242483` (`2024-11-22T02:28:03Z`) |
| Maximum timestamp | `1732243923` (`2024-11-22T02:52:03Z`) |
| Cadence | Exactly 1 second between all adjacent rows |
| Rows inside inclusive window | 1,441 |
| Rows before / after window | 0 / 0 |
| Explicit stable row ID | No |
| Timestamp uniqueness | `time` is unique, one row per timestep |
| Equal-timestamp ties | None |

Nonzero null counts:

| Column | Null count |
|---|---:|
| `carts-db_cpu` | 4 |
| `session-db_cpu` | 1 |
| `carts-db_diskio` | 4 |
| `session-db_diskio` | 161 |

All other metric columns have zero nulls. The `time` column is a unique timestamp key for the 1,441 timesteps, but it is not a declared row identifier.

Exact metric column families:

```text
time

carts_cpu
carts-db_cpu
catalogue_cpu
catalogue-db_cpu
front-end_cpu
orders_cpu
orders-db_cpu
payment_cpu
queue-master_cpu
rabbitmq_cpu
rabbitmq-exporter_cpu
session-db_cpu
shipping_cpu
user_cpu
user-db_cpu

carts_mem
carts-db_mem
catalogue_mem
catalogue-db_mem
front-end_mem
orders_mem
orders-db_mem
payment_mem
queue-master_mem
rabbitmq_mem
rabbitmq-exporter_mem
session-db_mem
shipping_mem
user_mem
user-db_mem

carts-db_diskio
catalogue-db_diskio
orders-db_diskio
rabbitmq_diskio
session-db_diskio
user-db_diskio

carts_socket
carts-db_socket
catalogue_socket
catalogue-db_socket
front-end_socket
orders_socket
orders-db_socket
payment_socket
queue-master_socket
rabbitmq_socket
rabbitmq-exporter_socket
session-db_socket
shipping_socket
user_socket
user-db_socket

carts_workload
catalogue_workload
front-end_workload
orders_workload
payment_workload
queue-master_workload
shipping_workload
user_workload

carts_error
front-end_error
orders_error
queue-master_error
shipping_error

carts_latency-50
catalogue_latency-50
front-end_latency-50
orders_latency-50
payment_latency-50
queue-master_latency-50
shipping_latency-50
user_latency-50

carts_latency-90
catalogue_latency-90
front-end_latency-90
orders_latency-90
payment_latency-90
queue-master_latency-90
shipping_latency-90
user_latency-90
```

## 4. Timestamp units and interval

### 4.1 Unit

Both time columns are plain `int64`; the Parquet metadata does not encode a timestamp logical type, timezone, or unit. The unit was verified from values and cross-file alignment, not from appearance:

- The values are 10-digit integers in the Unix-epoch range.
- `inject_time.txt` is `1732243203`, also a 10-digit integer.
- `1732243203` maps to `2024-11-22T02:40:03Z`.
- The metrics table has exactly 1,441 rows from `1732242483` through `1732243923`, with a 1-second cadence.
- `inject_time` is exactly 720 seconds after the minimum and 720 seconds before the maximum.
- Interpreting the same integers as milliseconds would place the event in January 1970, which is incompatible with the case timestamps and the 2024 log content.

Therefore the verified operational unit is **Unix epoch seconds**. No timezone offset is stored; epoch seconds denote UTC instants and all displayed conversions in this report use UTC. Selection must use the raw integer seconds, so it is independent of display timezone.

### 4.2 Interval

The inclusive interval is verified against the pinned telemetry:

`W = [1732242483, 1732243923]`

| Check | Result |
|---|---|
| `time_start` equals metrics and logs minimum | Yes |
| `time_end` equals metrics and logs maximum | Yes |
| Window span | 1,440 seconds = 24 minutes |
| `inject_time - time_start` | 720 seconds |
| `time_end - inject_time` | 720 seconds |
| Metrics rows before inject / at or after inject | 720 / 721 |
| Logs rows before inject / at or after inject | 43,180 / 41,485 |
| Metrics timesteps | 1,441, exactly one per second |

The previously reported `time_start = 1732242483` and `time_end = 1732243923` are correct for the pinned case. They are seconds, not milliseconds. The 720/721 metrics split matches Document 65's stated normal/faulty timestep count.

No `cases.parquet` or other label-bearing case index was downloaded. `inject_time.txt` plus the two telemetry timestamp ranges were sufficient to verify the interval.

## 5. Candidate service inventory

The permitted telemetry exposes these unranked component identifiers:

- **Observed in `logs.parquet`:** 13 values of `container_name`.
- **Observed in `metrics.parquet`:** 15 prefixes derived from the 80 metric column names.
- **Union of both telemetry sources:** 15 identifiers.
- **Logs-only identifiers:** none.
- **Metrics-only identifiers:** `catalogue-db`, `rabbitmq-exporter`.

Observed union, sorted lexicographically with no target marker and no ranking:

```text
carts
carts-db
catalogue
catalogue-db
front-end
orders
orders-db
payment
queue-master
rabbitmq
rabbitmq-exporter
session-db
shipping
user
user-db
```

### Completeness qualification

- **Verified complete service inventory:** **None established.** No authoritative service manifest is present in the three permitted artifacts.
- **Services merely observed:** the 13 log `container_name` values and the 15 metric prefixes above.
- **Completeness cannot be established for:** the union as a whole. The two sources disagree: two components appear only in metrics, and the logs do not prove that every deployed component emitted a line in this window. The metrics table also does not prove that the deployment contained no additional uninstrumented component.

This is not a claim that the 15-name union is the complete Sock Shop deployment. It is only the complete set observed in the permitted telemetry. The candidate list can be shown to an investigator only as an ordinary, unranked, unmarked inventory; it cannot be described as the verified complete inventory required by the current T1 freeze gate.

## 6. Deterministic row-selection algorithm

The following is the only admissible ordering procedure for T1 logs:

1. Read the immutable, hash-pinned `logs.parquet`.
2. Assign every row its original zero-based ordinal in physical read order: `0 .. 84,664`.
3. Select rows where `time_start <= timestamp <= time_end`, inclusive. All 84,665 rows satisfy this condition in the pinned file.
4. Sort selected rows by `(timestamp, tie_break)`.
5. For `tie_break`, use a verified stable row ID only if one exists. No such ID exists in this file: there is no ID column and no single unique column.
6. Because no stable ID exists, use the original zero-based row ordinal as the tie-breaker.
7. Preserve original row-group and batch order when assigning ordinals. This file has one row group and 84,665 rows, so the ordinal is exactly the physical row position in that group.
8. Do not use message text, service names, fault labels, error signatures, or target-bearing metadata to choose, filter, or rank rows.

This ordering is deterministic because the raw file is hash-pinned, has one row group, and has no descending timestamp pairs. The row identity remains `(timestamp, original ordinal)` even when many rows share a timestamp.

### Reproducibility probe

A canonical serialization of all 84,665 window rows, sorted by `(timestamp, original ordinal)`, was prepared twice from separate reads. Both runs produced:

`5dfd2eb7b689f485bb722b86eef5e6ce156662ff592668fd7b8082ed6de37ba9`

Both runs also contained 84,665 rows. This establishes deterministic ordering and serialization of the full window. It does **not** establish the final excerpt because `N_max` is not frozen.

## 7. `N_max` decision

**Status: BLOCKED.**

Document 65 does not contain a pre-registered numeric `N_max`. It contains this recommendation:

> “Let `N_max` be a pre-registered constant fixed before any label review (recommended: 2,000 rows). If the sorted row count exceeds `N_max`, select evenly spaced rows by index across the full sorted set; otherwise include all rows.”

The parenthetical **2,000** is explicitly a recommendation, not a frozen constant. No manifest exists with a numeric value, no manifest hash is recorded, and the phrase “evenly spaced rows by index” does not define endpoint rounding or behavior for `N_max = 1`.

I did not adopt 2,000 after inspecting the data. I did not select, preview, or rank an excerpt. The numeric value and exact index formula must be frozen prospectively before any label review.

### Recommended deterministic rule, not adopted

If the project later freezes a numeric `N_max >= 2`, the following rule is deterministic and should be recorded verbatim:

```text
M = number of rows in W after the timestamp filter
if M <= N_max:
    selected_indices = 0 .. M-1
else:
    selected_indices[i] = floor(i * (M - 1) / (N_max - 1))
    for i = 0 .. N_max - 1
```

The formula includes the first and last sorted rows and produces no duplicate indices when `2 <= N_max <= M`. The rows must still be ordered by `(timestamp, original zero-based ordinal)`. This is a recommendation only; it is not T1's frozen selection rule.

## 8. F1–F5 taxonomy

Document 65 contains the complete five-class taxonomy with the same definitions as Document 63:

| Code | Definition | Document 65 |
|---|---|---|
| **F1** | incorrect parameter values | Present |
| **F2** | missing parameters | Present |
| **F3** | missing function call | Present |
| **F4** | incorrect return values | Present |
| **F5** | missing exception handlers | Present |

The taxonomy is complete and can be shown to the investigator. This preflight did not derive, inspect, or record the target class or target service. The case slug was not decoded into a mapping, and no hidden label file was consulted.

## 9. Evidence-isolation assessment

### Verified layout

The preflight root is outside the Git repository. The actual resolved paths are:

- Repository: `C:\Users\Adi\Documents\ChatGPT\black`
- Staging: `%TEMP%\BLACKBOX_BDB5_T1_PREFLIGHT\staging\T1\raw\<case>\`
- Model-visible: `%TEMP%\BLACKBOX_BDB5_T1_PREFLIGHT\model_visible\T1\`
- Label vault: `%TEMP%\BLACKBOX_BDB5_T1_PREFLIGHT\label_vault\T1\` — **not created**

Verified conditions:

- Staging is outside the repository.
- Model-visible is outside the repository.
- Staging and model-visible are disjoint; they are not the same directory.
- `model_visible/T1` is empty: 0 files. No prompt, candidate list, excerpt, or raw path was placed there.
- The label-vault directory does not exist.
- No file matching `*root*cause*` exists anywhere under the preflight root.
- The only files under staging are the three permitted artifacts plus the staging hash manifest.
- No raw files were copied into model-visible.
- No hidden mapping or target-bearing metadata was copied anywhere.
- The candidate list in this report is unranked; no target marker or fault association is attached.

### What is not yet achieved

Directory separation is not access isolation. The current layout does not prove that a future inference process cannot read staging, the repository, Document 63/65, or the future label vault. A path check alone is not an access-control boundary.

Before any future inference, the following actual boundary is required:

1. Run inference under a dedicated unprivileged OS user or an isolated container, separate from the builder and scorer.
2. Mount only `model_visible/T1` into that environment, read-only.
3. Do not mount `staging/T1/raw`; do not mount `label_vault/T1`; do not mount the repository or any directory containing Documents 63/65.
4. Run the scorer in a separate process/namespace with access to the vault; the model-facing process must have no read permission to the vault or raw staging.
5. Ensure no environment variable, prompt, path string, log line, or metadata field reveals a raw staging path, target mapping, case slug, or hidden label.
6. Keep the staging files immutable and verify their SHA-256 values before and after preparation.
7. Make the sanitizer the only writer of model-visible output; make the model-facing process unable to write the staging or vault roots.
8. Run a negative access test: the inference principal must receive `permission denied` (or the platform-equivalent) when it attempts to read staging, the vault, and the repository. Directory names alone must not be accepted as evidence of isolation.

Because that enforcement has not been implemented or tested, physical evidence separation is **BLOCKED**, not passed.

## 10. PASS / FAIL / BLOCKED

| # | Gate | Status | Basis |
|---:|---|---|---|
| 1 | Dataset revision and artifact identity | **PASS** | Revision resolved; sizes and SHA-256 match HF LFS metadata; only permitted artifacts downloaded |
| 2 | Parquet schema | **PASS** | Schemas, row groups, row counts, dtypes, and nulls inspected directly |
| 3 | Timestamp units and interval | **PASS** | Unix epoch seconds verified by cross-file alignment; min/max equal `time_start`/`time_end`; 720/721 split verified |
| 4 | Stable row ordering | **PASS** | No stable ID; original zero-based ordinal is deterministic; one row group; nondecreasing order; full-window hash reproduced twice |
| 5 | Candidate service inventory | **BLOCKED** | Only a 15-name telemetry-observed union; no authoritative complete inventory; two metric-only components |
| 6 | F1–F5 taxonomy | **PASS** | All five definitions present in Document 65 and identical to Document 63 |
| 7 | `N_max` and row-selection rule | **BLOCKED** | Only a recommended 2,000; no frozen numeric value or exact formula; no excerpt selected |
| 8 | Physical evidence separation | **BLOCKED** | Layout is disjoint and model-visible is empty, but no OS/container read boundary is implemented or tested |
| 9 | Deterministic output reproduction | **BLOCKED** | Full-window ordering hash is reproducible; final excerpt hash cannot be produced until `N_max` is frozen |
| 10 | T1 manifest readiness | **BLOCKED** | Gates 5, 7, 8, and 9 are not satisfied; no manifest is frozen |

No gate is marked PASS merely because a directory exists or because a value looks plausible; each PASS above is tied to inspected bytes, schema metadata, or repeated deterministic output.

## 11. Remaining implementation dependencies

T1 cannot be frozen until all of the following are resolved:

1. **Freeze `N_max` and the exact index formula** in a manifest before any label review. Do not infer the value from observed log usefulness.
2. **Establish a complete candidate inventory** from an authoritative service manifest, or define and review a telemetry-derived completeness criterion. The current 15-name union is observed, not verified complete.
3. **Implement the actual access boundary** described in Section 9, including a negative permission test for staging, vault, and repository access.
4. **Build the telemetry adapter** that reads only the frozen window and row-ordering rule and emits evidence IDs; no telemetry ingestion path exists in the current checkout.
5. **Build the neutral model-visible package** without a prompt or target mapping. This preflight deliberately created none.
6. **Redact internal identifiers** from any future log excerpt, as required by Document 65.
7. **Freeze the manifest hash** after the inventory, window, ordering rule, `N_max`, and separation controls are verified.
8. **Independent review** of the manifest and label handling before any inference.

## 12. Git status delta

**Before this task's report:** `git status --porcelain` had **458** entries.

**After creating only this report:** the measured count is **459** entries:

```diff
+?? research/66_BDB5_T1_PREFLIGHT.md
```

- Added by this task: **1** file, `research/66_BDB5_T1_PREFLIGHT.md`.
- Removed: **0**.
- No tracked file was modified by this task.
- The 19 tracked modifications already present in the baseline remain untouched.
- `research/64_M4B3_AUDIT_REMEDIATION_REPORT.md`, `research/65_BDB5_PILOT_SPEC.md`, and the two root-level `research (3).zip` / `research (4).zip` entries were already present before this task and were not created or changed by it.
- No `git add`, `git commit`, `git reset`, `git clean`, or `git stash` was run.

## 13. What could not be verified

- A complete service inventory for the deployed Sock Shop system. The telemetry-observed union is 15 names, but completeness is not established.
- A pre-registered numeric `N_max`, its exact selection formula, or the final selected excerpt.
- Actual OS/container access isolation between inference, staging, and the future label vault.
- The target service, target fault class, root-cause line, or hidden mapping. These were intentionally not accessed.
- Any source-file, function, or line-level cause. RCAEval supplies no such label for T1, and no source revision was downloaded.
- Any model diagnosis, telemetry-adapter behavior, scoring result, benchmark execution, latency, or token count. None was run.
- A full-dataset or cross-case inventory check. Only the three permitted T1 artifacts were downloaded.
- Timezone encoded in the Parquet schema. No timezone metadata exists; epoch seconds were used as UTC instants for display, and the raw integers are what the selector must use.

## 14. Final decision

T1's data identity, schema, timestamp unit, interval, and deterministic ordinal ordering are verified. The candidate inventory is not complete, the numeric `N_max` is not frozen, the final excerpt cannot be produced, and the actual access boundary is not enforced.

**Final status:** `T1_PREFLIGHT_BLOCKED — NOT_EXECUTED — LIVE_INFERENCE_DISABLED`
