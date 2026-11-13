"""Preparation adapter for the real RCAEval BDB5-T1 telemetry case.

The adapter is deliberately preparation-only. It reads only the three
model-eligible telemetry artifacts, builds a deterministic log excerpt and a
complete metrics table, and never reads the evaluator label file or calls a
model.

The raw files are not bundled in the repository. Callers must pass a directory
containing the exact pinned artifacts. PyArrow is required only when reading
Parquet; the deterministic packet builder is import-safe without it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .models import (
    CaseCategory,
    CaseId,
    CaseManifest,
    EvidenceItem,
    EvidencePacket,
    EvidenceType,
    Readiness,
)
from .scoring import canonical_json, digest
from .validation import validate_packet


T1_N_MAX = 2_000
T1_WINDOW_START = 1_732_242_483
T1_WINDOW_END = 1_732_243_923
T1_INJECT_TIME = 1_732_243_203
T1_DATASET = "RCAEval"
T1_DATASET_REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
T1_ADAPTER = "rcaeval-telemetry-v1"
T1_REQUIRED_DIMENSIONS = (
    "service_top1",
    "service_top3",
    "fault_accuracy",
    "citation_validity",
    "citation_coverage",
    "l1_causal_status",
    "l2_causal_status",
    "l2_abstention",
    "unsupported_claim_rate",
)
T1_TASK_INSTRUCTIONS = (
    "This is a telemetry investigation for the incident window. The metrics "
    "table is complete for the window. The logs are a deterministic, unranked "
    "excerpt from the same window. Identify the single most likely faulty "
    "service and exactly one fault class from the supplied F1-F5 taxonomy. "
    "Cite the telemetry evidence you rely on. If the packet does not establish "
    "a source-level cause, state that the source cause is NOT_ESTABLISHED and "
    "identify the missing evidence. Do not invent a source revision, stack "
    "frame, test result, or execution. Return both a service prediction and a "
    "fault-class prediction."
)
T1_ARTIFACTS = {
    "logs.parquet": {
        "bytes": 1_003_956,
        "sha256": "eea9d351ff71dbd1eb2bf77a39db60dc8dc1cead962d8672ffb41627dae9bfbb",
    },
    "metrics.parquet": {
        "bytes": 187_614,
        "sha256": "8a20a7caba8f268e725d4921ccae887ab1b30c1741019ccd06992ea784e7ff32",
    },
    "inject_time.txt": {
        "bytes": 10,
        "sha256": "a130a8d9d14b547fe9a14b4858f82958380ce8a796bf7bc4fa8b482a14316ed8",
    },
}


class TelemetryError(ValueError):
    """The telemetry input is incomplete, malformed or outside its pin."""


@dataclass(frozen=True)
class SelectedTelemetry:
    """The deterministic, label-free slice sent to a future model."""

    log_rows: tuple[dict[str, Any], ...]
    metrics: Mapping[str, Sequence[Any]]
    inject_time: int
    inventory: tuple[str, ...]
    raw_hashes: dict[str, str]

    @property
    def selected_log_count(self) -> int:
        return len(self.log_rows)

    @property
    def metric_rows(self) -> int:
        return len(self.metrics["time"])


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_artifact(path: Path, *, expected_bytes: int, expected_sha256: str) -> str:
    if not path.is_file():
        raise TelemetryError(f"missing telemetry artifact: {path.name}")
    size = path.stat().st_size
    if size != expected_bytes:
        raise TelemetryError(
            f"{path.name} has {size} bytes; expected {expected_bytes}"
        )
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise TelemetryError(f"{path.name} SHA-256 does not match the pinned artifact")
    return actual


def read_inject_time(path: Path) -> int:
    text = path.read_text(encoding="ascii").strip()
    try:
        value = int(text)
    except ValueError as exc:
        raise TelemetryError("inject_time.txt must contain one integer") from exc
    if value != T1_INJECT_TIME:
        raise TelemetryError(f"inject_time is {value}; expected {T1_INJECT_TIME}")
    return value


def _require_pyarrow():
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise TelemetryError(
            "pyarrow is required to read the pinned RCAEval Parquet artifacts"
        ) from exc
    return parquet


def read_logs(path: Path) -> tuple[dict[str, Any], ...]:
    parquet = _require_pyarrow()
    table = parquet.read_table(path)
    expected = ["timestamp", "container_name", "message"]
    if table.schema.names != expected:
        raise TelemetryError(
            f"logs.parquet schema is {table.schema.names}; expected {expected}"
        )
    rows = table.to_pylist()
    if len(rows) != 84_665:
        raise TelemetryError(f"logs.parquet has {len(rows)} rows; expected 84665")
    result: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows):
        timestamp = row.get("timestamp")
        container = row.get("container_name")
        if not isinstance(timestamp, int):
            raise TelemetryError(f"log row {ordinal} has a non-integer timestamp")
        if not isinstance(container, str):
            raise TelemetryError(f"log row {ordinal} has a non-string container")
        result.append(
            {
                "ordinal": ordinal,
                "timestamp": timestamp,
                "container_name": container,
                "message": row.get("message"),
            }
        )
    if any(row["timestamp"] < T1_WINDOW_START or row["timestamp"] > T1_WINDOW_END for row in result):
        raise TelemetryError("logs.parquet contains rows outside the pinned window")
    return tuple(result)


def read_metrics(path: Path) -> dict[str, list[Any]]:
    parquet = _require_pyarrow()
    table = parquet.read_table(path)
    if "time" not in table.schema.names or len(table.schema.names) != 81:
        raise TelemetryError("metrics.parquet must contain time plus 80 metric columns")
    metrics = table.to_pydict()
    times = metrics.get("time")
    if not isinstance(times, list) or len(times) != 1_441:
        raise TelemetryError("metrics.parquet must contain 1441 timesteps")
    if times[0] != T1_WINDOW_START or times[-1] != T1_WINDOW_END:
        raise TelemetryError("metrics.parquet does not span the pinned window")
    if any(times[index] + 1 != times[index + 1] for index in range(len(times) - 1)):
        raise TelemetryError("metrics.parquet must have a one-second cadence")
    return {name: list(values) for name, values in metrics.items()}


def select_evenly_spaced(count: int, n_max: int = T1_N_MAX) -> tuple[int, ...]:
    """Choose deterministic indices across the full sorted set.

    The first and last rows are always retained. The integer floor rule is
    stable and does not depend on floating point or host libraries.
    """
    if count <= 0:
        raise TelemetryError("cannot select from an empty telemetry set")
    if n_max <= 0:
        raise TelemetryError("N_max must be positive")
    if n_max >= count:
        return tuple(range(count))
    if n_max == 1:
        return (0,)
    return tuple(index * (count - 1) // (n_max - 1) for index in range(n_max))


def select_log_rows(
    rows: Sequence[dict[str, Any]], n_max: int = T1_N_MAX
) -> tuple[dict[str, Any], ...]:
    ordered = sorted(rows, key=lambda item: (item["timestamp"], item["ordinal"]))
    indices = select_evenly_spaced(len(ordered), n_max)
    return tuple(ordered[index] for index in indices)


def _evidence_hash(case_id: CaseId, item: EvidenceItem) -> str:
    return digest(
        {
            "case_id": case_id.value,
            "evidence_id": item.evidence_id,
            "evidence_type": item.evidence_type.value,
            "text": item.text,
            "structured": item.structured,
        }
    )


def make_metric_evidence(
    metrics: Mapping[str, Sequence[Any]], inject_time: int
) -> EvidenceItem:
    times = metrics["time"]
    return EvidenceItem(
        evidence_id="metric:1",
        evidence_type=EvidenceType.TELEMETRY_METRIC,
        text=(
            f"Complete metrics table: {len(times)} one-second timesteps, "
            f"80 metric columns, window {T1_WINDOW_START}-{T1_WINDOW_END}, "
            f"injection time {inject_time}. Null metric values remain null."
        ),
        structured={
            "window_start": T1_WINDOW_START,
            "window_end": T1_WINDOW_END,
            "inject_time": inject_time,
            "timestamps": list(times),
            "columns": {name: list(values) for name, values in metrics.items() if name != "time"},
        },
    )


def make_log_evidence(rows: Sequence[dict[str, Any]]) -> tuple[EvidenceItem, ...]:
    if not rows:
        raise TelemetryError("log excerpt is empty")
    chunks: list[EvidenceItem] = []
    current: list[str] = []
    current_size = 0
    chunk_number = 1
    ordinals: list[int] = []
    timestamps: list[int] = []

    def flush() -> None:
        nonlocal current, current_size, chunk_number, ordinals, timestamps
        if not current:
            return
        chunks.append(
            EvidenceItem(
                evidence_id=f"log:{chunk_number}",
                evidence_type=EvidenceType.TELEMETRY_LOG,
                text="\n".join(current),
                structured={
                    "ordinals": ordinals,
                    "timestamps": timestamps,
                    "selection": "evenly-spaced-by-timestamp-then-original-ordinal",
                },
            )
        )
        chunk_number += 1
        current = []
        current_size = 0
        ordinals = []
        timestamps = []

    for row in rows:
        message = row.get("message")
        message = "" if message is None else str(message)
        message = message.replace("\r", "").replace("\n", "\\n")
        line = (
            f"row={row['ordinal']} ts={row['timestamp']} "
            f"container={row['container_name']} {message}"
        )
        if current and current_size + len(line) + 1 > 18_000:
            flush()
        current.append(line)
        current_size += len(line) + 1
        ordinals.append(int(row["ordinal"]))
        timestamps.append(int(row["timestamp"]))
    flush()
    return tuple(chunks)


def build_t1_payload(
    *,
    log_rows: Sequence[dict[str, Any]],
    metrics: Mapping[str, Sequence[Any]],
    inject_time: int,
    inventory: Sequence[str],
    raw_hashes: Mapping[str, str],
    inventory_source: str,
    inventory_status: str,
    n_max: int = T1_N_MAX,
) -> dict[str, Any]:
    """Build the deterministic prepared payload without reading any label."""
    if n_max != T1_N_MAX:
        raise TelemetryError(f"N_max is frozen at {T1_N_MAX}; got {n_max}")
    if inject_time != T1_INJECT_TIME:
        raise TelemetryError("inject_time does not match the frozen T1 constant")
    services = tuple(inventory)
    if len(services) < 2 or services != tuple(sorted(services)):
        raise TelemetryError("inventory must be lexicographically sorted and unranked")
    if len(services) != len(set(services)):
        raise TelemetryError("inventory must not contain duplicates")
    if len(metrics.get("time", ())) != 1_441:
        raise TelemetryError("metrics table is incomplete")
    if not log_rows:
        raise TelemetryError("log table is empty")

    selected = select_log_rows(log_rows, n_max)
    metric_evidence = make_metric_evidence(metrics, inject_time)
    log_evidence = make_log_evidence(selected)
    evidence = (metric_evidence, *log_evidence)

    artifact_hashes = {
        f"artifact:{name}": hasher for name, hasher in raw_hashes.items()
    }
    artifact_hashes.update(
        {f"artifact:{item.evidence_id.replace(':', '-')}": _evidence_hash(CaseId.T1, item)
         for item in evidence}
    )

    packet = EvidencePacket(
        case_id=CaseId.T1,
        task_instructions=T1_TASK_INSTRUCTIONS,
        evidence=evidence,
        candidate_inventory=services,
        source_revision=None,
        artifact_hashes=artifact_hashes,
    )
    manifest = CaseManifest(
        case_id=CaseId.T1,
        dataset=T1_DATASET,
        dataset_revision=T1_DATASET_REVISION,
        repository=None,
        source_revision=None,
        case_category=CaseCategory.TELEMETRY,
        required_evidence_types=(EvidenceType.TELEMETRY_METRIC, EvidenceType.TELEMETRY_LOG),
        allowed_files=(),
        allowed_scope=(),
        required_dimensions=T1_REQUIRED_DIMENSIONS,
        readiness=Readiness.PREPARED,
        adapter_requirements=(T1_ADAPTER,),
        artifact_hashes=artifact_hashes,
        synthetic=False,
    )
    report = validate_packet(manifest, packet)
    if not report.passed:
        raise TelemetryError(
            "prepared telemetry packet failed validation: "
            + ", ".join(item.code for item in report.errors)
        )

    telemetry_meta = {
        "window_start": T1_WINDOW_START,
        "window_end": T1_WINDOW_END,
        "inject_time": inject_time,
        "n_max": n_max,
        "log_rows_total": len(log_rows),
        "selected_log_rows": len(selected),
        "metric_rows": len(metrics["time"]),
        "metric_columns": 80,
        "inventory_source": inventory_source,
        "inventory_status": inventory_status,
        "inventory": list(services),
        "raw_hashes": dict(sorted(raw_hashes.items())),
    }
    return {
        "mode": "REAL_CASE_PREPARATION_ONLY",
        "model_calls": 0,
        "case_id": CaseId.T1.value,
        "readiness": Readiness.PREPARED.value,
        "model_visible_packet": packet.model_visible_payload(),
        "evaluator_only": {
            "manifest": manifest.model_dump(mode="json"),
            "packet_validation": report.model_dump(mode="json"),
            "telemetry": telemetry_meta,
        },
        "payload_hash": digest(
            {
                "case_id": CaseId.T1.value,
                "manifest": manifest.model_dump(mode="json"),
                "packet": packet.model_visible_payload(),
                "telemetry": telemetry_meta,
            }
        ),
    }


def load_inventory(path: Path) -> tuple[tuple[str, ...], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TelemetryError("inventory file must be a JSON object")
    services = payload.get("services")
    if not isinstance(services, list) or not services:
        raise TelemetryError("inventory file requires a non-empty services list")
    if any(not isinstance(item, str) or not item.strip() for item in services):
        raise TelemetryError("inventory service names must be non-empty strings")
    tuple_services = tuple(services)
    if tuple_services != tuple(sorted(tuple_services)) or len(tuple_services) != len(set(tuple_services)):
        raise TelemetryError("inventory services must be sorted and unique")
    return tuple_services, payload


def prepare_t1_case(
    raw_dir: Path, inventory_path: Path, *, n_max: int = T1_N_MAX
) -> dict[str, Any]:
    """Read the pinned raw files and return a prepared, unapproved payload."""
    hashes: dict[str, str] = {}
    for name, expected in T1_ARTIFACTS.items():
        hashes[name] = verify_artifact(
            raw_dir / name,
            expected_bytes=expected["bytes"],
            expected_sha256=expected["sha256"],
        )
    if (raw_dir / "root_cause.txt").exists():
        raise TelemetryError(
            "raw directory contains a label file; use a model-eligible staging directory"
        )

    inventory, inventory_payload = load_inventory(inventory_path)
    logs = read_logs(raw_dir / "logs.parquet")
    metrics = read_metrics(raw_dir / "metrics.parquet")
    inject_time = read_inject_time(raw_dir / "inject_time.txt")

    source = inventory_payload.get("source", {})
    if not isinstance(source, dict):
        source = {}
    inventory_source = str(
        source.get("description")
        or inventory_payload.get("source_description")
        or "pinned T1 service inventory"
    )
    inventory_status = str(
        inventory_payload.get("status", "UNVERIFIED_INVENTORY")
    )
    return build_t1_payload(
        log_rows=logs,
        metrics=metrics,
        inject_time=inject_time,
        inventory=inventory,
        raw_hashes=hashes,
        inventory_source=inventory_source,
        inventory_status=inventory_status,
        n_max=n_max,
    )


__all__ = [
    "T1_ADAPTER",
    "T1_ARTIFACTS",
    "T1_DATASET",
    "T1_DATASET_REVISION",
    "T1_INJECT_TIME",
    "T1_N_MAX",
    "T1_REQUIRED_DIMENSIONS",
    "T1_TASK_INSTRUCTIONS",
    "T1_WINDOW_END",
    "T1_WINDOW_START",
    "SelectedTelemetry",
    "TelemetryError",
    "build_t1_payload",
    "load_inventory",
    "make_log_evidence",
    "make_metric_evidence",
    "prepare_t1_case",
    "read_inject_time",
    "read_logs",
    "read_metrics",
    "select_evenly_spaced",
    "select_log_rows",
    "sha256_file",
    "verify_artifact",
]
