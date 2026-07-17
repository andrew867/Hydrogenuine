"""EXCITON dry soak monitor panel — read-only."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.dry_soak.storage import dry_soak_root, run_dry_soak_dir
from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.supervised_rehearsal.observer import assess_heartbeat_freshness
from hg_runtime.supervised_rehearsal.run_lock import lock_state, read_lock


def _discover_dry_soak_run_id() -> str | None:
    env_run = os.environ.get("HG_DRY_SOAK_RUN_ID") or os.environ.get("HG_AGENT_ZERO_RUN_ID")
    if env_run:
        return env_run
    root = dry_soak_root()
    if not root.is_dir():
        return None
    runs = sorted(
        [p.name for p in root.iterdir() if p.is_dir() and (p / "run.json").is_file()],
        reverse=True,
    )
    return runs[0] if runs else None


def _build_dry_soak_monitor_panel(ctx: CollectorContext) -> Any:
    run_id = _discover_dry_soak_run_id()
    if not run_id:
        return _panel(
            "AgentZeroDrySoakMonitorPanel",
            ExcitonPanelState.RED,
            {
                "freshness_status": "missing",
                "source_refs": [],
                "truth_state": "RED_DRY_SOAK_SOURCE_MISSING",
                "verdict": "RED_DRY_SOAK_SOURCE_MISSING",
                "generated_at": None,
                "expires_at": None,
                "direct_external_actions_allowed": False,
                "publish_available": False,
                "send_available": False,
            },
            degraded_reason="no dry soak run",
        )

    root = run_dry_soak_dir(run_id)
    run = {}
    exciton = {}
    if (root / "run.json").is_file():
        run = json.loads((root / "run.json").read_text(encoding="utf-8"))
    if (root / "exciton_snapshot.json").is_file():
        exciton = json.loads((root / "exciton_snapshot.json").read_text(encoding="utf-8"))

    heartbeat_at = exciton.get("last_heartbeat") or run.get("started_at")
    freshness = assess_heartbeat_freshness({"observed_at": heartbeat_at} if heartbeat_at else None)
    lock = read_lock(base=dry_soak_root())

    if freshness == "missing":
        state = ExcitonPanelState.RED
        verdict = "RED_DRY_SOAK_HEARTBEAT_MISSING"
    elif freshness == "stale":
        state = ExcitonPanelState.YELLOW
        verdict = "YELLOW_DRY_SOAK_HEARTBEAT_STALE"
    else:
        panel_state = exciton.get("panel_state", "YELLOW")
        try:
            state = ExcitonPanelState(panel_state)
        except ValueError:
            state = ExcitonPanelState.YELLOW
        verdict = exciton.get("truth_state") or run.get("verdict", "YELLOW_DRY_SOAK_IDLE")

    fields = {
        "run_id": run_id,
        "run_status": run.get("status") or exciton.get("run_status"),
        "turn_count": run.get("turn_count", exciton.get("turn_count", 0)),
        "elapsed_seconds": exciton.get("elapsed_seconds", 0),
        "lock_state": lock_state(base=dry_soak_root()).value,
        "stop_available": exciton.get("stop_available", True),
        "panic_available": exciton.get("panic_available", True),
        "last_heartbeat": heartbeat_at,
        "freshness_status": freshness,
        "provider_status": exciton.get("provider_status", "unknown"),
        "live_read_status": exciton.get("live_read_status", "unknown"),
        "artifact_count": exciton.get("artifact_count", 0),
        "review_queue_count": exciton.get("review_queue_count", 0),
        "duplicate_body_hash_rate": exciton.get("duplicate_body_hash_rate", 0.0),
        "resource_verdict": exciton.get("resource_verdict", "unknown"),
        "failure_budget_verdict": exciton.get("failure_budget_verdict", "unknown"),
        "source_refs": [str(root)],
        "source_ref_count": 1,
        "truth_state": verdict,
        "generated_at": heartbeat_at,
        "expires_at": None,
        "verdict": run.get("verdict", verdict),
        "direct_external_actions_allowed": False,
        "approve_available": False,
        "publish_available": False,
        "send_available": False,
    }
    return _panel("AgentZeroDrySoakMonitorPanel", state, fields)


def build_agent_zero_dry_soak_panels(ctx: CollectorContext) -> list:
    return [_build_dry_soak_monitor_panel(ctx)]


__all__ = ["build_agent_zero_dry_soak_panels"]
