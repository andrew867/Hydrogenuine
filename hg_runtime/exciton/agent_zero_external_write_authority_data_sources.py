"""EXCITON Agent Zero External Write Authority Monitor — read-only."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.external_write_authority.exciton_snapshot import build_monitor_snapshot


def _build_panel(ctx: CollectorContext) -> Any:
    snap = build_monitor_snapshot()
    fields = snap.to_payload()
    fields["panel_title"] = "Agent Zero External Write Authority Monitor"
    fields["truth_state"] = snap.verdict
    fields["direct_external_actions_allowed"] = False
    fields["publish_available"] = False
    fields["send_available"] = False
    fields["reply_available"] = False
    fields["comment_available"] = False
    fields["browser_available"] = False
    fields["live_write_buttons"] = False

    if snap.live_dispatch_allowed:
        state = ExcitonPanelState.RED
    elif fields.get("verdict", "").startswith("RED_"):
        state = ExcitonPanelState.RED
    elif snap.dry_run_only:
        state = ExcitonPanelState.YELLOW
    else:
        state = ExcitonPanelState.YELLOW

    return _panel("AgentZeroExternalWriteAuthorityMonitorPanel", state, fields)


def build_agent_zero_external_write_authority_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_external_write_authority_panels"]
