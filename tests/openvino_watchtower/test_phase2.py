"""Phase 2 watchtower tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


@pytest.fixture()
def tmp_sessions(tmp_path, monkeypatch):
    root = tmp_path / "sessions"
    monkeypatch.setattr("hg_runtime.openvino_watchtower.session.SESSIONS_ROOT", root)
    monkeypatch.chdir(WORKSPACE)
    return root


def test_session_starts(tmp_sessions):
    from hg_runtime.openvino_watchtower.session import start_session, stop_session

    s = start_session()
    assert s.session_id
    assert s.manifest_path.is_file()
    stop_session()


def test_events_appended_to_session(tmp_sessions):
    from hg_runtime.openvino_watchtower.events import configure_events, emit_event
    from hg_runtime.openvino_watchtower.session import load_session, start_session, stop_session

    ev_path = tmp_sessions.parent / "live.jsonl"
    configure_events(path=ev_path)
    s = start_session()
    emit_event("WATCHTOWER_STARTED")
    stop_session()
    session = load_session(s.session_id)
    assert session.events_path.is_file()
    lines = session.events_path.read_text(encoding="utf-8").strip().splitlines()
    assert any("WATCHTOWER_STARTED" in ln for ln in lines)


def test_manifest_written(tmp_sessions):
    from hg_runtime.openvino_watchtower.session import start_session, stop_session

    s = start_session()
    stop_session()
    data = json.loads(s.manifest_path.read_text(encoding="utf-8"))
    assert data["session_id"] == s.session_id


def test_replay_reads_session(tmp_sessions):
    from hg_runtime.openvino_watchtower.replay import WatchtowerReplay
    from hg_runtime.openvino_watchtower.session import start_session, stop_session

    s = start_session()
    s.append_event({"event_type": "INFERENCE_STARTED", "ts": "2026-01-01T00:00:00+00:00"})
    s.write_snapshot({"freshness_verdict": "fresh", "authority_created": False})
    stop_session()
    replay = WatchtowerReplay.open(s.session_id)
    assert replay.snapshot() is not None
    assert replay.events()


def test_replay_does_not_mutate_runtime(tmp_sessions):
    from hg_runtime.openvino_watchtower.events import DEFAULT_EVENT_PATH, configure_events, emit_event
    from hg_runtime.openvino_watchtower.replay import WatchtowerReplay, LIVE_EVENTS
    from hg_runtime.openvino_watchtower.session import start_session, stop_session

    live = tmp_sessions.parent / "events.jsonl"
    configure_events(path=live)
    emit_event("WATCHTOWER_STARTED")
    before = live.read_text(encoding="utf-8") if live.is_file() else ""
    s = start_session()
    s.append_event({"event_type": "INFERENCE_STARTED", "ts": "2026-01-01T00:00:00+00:00"})
    stop_session()
    replay = WatchtowerReplay.open(s.session_id)
    replay.assert_read_only()
    _ = replay.events()
    after = live.read_text(encoding="utf-8") if live.is_file() else ""
    assert before == after


def test_redaction_preserved_in_session(tmp_sessions):
    from hg_runtime.openvino_watchtower.session import start_session, stop_session

    s = start_session()
    s.append_event({"event_type": "X", "ts": "t", "prompt": "secret prompt", "api_key": "sk-test"})
    stop_session()
    text = s.events_path.read_text(encoding="utf-8")
    assert "sk-test" not in text
    assert "secret prompt" not in text or "prompt_hash" in text


def test_organ_trace_builds(tmp_sessions):
    from hg_runtime.openvino_watchtower.organ_trace import build_organ_trace

    events = [
        {"event_type": "INFERENCE_STARTED", "organ_id": "WILL", "span_id": "s1", "ts": "t"},
        {"event_type": "INFERENCE_COMPLETED", "organ_id": "WILL", "span_id": "s1", "ts": "t"},
    ]
    trace = build_organ_trace(events)
    assert trace["edges"]
    assert "chain_of_thought" not in json.dumps(trace)


def test_missing_refs_yellow(tmp_sessions):
    from hg_runtime.openvino_watchtower.organ_trace import build_organ_trace

    trace = build_organ_trace([])
    assert trace["verdict"].startswith("YELLOW")


def test_fast_span_green(tmp_sessions):
    from hg_runtime.openvino_watchtower.performance_budget import evaluate_span

    assert evaluate_span({"duration_ms": 100, "first_token_ms": 100}) == "PERF_GREEN"


def test_slow_first_token_yellow(tmp_sessions):
    from hg_runtime.openvino_watchtower.performance_budget import evaluate_span

    assert evaluate_span({"duration_ms": 8000, "first_token_ms": 8000}) == "PERF_YELLOW_SLOW"


def test_timeout_red(tmp_sessions):
    from hg_runtime.openvino_watchtower.performance_budget import evaluate_span

    assert evaluate_span({"duration_ms": 200000, "first_token_ms": 20000, "status": "failed", "error": "timeout"}) == "PERF_RED_TIMEOUT"


def test_stale_snapshot_not_green(tmp_sessions):
    from hg_runtime.openvino_watchtower.performance_budget import evaluate_snapshot

    perf = evaluate_snapshot({"freshness_verdict": "stale", "freshness_age_ms": 90000})
    assert perf["verdict"] in {"PERF_STALE", "PERF_CONTACT_LOST", "PERF_YELLOW_SLOW"}


def test_budget_config_loads():
    from hg_runtime.openvino_watchtower.performance_budget import PerformanceBudget

    b = PerformanceBudget.load()
    assert b.warning_first_token_ms == 5000


def test_incident_export_creates_package(tmp_sessions, tmp_path, monkeypatch):
    from hg_runtime.openvino_watchtower.incident_export import export_incident
    from hg_runtime.openvino_watchtower.session import start_session, stop_session

    monkeypatch.setattr("hg_runtime.openvino_watchtower.incident_export.INCIDENTS_ROOT", tmp_path / "incidents")
    s = start_session()
    s.append_event({"event_type": "INFERENCE_FAILED", "ts": "t", "payload": {"error": "timeout"}})
    s.write_snapshot({"freshness_verdict": "fresh", "authority_created": False, "permission_granted": False})
    sid = s.session_id
    stop_session()
    out = export_incident(session_id=sid, incident_id="inc-test", reason="test")
    assert (out / "manifest.json").is_file()
    assert (out / "privacy_report.json").is_file()
    blob = (out / "redacted_events.jsonl").read_text(encoding="utf-8")
    assert "api_key" not in blob.lower() or "REDACTED" in blob


def test_simulator_scenarios(tmp_sessions):
    from hg_runtime.openvino_watchtower.simulator import SCENARIOS, simulate_scenario

    for sc in SCENARIOS:
        result = simulate_scenario(sc)
        assert result["fixture"] is True
        assert result["snapshot"]["data_tier"] == "FIXTURE"


def test_ui_phase2_views():
    html = (WORKSPACE / "apps/openvino_watchtower/index.html").read_text(encoding="utf-8").lower()
    js = (WORKSPACE / "apps/openvino_watchtower/app.js").read_text(encoding="utf-8").lower()
    for view in ("replay", "organ trace", "waterfall", "performance", "incidents", "privacy"):
        assert view.replace(" ", "-") in html or view in html
    assert "rendertrace" in js or "renderTrace".lower() in js
    assert "cdn" not in html


def test_exciton_phase2_fields():
    from hg_runtime.openvino_watchtower.exciton_panel import exciton_panel_fields

    fields = exciton_panel_fields(
        {
            "freshness_verdict": "fresh",
            "provider_status": {},
            "model_status": {},
            "device_status": {},
            "active_inference_spans": [],
            "organ_activity": {},
            "redaction": {},
            "phase2": {"replay_session_count": 2, "performance_budget": {"verdict": "PERF_GREEN"}},
            "performance_verdict": "PERF_GREEN",
        }
    )
    assert fields["replay_session_count"] == 2
    assert fields["authority_created"] is False
