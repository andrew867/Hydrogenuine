"""EXCITON real soak visibility."""
from hg_runtime.exciton.agent_zero_real_soak_launch_data_sources import build_agent_zero_real_soak_launch_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.real_soak_launch.exciton_snapshot import build_real_soak_launch_monitor_snapshot


def test_no_live_buttons():
    snap = build_real_soak_launch_monitor_snapshot("missing")
    assert snap["live_action_buttons"] is False


def test_panel():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    p = build_agent_zero_real_soak_launch_panels(ctx)[0]
    assert p.panel_id == "AgentZeroRealSoakLaunchMonitorPanel"
