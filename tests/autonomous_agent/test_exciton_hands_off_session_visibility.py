"""EXCITON hands-off session visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_hands_off_session_data_sources import build_agent_zero_hands_off_session_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.hands_off_session.exciton_snapshot import build_hands_off_session_monitor_snapshot


def test_no_fake_green_external():
    snap = build_hands_off_session_monitor_snapshot()
    assert snap["external_action_autonomous_green"] is False


def test_scheduler_daemon_false():
    snap = build_hands_off_session_monitor_snapshot()
    assert snap["scheduler_allowed"] is False
    assert snap["daemon_allowed"] is False


def test_exciton_panel():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_hands_off_session_panels(ctx)[0]
    assert panel.panel_id == "AgentZeroHandsOffSessionMonitorPanel"
    assert panel.fields.get("live_write_buttons") is False


def test_stale_heartbeat_not_autonomous_green():
    snap = build_hands_off_session_monitor_snapshot()
    if snap.get("heartbeat_stale"):
        assert snap["external_action_autonomous_green"] is False
