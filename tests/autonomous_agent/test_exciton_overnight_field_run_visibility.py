"""EXCITON overnight field run visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_overnight_field_run_data_sources import build_agent_zero_overnight_field_run_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.overnight_field_run.exciton_snapshot import build_overnight_field_run_monitor_snapshot


def test_monitor_snapshot_no_live_buttons():
    snap = build_overnight_field_run_monitor_snapshot("nonexistent-run")
    assert snap["live_action_buttons"] is False
    assert snap["publish_available"] is False
    assert snap["panel_title"] == "Agent Zero Overnight Field Run Monitor"


def test_exciton_panel_builds():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_overnight_field_run_panels(ctx)[0]
    assert panel.panel_id == "AgentZeroOvernightFieldRunMonitorPanel"
    assert panel.fields.get("live_action_buttons") is False
