"""EXCITON social review queue panel tests."""

from __future__ import annotations

from hg_runtime.exciton.phase3_data_sources import build_phase3_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.panel_registry import PHASE_3_REQUIRED_PANELS


def test_phase3_panels_present_offline():
    panels = build_phase3_panels(CollectorContext(offline_fixture=True))
    ids = {p.panel_id for p in panels}
    for pid in PHASE_3_REQUIRED_PANELS:
        assert pid in ids


def test_approve_all_not_available_offline():
    panels = build_phase3_panels(CollectorContext(offline_fixture=True))
    decision = next(p for p in panels if p.panel_id == "SocialApprovalDecisionPanel")
    assert decision.fields.get("approve_all_available") is False
    assert decision.fields.get("direct_publish_available") is False
