"""EXCITON Phase 24.5 real soak launch monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.real_soak_launch.exciton_snapshot import build_real_soak_launch_monitor_snapshot


def _build_panel(ctx: CollectorContext) -> Any:
    snap = build_real_soak_launch_monitor_snapshot()
    fields = dict(snap)
    if snap.get("live_action_buttons"):
        state = ExcitonPanelState.RED
    elif str(snap.get("verdict", "")).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif snap.get("verdict", "").startswith("YELLOW"):
        state = ExcitonPanelState.YELLOW
    else:
        state = ExcitonPanelState.GREEN
    return _panel("AgentZeroRealSoakLaunchMonitorPanel", state, fields)


def build_agent_zero_real_soak_launch_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_real_soak_launch_panels"]
