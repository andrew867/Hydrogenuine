"""EXCITON task selection visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_task_selection_data_sources import build_agent_zero_task_selection_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.task_selection.exciton_snapshot import build_task_selection_monitor_snapshot


def test_monitor_no_fake_green_external():
    snap = build_task_selection_monitor_snapshot()
    assert snap["external_action_autonomous_green"] is False


def test_exciton_panel_requires_freshness_fields():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_task_selection_panels(ctx)[0]
    assert panel.panel_id == "AgentZeroTaskSelectionMonitorPanel"
    assert "freshness" in panel.fields or panel.fields.get("generated_at")


def test_exciton_no_live_write_buttons():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_task_selection_panels(ctx)[0]
    assert panel.fields.get("live_write_buttons") is False
    assert panel.fields.get("publish_available") is False
