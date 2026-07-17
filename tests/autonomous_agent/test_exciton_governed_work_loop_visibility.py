"""EXCITON governed work visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_governed_work_loop_data_sources import build_agent_zero_governed_work_loop_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.governed_work_loop.exciton_snapshot import build_governed_work_loop_monitor_snapshot


def test_no_fake_live_green():
    snap = build_governed_work_loop_monitor_snapshot()
    assert snap["external_action_autonomous_green"] is False


def test_exciton_not_approval():
    snap = build_governed_work_loop_monitor_snapshot()
    assert snap.get("exciton_is_approval") is False


def test_panel():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_governed_work_loop_panels(ctx)[0]
    assert panel.panel_id == "AgentZeroGovernedWorkLoopMonitorPanel"
    assert panel.fields.get("live_write_buttons") is False
