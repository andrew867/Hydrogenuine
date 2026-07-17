"""EXCITON external write authority visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_external_write_authority_data_sources import (
    build_agent_zero_external_write_authority_panels,
)
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.external_write_authority.exciton_snapshot import build_monitor_snapshot


def test_monitor_shows_dry_run_only():
    snap = build_monitor_snapshot()
    assert snap.dry_run_only is True
    assert snap.live_dispatch_allowed is False


def test_exciton_no_published_green():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panels = build_agent_zero_external_write_authority_panels(ctx)
    assert len(panels) == 1
    panel = panels[0]
    assert panel.panel_id == "AgentZeroExternalWriteAuthorityMonitorPanel"
    assert panel.state in (ExcitonPanelState.YELLOW, ExcitonPanelState.RED)
    assert panel.fields.get("publish_available") is False
    assert panel.fields.get("live_write_buttons") is False


def test_exciton_no_live_write_buttons():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_external_write_authority_panels(ctx)[0]
    forbidden = panel.fields.get("direct_external_actions_allowed")
    assert forbidden is False
