"""Real panel data tiers — no fake GREEN."""

from __future__ import annotations

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.exciton.panel_registry import ALL_PANEL_CONTRACTS, PHASE_2_REQUIRED_PANELS
from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot


def test_all_panels_have_data_tier_live():
    snap = build_snapshot(AggregatorConfig(offline_fixture=False))
    for p in snap.panels:
        tier = p.fields.get("data_tier")
        assert tier in ("LIVE", "LIVE_IDLE", "FIXTURE"), f"{p.panel_id} missing data_tier"


def test_fixture_mode_labels_fixture():
    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    for p in snap.panels:
        assert p.fields.get("data_tier") == "FIXTURE"


def test_phase2_panels_present():
    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    ids = {p.panel_id for p in snap.panels}
    for pid in PHASE_2_REQUIRED_PANELS:
        assert pid in ids


def test_no_secrets_in_snapshot():
    snap = build_snapshot(AggregatorConfig(offline_fixture=False))
    payload = snap.to_payload()
    assert not scan_forbidden(payload)


def test_green_panels_have_contract():
    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    contracts = {c.panel_id for c in ALL_PANEL_CONTRACTS}
    for p in snap.panels:
        if p.state.value == "GREEN":
            assert p.panel_id in contracts
