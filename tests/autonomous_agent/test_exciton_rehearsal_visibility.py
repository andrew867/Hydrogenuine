"""EXCITON rehearsal visibility tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.exciton.agent_zero_rehearsal_data_sources import build_agent_zero_rehearsal_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.panel_registry import CONTRACT_BY_ID
from hg_runtime.exciton.schema import ExcitonPanelState


def test_rehearsal_panel_registered():
    assert "AgentZeroRehearsalMonitorPanel" in CONTRACT_BY_ID
    contract = CONTRACT_BY_ID["AgentZeroRehearsalMonitorPanel"]
    assert "publish_social" in contract.forbidden_controls


def test_panel_has_truth_freshness_when_no_run():
    panels = build_agent_zero_rehearsal_panels(CollectorContext(offline_fixture=False))
    assert len(panels) == 1
    panel = panels[0]
    assert panel.fields.get("truth_state")
    assert panel.fields.get("freshness_status") is not None or panel.state == ExcitonPanelState.RED


def test_stale_heartbeat_not_green():
    panels = build_agent_zero_rehearsal_panels(CollectorContext(offline_fixture=True))
    panel = panels[0]
    if panel.fields.get("freshness_status") == "stale":
        assert panel.state != ExcitonPanelState.GREEN


def test_no_publish_buttons():
    contract = CONTRACT_BY_ID["AgentZeroRehearsalMonitorPanel"]
    assert "approve" not in contract.allowed_controls
    assert "publish_social" in contract.forbidden_controls
