"""Tests for FilePersonaStore, ArtifactStore, and SteeringSink (Phase 4)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hg_cognition.persona.quad import QuadCoords
from hg_cognition.schemas.common import MeditationReport, Score, SteeringRecommendation
from hg_cognition.integrations.memory_impls import JsonlArtifactStore

from hg_bridge.integrations import FilePersonaStore, ContextualSteeringSink, RealtimeSteeringSink


def test_jsonl_artifact_store_write_report(tmp_path):
    """JsonlArtifactStore write_report then read file; line present with report_id and correlation_id."""
    path = tmp_path / "reports.jsonl"
    store = JsonlArtifactStore(str(path))
    report = MeditationReport(
        report_id="rep-1",
        correlation_id="corr-1",
        window_start_ts=1000.0,
        window_end_ts=2000.0,
        scores=[Score("x", 0.5, 1, [], "sid-1")],
        persona_updates={},
        signature_updates={},
        contradictions=[],
        steering_recommendations=[],
        summary="ok",
    )
    store.write_report(report)
    content = path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert len(lines) == 1
    assert "rep-1" in lines[0]
    assert "corr-1" in lines[0]


def test_realtime_steering_sink_mock_adapter():
    """RealtimeSteeringSink submit(recs) calls adapter.submit with SteeringEvent (kind, payload, context)."""
    submitted = []
    mock_adapter = MagicMock()
    def capture(ev):
        submitted.append(ev)
    mock_adapter.submit = capture

    sink = RealtimeSteeringSink(
        mock_adapter,
        tenant_id="tenant-x",
        actor_id="actor-y",
        correlation_id="corr-z",
        run_id="run-1",
    )
    recs = [
        SteeringRecommendation(kind="profile_switch", strength=0.7, payload={"profile": "focus"}, reason="r1", stable_id="s1"),
        SteeringRecommendation(kind="constraint_nudge", strength=0.5, payload={"mode": "strict"}, reason="r2", stable_id="s2"),
    ]
    sink.submit(recs)

    assert len(submitted) == 2
    assert submitted[0].tenant_id == "tenant-x"
    assert submitted[0].actor_id == "actor-y"
    assert submitted[0].correlation_id == "corr-z"
    assert submitted[0].run_id == "run-1"
    assert submitted[0].kind == "profile_switch"
    assert submitted[0].payload == {"profile": "focus"}
    assert submitted[1].kind == "constraint_nudge"
    assert submitted[1].payload == {"mode": "strict"}


def test_file_persona_store_roundtrip(tmp_path):
    """FilePersonaStore save then load returns same QuadCoords."""
    store = FilePersonaStore(tmp_path)
    hist = [QuadCoords(0.1, 0.2, 0.3), QuadCoords(-0.5, 0.5, 0.4)]
    store.save_history("agent1", hist)
    loaded = store.load_history("agent1")
    assert len(loaded) == 2
    assert loaded[0].x == 0.1 and loaded[0].y == 0.2 and loaded[0].confidence == 0.3
    assert loaded[1].x == -0.5 and loaded[1].y == 0.5


def test_file_persona_store_empty_missing(tmp_path):
    """FilePersonaStore load_history returns [] for missing actor."""
    store = FilePersonaStore(tmp_path)
    assert store.load_history("nonexistent") == []


def test_contextual_steering_sink_submit(tmp_path):
    """ContextualSteeringSink set_context then submit calls adapter with correct event."""
    from hg_realtime.steering.file_adapter import FileSteeringAdapter
    path = tmp_path / "steering.jsonl"
    adapter = FileSteeringAdapter(path)
    sink = ContextualSteeringSink(adapter)
    sink.set_context(tenant_id="t1", actor_id="a1", correlation_id="c1", run_id="r1")
    recs = [
        SteeringRecommendation(kind="profile_switch", strength=0.8, payload={"profile": "x"}, reason="test", stable_id="id1"),
    ]
    sink.submit(recs)
    content = path.read_text(encoding="utf-8")
    assert "profile_switch" in content
    assert "t1" in content and "c1" in content
