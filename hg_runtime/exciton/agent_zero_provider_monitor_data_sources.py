"""EXCITON Agent Zero Provider Monitor — read-only."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.live_provider.exciton_snapshot import build_provider_monitor_fields


def _build_panel(ctx: CollectorContext) -> Any:
    fields = build_provider_monitor_fields()
    freshness = fields.get("freshness_status", "missing")
    verdict = fields.get("verdict", "YELLOW_PROVIDER_UNAVAILABLE_DRY_AUTONOMY_RESTRICTED")

    if freshness == "missing" or verdict.startswith("RED_"):
        state = ExcitonPanelState.RED if verdict.startswith("RED_") else ExcitonPanelState.YELLOW
    elif freshness == "stale":
        state = ExcitonPanelState.YELLOW
    elif fields.get("provider_status") == "available" and verdict.startswith("GREEN_"):
        state = ExcitonPanelState.GREEN
    else:
        state = ExcitonPanelState.YELLOW

    fields.update(
        {
            "truth_state": verdict,
            "direct_external_actions_allowed": False,
            "publish_available": False,
            "send_available": False,
            "approve_available": False,
        }
    )
    return _panel("AgentZeroProviderMonitorPanel", state, fields)


def build_agent_zero_provider_monitor_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_provider_monitor_panels"]
