"""Phase 3 tests — provider hooks, autostart, incident UI, CT registry."""

from __future__ import annotations

import json
import os
import socket
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _watchtower_env(monkeypatch):
    monkeypatch.setenv("HG_OPENVINO_WATCHTOWER_ENABLED", "true")


def test_provider_hooks_config_defaults():
    from hg_runtime.openvino_watchtower.provider_hooks_config import load_provider_hooks_config

    cfg = load_provider_hooks_config()
    assert cfg.enabled is True
    assert cfg.strict_mode is False
    assert cfg.capture_raw_prompt is False
    assert cfg.capture_raw_output is False
    assert cfg.redaction_required is True


def test_runtime_config_default_no_autostart(monkeypatch):
    monkeypatch.delenv("HG_OPENVINO_WATCHTOWER_AUTOSTART", raising=False)
    monkeypatch.delenv("HG_OPENVINO_WATCHTOWER_ENABLED", raising=False)
    from hg_runtime.openvino_watchtower.runtime_config import load_runtime_config

    cfg = load_runtime_config()
    assert cfg.autostart is False


def test_external_host_rejected():
    from hg_runtime.openvino_watchtower.runtime_config import validate_host

    ok, err = validate_host("0.0.0.0")
    assert ok is False
    assert "denied" in (err or "")


def test_provider_emits_inference_events():
    from hg_runtime.model_provider_fabric.streaming import emit_non_streaming_as_events
    from hg_runtime.openvino_watchtower.collector import OpenVINOWatchtowerCollector

    c = OpenVINOWatchtowerCollector()
    with patch("hg_runtime.openvino_watchtower.collector.get_collector", return_value=c):
        emit_non_streaming_as_events(
            provider_id="cpu-stub",
            model_id="test-model",
            role="primary",
            organ_id="organ-a",
            request_id="req-1",
            full_text="hello world",
        )
    snap = c.snapshot(persist=False)
    assert snap.get("request_count", 0) >= 1


def test_hook_exception_does_not_break_provider(monkeypatch):
    from hg_runtime.model_provider_fabric.streaming import emit_non_streaming_as_events
    from hg_runtime.openvino_watchtower.provider_hooks_config import ProviderHooksConfig

    monkeypatch.setattr(
        "hg_runtime.model_provider_fabric.watchtower_adapter._cfg",
        lambda: ProviderHooksConfig(enabled=True, strict_mode=False),
    )

    def boom(*a, **k):
        raise RuntimeError("telemetry fail")

    monkeypatch.setattr(
        "hg_runtime.openvino_watchtower.instrumentation.inference_span",
        boom,
    )
    events = emit_non_streaming_as_events(
        provider_id="cpu-stub",
        model_id="m",
        role="primary",
        organ_id=None,
        request_id="req-2",
        full_text="ok",
    )
    assert len(events) == 3


def test_strict_mode_raises(monkeypatch):
    from hg_runtime.model_provider_fabric.watchtower_adapter import WatchtowerInferenceContext
    from hg_runtime.openvino_watchtower.provider_hooks_config import ProviderHooksConfig

    monkeypatch.setattr(
        "hg_runtime.model_provider_fabric.watchtower_adapter._cfg",
        lambda: ProviderHooksConfig(enabled=True, strict_mode=True),
    )

    def boom(*a, **k):
        raise RuntimeError("strict")

    monkeypatch.setattr(
        "hg_runtime.openvino_watchtower.instrumentation.inference_span",
        boom,
    )
    with pytest.raises(RuntimeError):
        with WatchtowerInferenceContext(
            provider_id="p",
            model_id="m",
            request_id="r",
        ):
            pass


def test_no_raw_prompt_by_default():
    from hg_runtime.model_provider_fabric.watchtower_adapter import safe_prompt_meta

    meta = safe_prompt_meta("secret prompt text")
    assert "raw_prompt" not in meta
    assert "prompt_text" not in meta


def test_autostart_duplicate_reuses(monkeypatch):
    from hg_runtime.openvino_watchtower import lifecycle

    lifecycle._sidecar_started = False
    lifecycle._sidecar_server = None

    class FakeServer:
        def start(self, *, background=True):
            return None

        def stop(self):
            return None

    monkeypatch.setattr(
        "hg_runtime.openvino_watchtower.server.OpenVINOWatchtowerServer",
        FakeServer,
    )
    monkeypatch.setattr(lifecycle, "_port_open", lambda h, p: False)
    r1 = lifecycle.start_sidecar()
    r2 = lifecycle.start_sidecar()
    assert r1.ok
    assert r2.reused or r2.ok


def test_incident_export_endpoint(monkeypatch, tmp_path):
    from hg_runtime.openvino_watchtower.server import OpenVINOWatchtowerServer
    from hg_runtime.openvino_watchtower.session import WatchtowerSession

    sess = WatchtowerSession.open(session_id="sess-ui-test")
    sess.append_event({"event_type": "TEST", "payload": {}})
    sess.stop()

    def fake_export(**kwargs):
        out = tmp_path / kwargs["incident_id"]
        out.mkdir()
        (out / "manifest.json").write_text(json.dumps({"snapshot_hash": "abc"}), encoding="utf-8")
        (out / "privacy_report.json").write_text("{}", encoding="utf-8")
        return out

    monkeypatch.setattr("hg_runtime.openvino_watchtower.incident_export.export_incident", fake_export)

    port = 18791
    server = OpenVINOWatchtowerServer(host="127.0.0.1", port=port)
    server.start(background=True)
    try:

        def _post():
            import urllib.request

            body = json.dumps({"session_id": "sess-ui-test", "incident_id": "inc-1", "reason": "test"}).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/incident/export",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())

        data = _post()
        assert data["ok"] is True
        assert data["redaction_applied"] is True
        assert data["authority_created"] is False
    finally:
        server.stop()


def test_ui_export_button_exists():
    html = (WORKSPACE / "apps/openvino_watchtower/index.html").read_text(encoding="utf-8")
    js = (WORKSPACE / "apps/openvino_watchtower/app.js").read_text(encoding="utf-8")
    assert 'id="export-incident-btn"' in html
    assert "export-incident-btn" in js
    assert "/incident/export" in js


def test_ct_registry_lists_watchtower_gates():
    text = (WORKSPACE / "config/truth_gate_registry.yaml").read_text(encoding="utf-8")
    for gate in (
        "openvino_watchtower_final",
        "openvino_watchtower_phase_2_final",
        "openvino_watchtower_provider_hook",
        "openvino_watchtower_autostart",
        "openvino_watchtower_phase_3_final",
    ):
        assert gate in text
