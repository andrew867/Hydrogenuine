"""EXCITON Phase 0 — status aggregator tests."""

from __future__ import annotations

from hg_runtime.exciton.panel_registry import (
    CONTRACT_BY_ID,
    INFERENCE_WATCHTOWER_REQUIRED_PANELS,
    AGENT_ZERO_CONSOLE_REQUIRED_PANELS,
    PHASE_1_REQUIRED_PANELS,
    PHASE_2_REQUIRED_PANELS,
    PHASE_3_REQUIRED_PANELS,
    REQUIRED_PANELS,
    SITUATIONAL_REQUIRED_PANELS,
    missing_required_panels,
)
from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot


def _snap(**kw):
    return build_snapshot(AggregatorConfig(offline_fixture=True, **kw)).to_payload()


def test_snapshot_validates_required_keys():
    p = _snap()
    for key in (
        "schema", "version", "snapshot_id", "generated_at", "chrono_ref",
        "overall_verdict", "panels", "snapshot_hash", "refresh_policy",
        "dangerous_actions_disabled", "stop_available", "panic_available",
    ):
        assert key in p


def test_snapshot_hash_stable_across_builds():
    assert _snap()["snapshot_hash"] == _snap()["snapshot_hash"]


def test_frozen_advisory_constants():
    p = _snap()
    assert p["advisory_only"] is True
    assert p["permission_granted"] is False
    assert p["authority_created"] is False


def test_all_required_panels_present():
    p = _snap()
    ids = [panel["panel_id"] for panel in p["panels"]]
    assert missing_required_panels(ids) == []
    # Contract migration M3: the snapshot grew to include the Phase-3 social-review, situational
    # awareness, and inference-watchtower panels. The count contract now spans every registered
    # group, every emitted panel must be registered (no orphan panels), and none may duplicate.
    expected = (
        set(REQUIRED_PANELS)
        | set(PHASE_1_REQUIRED_PANELS)
        | set(PHASE_2_REQUIRED_PANELS)
        | set(PHASE_3_REQUIRED_PANELS)
        | set(SITUATIONAL_REQUIRED_PANELS)
        | set(INFERENCE_WATCHTOWER_REQUIRED_PANELS)
        | set(AGENT_ZERO_CONSOLE_REQUIRED_PANELS)
    )
    assert set(ids) == expected
    assert len(ids) == len(expected)
    assert [i for i in ids if i not in CONTRACT_BY_ID] == []


def test_snapshot_includes_temporal_context():
    p = _snap()
    temporal = next(x for x in p["panels"] if x["panel_id"] == "TemporalPanel")
    assert temporal["fields"].get("current_time")
    assert p["chrono_ref"]


def test_degraded_source_is_honest_not_fake_green():
    p = _snap()
    audio = next(x for x in p["panels"] if x["panel_id"] == "AudioPanel")
    assert audio["state"] == "DEGRADED"
    assert audio["degraded"]["degraded"] is True
    assert audio["degraded"]["reason"]
    # overall verdict reflects degradation honestly (allowed YELLOW), never fake green.
    assert p["overall_verdict"].startswith("YELLOW")


def test_live_mode_does_not_crash_and_degrades_safely():
    p = build_snapshot(AggregatorConfig(offline_fixture=False)).to_payload()
    ids = [panel["panel_id"] for panel in p["panels"]]
    assert missing_required_panels(ids) == []
    assert len(ids) >= len(REQUIRED_PANELS)
    assert p["permission_granted"] is False


def test_refresh_policy_is_bounded():
    p = _snap()
    assert p["refresh_policy"]["bounded"] is True
    assert p["refresh_policy"]["background_autonomy"] is False
    assert p["refresh_policy"]["interval_seconds"] >= p["refresh_policy"]["min_interval_seconds"]
