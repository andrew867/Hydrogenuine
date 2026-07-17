"""Tests for OpenVINO Watchtower."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


@pytest.fixture()
def watchtower_env(monkeypatch, tmp_path):
    root = tmp_path / "watchtower"
    monkeypatch.setenv("HG_OPENVINO_WATCHTOWER_ENABLED", "true")
    monkeypatch.chdir(WORKSPACE)
    yield root


def test_schema_validates_event():
    from hg_runtime.openvino_watchtower.schema import InferenceEvent, validate_event_dict

    ev = InferenceEvent("WATCHTOWER_STARTED").to_dict()
    assert validate_event_dict(ev) == []


def test_event_append_writes_jsonl(watchtower_env, tmp_path):
    from hg_runtime.openvino_watchtower.events import configure_events, emit_event, read_recent_events

    path = tmp_path / "events.jsonl"
    configure_events(path=path)
    emit_event("WATCHTOWER_STARTED")
    assert path.is_file()
    events = read_recent_events(path=path)
    assert events[-1]["event_type"] == "WATCHTOWER_STARTED"


def test_snapshot_generated(watchtower_env):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.store import WatchtowerStore

    store = WatchtowerStore(root=watchtower_env)
    collector = OpenVINOWatchtowerCollector(store=store)
    snap = collector.snapshot()
    assert snap["snapshot_id"]
    assert store.snapshot_path.is_file()


def test_freshness_age_computed():
    from hg_runtime.openvino_watchtower.snapshot import compute_freshness

    now = datetime.now(timezone.utc)
    ts = (now - timedelta(seconds=5)).isoformat()
    fresh = compute_freshness(ts, now=now)
    assert fresh.freshness_verdict == "fresh"
    assert fresh.freshness_age_ms >= 5000


def test_stale_snapshot_becomes_stale():
    from hg_runtime.openvino_watchtower.snapshot import compute_freshness

    now = datetime.now(timezone.utc)
    ts = (now - timedelta(seconds=150)).isoformat()
    fresh = compute_freshness(ts, now=now)
    assert fresh.freshness_verdict == "stale"


def test_contact_lost():
    from hg_runtime.openvino_watchtower.snapshot import compute_freshness

    now = datetime.now(timezone.utc)
    ts = (now - timedelta(seconds=400)).isoformat()
    fresh = compute_freshness(ts, now=now)
    assert fresh.freshness_verdict == "contact_lost"


def test_provider_unavailable_not_fake_green():
    from hg_runtime.openvino_watchtower.snapshot import panel_state_for_snapshot

    snap = {
        "freshness_verdict": "fresh",
        "provider_status": {"healthy": False, "mode": "unavailable"},
    }
    assert panel_state_for_snapshot(snap) != "GREEN"


def test_inference_span_lifecycle(watchtower_env):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.store import WatchtowerStore

    c = OpenVINOWatchtowerCollector(store=WatchtowerStore(root=watchtower_env))
    span = c.begin_inference(organ_id="WILL", task="probe", model_id="test")
    c.on_chunk(span.span_id, delta="hello")
    c.complete_inference(span.span_id, output_text="hello")
    state = c.build_state()
    assert state["request_count"] == 1
    assert state["recent_inference_spans"][0].status == "completed"


def test_inference_failure_recorded(watchtower_env):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.store import WatchtowerStore

    c = OpenVINOWatchtowerCollector(store=WatchtowerStore(root=watchtower_env))
    span = c.begin_inference(task="fail")
    c.fail_inference(span.span_id, error="boom")
    assert c.build_state()["error_count"] == 1


def test_organ_activity_event(watchtower_env):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.store import WatchtowerStore

    c = OpenVINOWatchtowerCollector(store=WatchtowerStore(root=watchtower_env))
    c.set_organ_activity("EXCITON", state="active", task="render")
    assert c.build_state()["organ_activity"]["EXCITON"].state == "active"


def test_queue_depth_event(watchtower_env):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.store import WatchtowerStore

    c = OpenVINOWatchtowerCollector(store=WatchtowerStore(root=watchtower_env))
    c.set_queue_depth("operator_queue", 3)
    assert c.build_state()["queue_depths"]["operator_queue"] == 3


def test_redaction_removes_secrets():
    from hg_runtime.openvino_watchtower.redaction import redact_payload

    clean, applied = redact_payload({"api_key": "sk-secret", "prompt": "hello world"})
    assert "api_key" not in clean
    assert applied
    assert "prompt_hash" in clean or "prompt_length" in clean


def test_raw_prompt_disabled_by_default():
    from hg_runtime.openvino_watchtower.schema import TelemetryRedactionPolicy

    assert TelemetryRedactionPolicy().raw_prompts_enabled is False


def test_hidden_chain_of_thought_absent():
    from hg_runtime.openvino_watchtower.redaction import redact_payload

    clean, _ = redact_payload({"chain_of_thought": "secret reasoning"})
    assert "chain_of_thought" not in clean


def test_local_server_binds_loopback_only(watchtower_env, monkeypatch):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.server import OpenVINOWatchtowerServer

    collector = OpenVINOWatchtowerCollector()
    monkeypatch.setattr(collector, "refresh_probes", lambda **_: None)

    server = OpenVINOWatchtowerServer(host="127.0.0.1", port=8792, collector=collector)
    server.start(background=True)
    time.sleep(0.5)
    try:
        with urlopen("http://127.0.0.1:8792/status", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data["authority_created"] is False
    finally:
        server.stop()


def test_status_endpoint_returns_snapshot(watchtower_env, monkeypatch):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.server import OpenVINOWatchtowerServer

    collector = OpenVINOWatchtowerCollector()
    monkeypatch.setattr(collector, "refresh_probes", lambda **_: None)

    server = OpenVINOWatchtowerServer(host="127.0.0.1", port=8793, collector=collector)
    server.start(background=True)
    time.sleep(0.5)
    try:
        with urlopen("http://127.0.0.1:8793/status", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert "freshness_verdict" in data
    finally:
        server.stop()


def test_metrics_endpoint(watchtower_env, monkeypatch):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.server import OpenVINOWatchtowerServer

    collector = OpenVINOWatchtowerCollector()
    monkeypatch.setattr(collector, "refresh_probes", lambda **_: None)

    server = OpenVINOWatchtowerServer(host="127.0.0.1", port=8794, collector=collector)
    server.start(background=True)
    time.sleep(0.5)
    try:
        with urlopen("http://127.0.0.1:8794/metrics", timeout=5) as resp:
            body = resp.read().decode("utf-8")
        assert "hg_openvino_inference_requests_total" in body
    finally:
        server.stop()


def test_exciton_panel_consumes_snapshot():
    from hg_runtime.exciton.schema import ExcitonPanelState
    from hg_runtime.openvino_watchtower.exciton_panel import exciton_panel_fields, exciton_panel_state

    snap = {
        "freshness_verdict": "stale",
        "provider_status": {"verdict": "YELLOW", "mode": "unavailable", "healthy": False},
        "model_status": {},
        "device_status": {},
        "active_inference_spans": [],
        "organ_activity": {},
        "redaction": {},
    }
    fields = exciton_panel_fields(snap)
    assert fields["authority_created"] is False
    assert exciton_panel_state(snap) == ExcitonPanelState.YELLOW


def test_exciton_panel_no_authority():
    from hg_runtime.exciton.schema import ExcitonPanelState
    from hg_runtime.openvino_watchtower.exciton_panel import exciton_panel_fields, exciton_panel_state

    snap = {
        "freshness_verdict": "contact_lost",
        "provider_status": {"verdict": "YELLOW", "mode": "unavailable"},
        "model_status": {},
        "device_status": {},
        "active_inference_spans": [],
        "organ_activity": {},
        "redaction": {},
    }
    fields = exciton_panel_fields(snap)
    assert fields["permission_granted"] is False
    assert exciton_panel_state(snap) == ExcitonPanelState.RED


def test_ui_has_required_sections():
    html = (WORKSPACE / "apps/openvino_watchtower/index.html").read_text(encoding="utf-8")
    js = (WORKSPACE / "apps/openvino_watchtower/app.js").read_text(encoding="utf-8")
    for needle in ("view-live", "organ-grid", "freshness", "provider-fields", "view-replay", "view-trace"):
        assert needle in html
    assert "renderOrganMap" in js
    assert "cdn" not in html.lower()
    assert "analytics" not in html.lower()


def test_no_authority_flags_in_snapshot(watchtower_env):
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector
    from hg_runtime.openvino_watchtower.store import WatchtowerStore

    snap = OpenVINOWatchtowerCollector(store=WatchtowerStore(root=watchtower_env)).snapshot()
    assert snap["authority_created"] is False
    assert snap["permission_granted"] is False
