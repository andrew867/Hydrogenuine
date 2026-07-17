from __future__ import annotations

from pathlib import Path

import pytest

from hg_dep.appliance_config import ApplianceConfig
from hg_dep.appliance_runtime import ApplianceRuntime
from hg_dep.vllm_health import check_vllm_health
from hg_runtime.cognition.fake_provider import FakeModelProvider
from hg_runtime.replay import replay


def _config(tmp_path: Path, *, daemon: bool = False) -> ApplianceConfig:
    return ApplianceConfig(
        runtime_dir=tmp_path / "runtime",
        log_dir=tmp_path / "logs",
        cognition_mode="stub",
        max_ticks=None if daemon else 2,
        daemon_mode=daemon,
        require_enabled=False,
        governance_trace=False,
    )


def test_bounded_appliance_start_stop_and_replay(tmp_path: Path):
    config = _config(tmp_path)
    runtime = ApplianceRuntime(config)
    summary = runtime.start_bounded(max_ticks=2, submit_chat=True)
    assert summary["ok"] is True
    assert summary["ticks"] >= 1
    assert summary["state_hash"].startswith("sha256:")

    events = list(runtime.controller.bus.read_all())
    types = [event["type"] for event in events]
    assert "RUNTIME_TICK_COMPLETED" in types
    assert "RUNTIME_STOPPED" in types

    replay_summary = runtime.replay_latest()
    assert replay_summary["ok"] is True
    assert replay_summary["state_hash"] == summary["state_hash"]


def test_stub_cognition_mode_uses_fake_provider_offline(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_STREAMING", "1")
    config = _config(tmp_path)
    runtime = ApplianceRuntime(config)
    runtime.start_bounded(max_ticks=1, submit_chat=True)
    provider = runtime.controller.loop.cognition.provider
    assert isinstance(provider, FakeModelProvider)


def test_stop_request_writes_stop_file(tmp_path: Path):
    config = _config(tmp_path)
    runtime = ApplianceRuntime(config)
    result = runtime.stop(reason="test_stop")
    assert result["stop_requested"] is True
    assert config.stop_request_path.exists()


def test_stop_request_integrates_with_controller(tmp_path: Path):
    config = ApplianceConfig(
        runtime_dir=tmp_path / "runtime",
        log_dir=tmp_path / "logs",
        cognition_mode="stub",
        daemon_mode=True,
        require_enabled=False,
    )
    runtime = ApplianceRuntime(config)
    runtime.controller.loop.start()
    runtime.submit_chat("daemon tick")
    runtime.controller.run_once(poll_timeout=0.0)
    runtime.request_stop("test_daemon_stop")
    assert config.stop_request_path.exists()
    runtime.controller.request_stop(reason="test_daemon_stop")
    runtime.controller.loop.stop(reason="test_daemon_stop")
    assert replay(tmp_path / "runtime").ok is True


def test_vllm_health_skipped_without_url():
    result = check_vllm_health(None)
    assert result["skipped"] is True
    assert result["ok"] is False


@pytest.mark.skipif(
    not __import__("os").environ.get("HG_APPLIANCE_VLLM_HEALTH_CHECK"),
    reason="live vLLM health check not configured",
)
def test_vllm_health_live_when_configured():
    import os

    result = check_vllm_health(os.environ.get("HG_APPLIANCE_VLLM_BASE_URL"))
    assert "ok" in result
