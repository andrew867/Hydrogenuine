"""EXCITON extended dry autonomy monitor panel — read-only."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.extended_dry_autonomy.exciton_snapshot import build_exciton_panel_fields
from hg_runtime.extended_dry_autonomy.extended_lock import lock_state
from hg_runtime.extended_dry_autonomy.storage import extended_root, run_dir
from hg_runtime.supervised_rehearsal.observer import assess_heartbeat_freshness


def _discover_run_id() -> str | None:
    env_run = os.environ.get("HG_EXTENDED_DRY_AUTONOMY_RUN_ID") or os.environ.get("HG_AGENT_ZERO_RUN_ID")
    if env_run:
        return env_run
    root = extended_root()
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
            "AgentZeroExtendedDryAutonomyMonitorPanel",
            ExcitonPanelState.RED,
            {
                "freshness_status": "missing",
                "truth_state": "RED_EXTENDED_DRY_SOURCE_MISSING",
                "verdict": "RED_EXTENDED_DRY_SOURCE_MISSING",
                "direct_external_actions_allowed": False,
                "publish_available": False,
                "send_available": False,
            },
            degraded_reason="no extended dry autonomy run",
        )

    root = run_dir(run_id)
    fields = build_exciton_panel_fields(run_id)
    hb_lines = (root / "heartbeats.jsonl").read_text(encoding="utf-8").strip().splitlines() if (root / "heartbeats.jsonl").is_file() else []
    last_hb = json.loads(hb_lines[-1]) if hb_lines else {}
    heartbeat_at = last_hb.get("observed_at")
    freshness = assess_heartbeat_freshness({"observed_at": heartbeat_at} if heartbeat_at else None)

    anchor_path = root / "anchor_audit.json"
    anchor_verdict = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"
    if anchor_path.is_file():
        anchor_verdict = json.loads(anchor_path.read_text(encoding="utf-8")).get("verdict", anchor_verdict)

    if freshness == "missing":
        state = ExcitonPanelState.RED
        verdict = "RED_EXTENDED_DRY_HEARTBEAT_MISSING"
    elif freshness == "stale":
        state = ExcitonPanelState.YELLOW
        verdict = fields.get("verdict", "YELLOW_EXTENDED_DRY_HEARTBEAT_STALE")
    elif anchor_verdict == "GREEN_REMOTE_ANCHOR_FRESH":
        state = ExcitonPanelState.GREEN if str(fields.get("verdict", "")).startswith("GREEN_") else ExcitonPanelState.YELLOW
        verdict = fields.get("verdict", anchor_verdict)
    elif anchor_verdict.startswith("YELLOW_"):
        state = ExcitonPanelState.YELLOW
        verdict = fields.get("verdict", anchor_verdict)
    else:
        lv = fields.get("verdict", "YELLOW_EXTENDED_DRY_IDLE")
        state = ExcitonPanelState.GREEN if str(lv).startswith("GREEN_") else ExcitonPanelState.YELLOW
        verdict = lv

    fields.update(
        {
            "freshness_status": freshness,
            "lock_state": lock_state().value,
            "remote_anchor_status": anchor_verdict,
            "truth_state": verdict,
            "verdict": verdict,
            "direct_external_actions_allowed": False,
            "publish_available": False,
            "send_available": False,
            "approve_available": False,
        }
    )
    return _panel("AgentZeroExtendedDryAutonomyMonitorPanel", state, fields)


def build_agent_zero_extended_dry_autonomy_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_extended_dry_autonomy_panels"]
