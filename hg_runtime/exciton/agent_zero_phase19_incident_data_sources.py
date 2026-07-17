"""EXCITON Phase 19 external action audit / incident monitor."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.external_write_authority.action_ledger import Phase19Verdict
from hg_runtime.external_write_authority.phase19_snapshot import build_phase19_monitor_snapshot


def _build_panel(ctx: CollectorContext) -> Any:
    snap = build_phase19_monitor_snapshot()
    fields = snap.to_payload()
    fields["panel_title"] = "Agent Zero External Action Audit / Incident Monitor"
    fields["truth_state"] = snap.verdict
    fields["direct_external_actions_allowed"] = False
    fields["publish_available"] = False

    if str(snap.verdict).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif snap.verdict == Phase19Verdict.GREEN:
        state = ExcitonPanelState.GREEN
    else:
        state = ExcitonPanelState.YELLOW

    return _panel("AgentZeroPhase19IncidentMonitorPanel", state, fields)


def build_agent_zero_phase19_incident_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_phase19_incident_panels"]
