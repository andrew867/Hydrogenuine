"""EXCITON Phase 21 task selection monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.task_selection.exciton_snapshot import build_task_selection_monitor_snapshot


def _build_panel(ctx: CollectorContext) -> Any:
    snap = build_task_selection_monitor_snapshot()
    fields = dict(snap)
    fields["panel_title"] = "Agent Zero Task Selection Monitor"
    fields["truth_state"] = snap.get("verdict")
    fields["direct_external_actions_allowed"] = False
    fields["publish_available"] = False
    fields["live_write_buttons"] = False

    if snap.get("external_action_autonomous_green"):
        state = ExcitonPanelState.RED
    elif str(snap.get("verdict", "")).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif not snap.get("task_receipt_refs") and snap.get("objective_universe_status") == "none":
        state = ExcitonPanelState.YELLOW
    else:
        state = ExcitonPanelState.GREEN

    return _panel("AgentZeroTaskSelectionMonitorPanel", state, fields)


def build_agent_zero_task_selection_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_task_selection_panels"]
