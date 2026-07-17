"""EXCITON provider visibility tests."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_provider_monitor_data_sources import build_agent_zero_provider_monitor_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.live_provider.exciton_snapshot import build_provider_monitor_fields


def test_provider_monitor_fields():
    fields = build_provider_monitor_fields()
    assert fields.get("publish_available") is False
    assert fields.get("send_available") is False
    assert "provider_kind" in fields
    assert "verdict" in fields


def test_exciton_panel_not_fake_green_without_health():
    panels = build_agent_zero_provider_monitor_panels(CollectorContext(offline_fixture=True))
    assert len(panels) == 1
    panel = panels[0]
    assert panel.panel_id == "AgentZeroProviderMonitorPanel"
    assert panel.state in (ExcitonPanelState.YELLOW, ExcitonPanelState.RED, ExcitonPanelState.GREEN)
    assert panel.fields.get("publish_available") is False
