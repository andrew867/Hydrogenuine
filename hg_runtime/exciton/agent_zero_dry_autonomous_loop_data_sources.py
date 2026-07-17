"""EXCITON dry autonomous loop monitor panel — read-only."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.dry_autonomous_loop.storage import loop_root, run_loop_dir
from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.dry_autonomous_loop.loop_lock import lock_state
from hg_runtime.supervised_rehearsal.observer import assess_heartbeat_freshness


def _discover_run_id() -> str | None:
    env_run = os.environ.get("HG_DRY_AUTONOMOUS_LOOP_RUN_ID") or os.environ.get("HG_AGENT_ZERO_RUN_ID")
    if env_run:
        return env_run
    root = loop_root()
    if not root.is_dir():
        return None
    runs = sorted(
        [p.name for p in root.iterdir() if p.is_dir() and (p / "run.json").is_file()],
        reverse=True,
    )
    return runs[0] if runs else None


def _build_panel(ctx: CollectorContext) -> Any:
    run_id = _discover_run_id()
    if not run_id:
        return _panel(
            "AgentZeroDryAutonomousLoopMonitorPanel",
            ExcitonPanelState.RED,
            {
                "freshness_status": "missing",
                "truth_state": "RED_DRY_LOOP_SOURCE_MISSING",
                "verdict": "RED_DRY_LOOP_SOURCE_MISSING",
                "direct_external_actions_allowed": False,
                "publish_available": False,
                "send_available": False,
            },
            degraded_reason="no dry autonomous loop run",
        )

    root = run_loop_dir(run_id)
    run = json.loads((root / "run.json").read_text(encoding="utf-8")) if (root / "run.json").is_file() else {}
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8")) if (root / "config.json").is_file() else {}
    hb_lines = (root / "heartbeats.jsonl").read_text(encoding="utf-8").strip().splitlines() if (root / "heartbeats.jsonl").is_file() else []
    last_hb = json.loads(hb_lines[-1]) if hb_lines else {}

    heartbeat_at = last_hb.get("observed_at") or run.get("started_at")
    freshness = assess_heartbeat_freshness({"observed_at": heartbeat_at} if heartbeat_at else None)

    if freshness == "missing":
        state = ExcitonPanelState.RED
        verdict = "RED_DRY_LOOP_HEARTBEAT_MISSING"
    elif freshness == "stale":
        state = ExcitonPanelState.YELLOW
        verdict = "YELLOW_DRY_LOOP_HEARTBEAT_STALE"
    else:
        lv = run.get("verdict", "YELLOW_DRY_LOOP_IDLE")
        state = ExcitonPanelState.GREEN if str(lv).startswith("GREEN_") else ExcitonPanelState.YELLOW
        verdict = lv

    fields = {
        "run_id": run_id,
        "status": run.get("status"),
        "iteration_count": run.get("iteration_count", 0),
        "max_iterations": cfg.get("max_iterations", 0),
        "elapsed_seconds": last_hb.get("elapsed_seconds", 0),
        "max_duration_seconds": cfg.get("max_duration_seconds", 0),
        "lock_state": lock_state(base=loop_root()).value,
        "stop_available": True,
        "panic_available": True,
        "last_heartbeat": heartbeat_at,
        "freshness_status": freshness,
        "provider_status": last_hb.get("provider_status", "unknown"),
        "live_read_status": last_hb.get("live_read_status", "unknown"),
        "artifact_count": last_hb.get("artifact_count", 0),
        "review_queue_count": last_hb.get("review_queue_count", 0),
        "failure_budget_status": last_hb.get("failure_budget_status", "unknown"),
        "last_turn_verdict": last_hb.get("last_turn_verdict"),
        "truth_state": verdict,
        "verdict": run.get("verdict", verdict),
        "direct_external_actions_allowed": False,
        "approve_available": False,
        "publish_available": False,
        "send_available": False,
    }
    return _panel("AgentZeroDryAutonomousLoopMonitorPanel", state, fields)


def build_agent_zero_dry_autonomous_loop_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_dry_autonomous_loop_panels"]
