"""EXCITON Phase 24 overnight field run monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.overnight_field_run.exciton_snapshot import build_overnight_field_run_monitor_snapshot


def _build_panel(ctx: CollectorContext) -> Any:
    snap = build_overnight_field_run_monitor_snapshot()
    fields = dict(snap)
    fields["panel_title"] = "Agent Zero Overnight Field Run Monitor"

    if snap.get("overnight_green_eligible") and snap.get("infrastructure_only"):
        state = ExcitonPanelState.RED
    elif str(snap.get("verdict", "")).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif snap.get("verdict", "").startswith("YELLOW"):
        state = ExcitonPanelState.YELLOW
    else:
        state = ExcitonPanelState.GREEN

    return _panel("AgentZeroOvernightFieldRunMonitorPanel", state, fields)


def build_agent_zero_overnight_field_run_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_overnight_field_run_panels"]
