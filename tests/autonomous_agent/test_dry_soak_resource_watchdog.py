"""Dry soak resource watchdog tests."""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_soak.resource_watchdog import adjusted_turn_interval, collect_resource_snapshot
from hg_runtime.dry_soak.schema import DrySoakResourceSnapshot, now_iso


def test_records_snapshot(tmp_path):
    snap = collect_resource_snapshot(
        run_id="r1",
        turn_index=1,
        turn_duration_seconds=0.5,
        turn_base=tmp_path / "turns",
        dry_soak_root=tmp_path,
    )
    assert snap.run_id == "r1"
    assert snap.hash
    assert snap.verdict in ("GREEN_RESOURCE_OK", "YELLOW_RESOURCE_METRICS_PARTIAL")


def test_cannot_expand_authority_under_pressure():
    base_interval = 0.0
    pressured = DrySoakResourceSnapshot(
        run_id="r1",
        turn_index=1,
        observed_at=now_iso(),
        artifact_count=0,
        review_queue_count=0,
        turn_duration_seconds=1.0,
        disk_free_bytes=None,
        verdict="YELLOW_DRY_SOAK_RESOURCE_PRESSURE",
    )
    assert adjusted_turn_interval(base_interval, pressured) >= base_interval
