"""EXCITON extended dry autonomy monitor snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.extended_dry_autonomy.extended_lock import lock_state
from hg_runtime.extended_dry_autonomy.storage import run_dir, write_json


def write_exciton_snapshot(
    run_id: str,
    heartbeat: dict[str, Any],
    *,
    config: dict[str, Any],
    extended_base: Path | None = None,
) -> Path:
    snapshot = {
        "panel_id": "AgentZeroExtendedDryAutonomyMonitorPanel",
        "title": "Agent Zero Extended Dry Autonomy Monitor",
        "run_id": run_id,
        "status": heartbeat.get("verdict"),
        "iteration_count": heartbeat.get("iteration_index", 0),
        "max_iterations": config.get("max_iterations", 0),
        "elapsed_seconds": heartbeat.get("elapsed_seconds", 0),
        "max_duration_seconds": config.get("max_duration_seconds", 0),
        "last_heartbeat": heartbeat.get("observed_at"),
        "freshness_status": "fresh",
        "lock_state": lock_state(base=extended_base).value,
        "stop_available": True,
        "panic_available": True,
        "pause_state": heartbeat.get("pause_state", "running"),
        "checkpoint_status": heartbeat.get("checkpoint_status", "none"),
        "provider_status": heartbeat.get("provider_status"),
        "live_read_status": heartbeat.get("live_read_status"),
        "artifact_count": heartbeat.get("artifact_count", 0),
        "review_queue_count": heartbeat.get("review_queue_count", 0),
        "duplication_status": heartbeat.get("duplication_status"),
        "resource_status": heartbeat.get("resource_status"),
        "endurance_budget_status": heartbeat.get("endurance_budget_status"),
        "last_turn_verdict": heartbeat.get("last_turn_verdict"),
        "direct_external_actions_allowed": False,
        "publish_available": False,
        "send_available": False,
        "approve_available": False,
    }
    return write_json(run_dir(run_id, base=extended_base) / "exciton_snapshot.json", snapshot)


def build_exciton_panel_fields(run_id: str, *, extended_base: Path | None = None) -> dict[str, Any]:
    root = run_dir(run_id, base=extended_base)
    snap_path = root / "exciton_snapshot.json"
    if snap_path.is_file():
        return json.loads(snap_path.read_text(encoding="utf-8"))
    return {
        "panel_id": "AgentZeroExtendedDryAutonomyMonitorPanel",
        "truth_state": "RED_EXTENDED_DRY_SOURCE_MISSING",
        "verdict": "RED_EXTENDED_DRY_SOURCE_MISSING",
        "freshness_status": "missing",
        "direct_external_actions_allowed": False,
        "publish_available": False,
        "send_available": False,
    }


__all__ = ["build_exciton_panel_fields", "write_exciton_snapshot"]
