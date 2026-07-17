"""EXCITON Agent Zero Live Read Monitor — read-only."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.live_read_endurance.exciton_snapshot import build_monitor_fields


def _build_panel(ctx: CollectorContext) -> Any:
    fields = build_monitor_fields()
    freshness = fields.get("freshness", "missing")
    verdict = fields.get("verdict", "YELLOW_LIVE_READ_CREDENTIALS_MISSING")

    if fields.get("write_scope_detected"):
        state = ExcitonPanelState.RED
    elif verdict.startswith("RED_"):
        state = ExcitonPanelState.RED
    elif freshness in ("missing", "stale", "credentials_missing", "unavailable"):
        state = ExcitonPanelState.YELLOW
    elif freshness == "empty_but_fresh":
        state = ExcitonPanelState.YELLOW
    elif verdict.startswith("GREEN_") and fields.get("last_read_receipt"):
        state = ExcitonPanelState.GREEN
    else:
        state = ExcitonPanelState.YELLOW

    fields.update(
        {
            "truth_state": verdict,
            "direct_external_actions_allowed": False,
            "publish_available": False,
            "send_available": False,
            "reply_available": False,
            "comment_available": False,
            "browser_available": False,
        }
    )
    return _panel("AgentZeroLiveReadMonitorPanel", state, fields)


def build_agent_zero_live_read_monitor_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_live_read_monitor_panels"]
