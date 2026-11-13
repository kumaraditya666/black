from __future__ import annotations

import json
from pathlib import Path

import pytest

from blackbox.bdb5.review import review_payload
from blackbox.bdb5.telemetry import (
    T1_INJECT_TIME,
    T1_N_MAX,
    T1_WINDOW_END,
    T1_WINDOW_START,
    TelemetryError,
    build_t1_payload,
    load_inventory,
    make_log_evidence,
    select_evenly_spaced,
    select_log_rows,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "fixtures" / "bdb5" / "t1" / "service_inventory.json"


def _metrics() -> dict[str, list[object]]:
    return {
        "time": [T1_WINDOW_START + index for index in range(1_441)],
        "carts_cpu": [0.1] * 1_441,
    }


def _logs(count: int = 2_001) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "ordinal": index,
            "timestamp": T1_WINDOW_START + (index // 100),
            "container_name": "carts",
            "message": "ordinary request log",
        }
        for index in range(count)
    )


def _payload():
    services, _ = load_inventory(INVENTORY)
    return build_t1_payload(
        log_rows=_logs(),
        metrics=_metrics(),
        inject_time=T1_INJECT_TIME,
        inventory=services,
        raw_hashes={
            "logs.parquet": "a" * 64,
            "metrics.parquet": "b" * 64,
            "inject_time.txt": "c" * 64,
        },
        inventory_source="test reference",
        inventory_status="TEST_REFERENCE_ONLY",
    )


def test_t1_constants_are_frozen():
    assert T1_N_MAX == 2_000
    assert (T1_WINDOW_START, T1_WINDOW_END) == (1_732_242_483, 1_732_243_923)
    assert T1_INJECT_TIME == 1_732_243_203


def test_even_selection_is_complete_deterministic_and_bounded():
    indices = select_evenly_spaced(84_665, T1_N_MAX)
    assert len(indices) == T1_N_MAX
    assert len(set(indices)) == T1_N_MAX
    assert indices[0] == 0
    assert indices[-1] == 84_664
    assert indices == select_evenly_spaced(84_665, T1_N_MAX)


def test_log_selection_uses_original_ordinal_for_ties():
    rows = (
        {"ordinal": 2, "timestamp": 10, "container_name": "b", "message": "x"},
        {"ordinal": 1, "timestamp": 10, "container_name": "a", "message": "y"},
        {"ordinal": 0, "timestamp": 9, "container_name": "a", "message": "z"},
    )
    selected = select_log_rows(rows, n_max=3)
    assert [row["ordinal"] for row in selected] == [0, 1, 2]


def test_payload_has_frozen_n_max_complete_metrics_and_2000_logs():
    payload = _payload()
    packet = payload["model_visible_packet"]
    telemetry = payload["evaluator_only"]["telemetry"]
    assert payload["readiness"] == "PREPARED"
    assert packet["case_id"] == "BDB5-T1"
    assert packet["source_revision"] is None
    assert telemetry["n_max"] == T1_N_MAX
    assert telemetry["metric_rows"] == 1_441
    assert telemetry["selected_log_rows"] == 2_000
    assert len(packet["candidate_inventory"]) == 15
    assert any(item["evidence_type"] == "TELEMETRY_METRIC" for item in packet["evidence"])
    assert any(item["evidence_type"] == "TELEMETRY_LOG" for item in packet["evidence"])
    assert payload["evaluator_only"]["packet_validation"]["issues"] == []


def test_payload_omits_label_and_source_fields():
    visible = json.dumps(_payload()["model_visible_packet"]).lower()
    assert "root_cause" not in visible
    assert "gold_patch" not in visible
    assert "test_patch" not in visible
    assert "fix_commit" not in visible


def test_log_evidence_chunks_stay_under_text_limit():
    rows = tuple(
        {
            "ordinal": index,
            "timestamp": T1_WINDOW_START + index,
            "container_name": "svc",
            "message": "m" * 400,
        }
        for index in range(300)
    )
    chunks = make_log_evidence(rows)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 20_000 for chunk in chunks)
    assert sum(len(chunk.structured["ordinals"]) for chunk in chunks) == 300


def test_inventory_must_be_sorted_and_unique(tmp_path):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps({"services": ["b", "a"]}), encoding="utf-8")
    with pytest.raises(TelemetryError, match="sorted and unique"):
        load_inventory(path)


def test_review_accepts_t1_prepared_payload():
    review = review_payload(_payload())
    assert review.passed, review.issues
    assert review.case_id == "BDB5-T1"
    assert review.status == "REVIEW_PASSED"
    assert review.payload()["approved"] is False
