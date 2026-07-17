"""EXCITON Phase 18 live smoke visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_phase18_live_smoke_data_sources import (
    build_agent_zero_phase18_live_smoke_panels,
    build_phase18_monitor_fields,
)
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.external_write_authority.live_smoke import Phase18Verdict


def test_exciton_not_approval():
    fields = build_phase18_monitor_fields()
    assert fields.get("exciton_is_approval") is False
    assert fields.get("live_write_buttons") is False


def test_exciton_no_green_without_platform_proof():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_phase18_live_smoke_panels(ctx)[0]
    assert panel.panel_id == "AgentZeroPhase18LiveSmokeMonitorPanel"
    if panel.fields.get("external_side_effect_count", 0) == 0:
        assert panel.state in (ExcitonPanelState.YELLOW, ExcitonPanelState.RED)


def test_default_verdict_yellow_ready():
    from hg_runtime.external_write_authority.live_smoke import reset_live_dispatch_count

    reset_live_dispatch_count()
    fields = build_phase18_monitor_fields()
    verdict = str(fields.get("verdict", ""))
    assert verdict.startswith("YELLOW_")
