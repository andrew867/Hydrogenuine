"""EXCITON Phase 23 governed work loop monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.governed_work_loop.exciton_snapshot import build_governed_work_loop_monitor_snapshot


def _build_panel(ctx: CollectorContext) -> Any:
    snap = build_governed_work_loop_monitor_snapshot()
    fields = dict(snap)
    fields["panel_title"] = "Agent Zero Governed Work Loop Monitor"
    fields["direct_external_actions_allowed"] = False
    fields["publish_available"] = False
    fields["live_write_buttons"] = False

    if snap.get("external_action_autonomous_green"):
        state = ExcitonPanelState.RED
    elif str(snap.get("verdict", "")).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif snap.get("verdict", "").startswith("YELLOW"):
        state = ExcitonPanelState.YELLOW
    else:
        state = ExcitonPanelState.GREEN

    return _panel("AgentZeroGovernedWorkLoopMonitorPanel", state, fields)


def build_agent_zero_governed_work_loop_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_governed_work_loop_panels"]
