"""EXCITON live read visibility tests."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_live_read_monitor_data_sources import build_agent_zero_live_read_monitor_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.live_read_endurance.exciton_snapshot import build_monitor_fields


def test_monitor_fields_read_only():
    fields = build_monitor_fields()
    assert fields.get("publish_available") is False
    assert fields.get("send_available") is False
    assert fields.get("read_only_status") is True
    assert "verdict" in fields


def test_exciton_panel_credentials_missing_not_green():
    panels = build_agent_zero_live_read_monitor_panels(CollectorContext(offline_fixture=True))
    assert len(panels) == 1
    panel = panels[0]
    assert panel.panel_id == "AgentZeroLiveReadMonitorPanel"
    assert panel.state != ExcitonPanelState.GREEN or panel.fields.get("last_read_receipt")
    assert panel.fields.get("browser_available") is False


def test_exciton_write_scope_red(monkeypatch):
    monkeypatch.setattr(
        "hg_runtime.live_read_endurance.credential_scope._write_scope_detected",
        lambda: True,
    )
    panels = build_agent_zero_live_read_monitor_panels(CollectorContext(offline_fixture=False))
    assert panels[0].state == ExcitonPanelState.RED
