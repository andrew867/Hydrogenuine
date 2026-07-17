"""EXCITON Phase 22 hands-off session monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.hands_off_session.exciton_snapshot import build_hands_off_session_monitor_snapshot


def _build_panel(ctx: CollectorContext, session_id: str | None = None) -> Any:
    snap = build_hands_off_session_monitor_snapshot(session_id)
    fields = dict(snap)
    fields["panel_title"] = "Agent Zero Hands-Off Session Monitor"
    fields["direct_external_actions_allowed"] = False
    fields["publish_available"] = False
    fields["live_write_buttons"] = False

    if snap.get("external_action_autonomous_green"):
        state = ExcitonPanelState.RED
    elif snap.get("heartbeat_stale") and snap.get("foreground_status") == "running":
        state = ExcitonPanelState.YELLOW
    elif snap.get("fixed_turn_cap") or snap.get("fixed_duration_cap"):
        state = ExcitonPanelState.RED
    elif str(snap.get("verdict", "")).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif snap.get("foreground_status") == "none":
        state = ExcitonPanelState.YELLOW
    else:
        state = ExcitonPanelState.GREEN

    return _panel("AgentZeroHandsOffSessionMonitorPanel", state, fields)


def build_agent_zero_hands_off_session_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_hands_off_session_panels"]
