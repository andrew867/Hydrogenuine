"""EXCITON Agent Zero rehearsal monitor panel — read-only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.supervised_rehearsal.observer import assess_heartbeat_freshness
from hg_runtime.supervised_rehearsal.rehearsal_store import RehearsalStore, rehearsal_root
from hg_runtime.supervised_rehearsal.run_lock import lock_state, read_lock


def _discover_rehearsal_run_id() -> str | None:
    env_run = os.environ.get("HG_REHEARSAL_RUN_ID") or os.environ.get("HG_AGENT_ZERO_RUN_ID")
    if env_run:
        return env_run
    root = rehearsal_root()
    if not root.is_dir():
        return None
    runs = sorted(
        [p.name for p in root.iterdir() if p.is_dir() and (p / "run.json").is_file()],
        reverse=True,
    )
    return runs[0] if runs else None


def _build_rehearsal_monitor_panel(ctx: CollectorContext) -> Any:
    run_id = _discover_rehearsal_run_id()
    if not run_id:
        return _panel(
            "AgentZeroRehearsalMonitorPanel",
            ExcitonPanelState.RED,
            {
                "freshness_status": "missing",
                "source_refs": [],
                "truth_state": "RED_REHEARSAL_SOURCE_MISSING",
                "verdict": "RED_REHEARSAL_SOURCE_MISSING",
                "generated_at": None,
                "expires_at": None,
            },
            degraded_reason="no rehearsal run",
        )

    store = RehearsalStore(run_id)
    run = store.read_run() or {}
    result = store.read_result() or {}
    postflight = store.read_postflight() or {}
    heartbeat = store.latest_observer_heartbeat()
    freshness = assess_heartbeat_freshness(heartbeat)
    lock = read_lock()

    if freshness == "missing":
        state = ExcitonPanelState.RED
        verdict = "RED_REHEARSAL_HEARTBEAT_MISSING"
    elif freshness == "stale":
        state = ExcitonPanelState.YELLOW
        verdict = "YELLOW_REHEARSAL_HEARTBEAT_STALE"
    else:
        state = ExcitonPanelState.GREEN if run else ExcitonPanelState.YELLOW
        verdict = run.get("verdict", result.get("verdict", "YELLOW_REHEARSAL_IDLE"))

    fields = {
        "run_id": run_id,
        "lock_state": lock_state().value,
        "turn_count": run.get("turn_count", result.get("turn_count", 0)),
        "last_heartbeat": heartbeat.get("observed_at") if heartbeat else None,
        "freshness_status": freshness,
        "stop_available": heartbeat.get("stop_available", True) if heartbeat else True,
        "panic_available": heartbeat.get("panic_available", True) if heartbeat else True,
        "last_turn_verdict": (result.get("turn_summaries") or [{}])[-1].get("verdict") if result.get("turn_summaries") else None,
        "artifact_count": postflight.get("artifact_count", 0),
        "review_candidate_count": postflight.get("review_candidate_count", 0),
        "run_status": run.get("status"),
        "source_refs": [str(store.root)],
        "source_ref_count": 1,
        "truth_state": verdict,
        "generated_at": heartbeat.get("observed_at") if heartbeat else run.get("started_at"),
        "expires_at": None,
        "verdict": verdict,
        "direct_external_actions_allowed": False,
        "approve_available": False,
        "publish_available": False,
        "send_available": False,
        "data_tier": "FIXTURE" if ctx.offline_fixture else "LIVE",
    }
    return _panel("AgentZeroRehearsalMonitorPanel", state, fields)


def build_agent_zero_rehearsal_panels(ctx: CollectorContext) -> list:
    return [_build_rehearsal_monitor_panel(ctx)]


__all__ = ["build_agent_zero_rehearsal_panels"]
