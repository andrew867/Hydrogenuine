"""EXCITON Phase 19 incident visibility."""
from __future__ import annotations

from hg_runtime.exciton.agent_zero_phase19_incident_data_sources import build_agent_zero_phase19_incident_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.external_write_authority.action_ledger import Phase19Verdict
from hg_runtime.external_write_authority.phase19_snapshot import build_phase19_monitor_snapshot


def test_exciton_not_approval():
    snap = build_phase19_monitor_snapshot()
    assert snap.to_payload()["exciton_is_approval"] is False


def test_exciton_cannot_fake_green_without_proof():
    ctx = CollectorContext(offline_fixture=True, allow_network=False)
    panel = build_agent_zero_phase19_incident_panels(ctx)[0]
    assert panel.panel_id == "AgentZeroPhase19IncidentMonitorPanel"
    if not panel.fields.get("phase18_live_proof_exists"):
        assert panel.state != ExcitonPanelState.GREEN or panel.fields.get("verdict") == Phase19Verdict.GREEN


def test_default_yellow_readiness():
    snap = build_phase19_monitor_snapshot()
    if not snap.phase18_live_proof_exists:
        assert snap.verdict == Phase19Verdict.YELLOW_NO_PROOF
