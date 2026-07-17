"""EXCITON Agent Zero review visibility tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.exciton.agent_zero_review_data_sources import (
    build_agent_zero_review_panels,
    build_agent_zero_review_snapshot_fields,
)
from hg_runtime.exciton.control_api import ExcitonControlAPI
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.panel_registry import CONTRACT_BY_ID
from hg_runtime.exciton.schema import ExcitonPanelState


def test_review_panels_registered():
    for pid in ("AgentZeroReviewQueuePanel", "AgentZeroTurnTracePanel", "AgentZeroArtifactQualityPanel"):
        assert pid in CONTRACT_BY_ID
        contract = CONTRACT_BY_ID[pid]
        assert "approve" not in contract.allowed_controls
        assert "publish_social" in contract.forbidden_controls


def test_panels_have_truth_freshness_source():
    panels = build_agent_zero_review_panels(CollectorContext(offline_fixture=True))
    assert len(panels) == 3
    for panel in panels:
        assert "truth_state" in panel.fields
        assert "freshness_status" in panel.fields
        assert "verdict" in panel.fields


def test_snapshot_fields_in_status_api():
    api = ExcitonControlAPI(offline_fixture=True)
    status = api.get_status()
    for key in ("agent_zero_review_queue", "agent_zero_turn_trace", "agent_zero_artifact_quality"):
        assert key in status
        block = status[key]
        assert block.get("truth_state")
        assert "freshness_status" in block
        assert "source_refs" in block
        assert "verdict" in block


def test_no_approve_publish_send_buttons_in_contracts():
    for pid in ("AgentZeroReviewQueuePanel", "AgentZeroArtifactQualityPanel"):
        forbidden = CONTRACT_BY_ID[pid].forbidden_controls
        assert "publish_social" in forbidden
        assert "send_email" in forbidden


def test_fixture_offline_panel_not_fake_green_without_source():
    fields = build_agent_zero_review_snapshot_fields(CollectorContext(offline_fixture=True))
    for key, block in fields.items():
        if not block.get("source_refs"):
            assert block.get("panel_state") != ExcitonPanelState.GREEN.value
