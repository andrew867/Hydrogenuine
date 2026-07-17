"""Continuity YELLOW closure."""

from __future__ import annotations

from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot


def test_self_mirror_continuity_not_unknown_live():
    snap = build_snapshot(AggregatorConfig(offline_fixture=False))
    sm = next(p for p in snap.panels if p.panel_id == "SelfMirrorPanel")
    assert sm.fields.get("continuity_status") in ("HIGH", "MEDIUM", "LOW")
    assert sm.fields.get("continuity_status") != "UNKNOWN"


def test_continuity_high_when_chrono_and_anchor_present():
    snap = build_snapshot(AggregatorConfig(offline_fixture=False))
    sm = next(p for p in snap.panels if p.panel_id == "SelfMirrorPanel")
    # With verified anchor + chrono lock evidence, continuity should be HIGH or MEDIUM
    assert sm.fields.get("continuity_status") in ("HIGH", "MEDIUM")
