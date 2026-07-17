"""Situational awareness UI integration tests."""

from __future__ import annotations

from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_html_has_situational_sections():
    html = (WORKSPACE / "apps/exciton/index.html").read_text(encoding="utf-8")
    assert "away-digest-panel" in html
    assert "timeline-list" in html
    assert "alert-strip" in html


def test_js_fetches_situational():
    js = (WORKSPACE / "apps/exciton/app.js").read_text(encoding="utf-8")
    assert "situational-awareness" in js
    assert "renderSituational" in js


def test_situational_panels_in_snapshot():
    from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot

    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    ids = {p.panel_id for p in snap.panels}
    assert "DataFreshnessPanel" in ids
    assert "AwayDigestPanel" in ids
