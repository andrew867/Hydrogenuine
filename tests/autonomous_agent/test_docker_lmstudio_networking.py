"""Tests for LM Studio Docker networking module."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _fixture_env(monkeypatch):
    monkeypatch.setenv("HG_MODE", "fixture")
    monkeypatch.setenv("HG_RUNTIME_PROFILE", "fixture")
    monkeypatch.setenv("HG_PROOF_DIR", "/data/proofs")
    monkeypatch.setenv("HG_REPORT_DIR", "/data/reports")
    monkeypatch.setenv("HG_STATE_DIR", "/data/state")
    monkeypatch.setenv("HG_DB_URL", "sqlite:////data/state/hydrogenuine.sqlite3")
    monkeypatch.setenv("HG_DISABLE_REMOTE_PROVIDERS", "true")
    monkeypatch.setenv("HG_DISABLE_LIVE_EFFECTS", "true")
    monkeypatch.setenv("HG_REQUIRE_OPERATOR_REVIEW", "true")
    monkeypatch.setenv("HG_LMSTUDIO_BASE_URL", "http://host.docker.internal:1234/v1")
    monkeypatch.setenv("HG_LMSTUDIO_SELECTED_MODEL", "google/gemma-4-e4b")
    monkeypatch.setenv("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b,gemma-3-4b-it,qwen2.5-7b-instruct")
    monkeypatch.setenv("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,cybersecurity,offensive,uncensored,30b,qwen3-coder-30b")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", "/models/openvino")
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_check_host_docker_internal():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_lmstudio_endpoint
    cfg = load_runtime_config()
    check = check_lmstudio_endpoint(cfg)
    assert check.is_host_docker_internal is True
    assert check.is_container_localhost is False
    assert check.warning == ""


def test_check_container_localhost_warns(monkeypatch):
    monkeypatch.setenv("HG_LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_lmstudio_endpoint, CONTAINER_LOCALHOST_WARNING
    cfg = load_runtime_config()
    check = check_lmstudio_endpoint(cfg)
    assert check.is_container_localhost is True
    assert check.warning == CONTAINER_LOCALHOST_WARNING


def test_check_tailscale_ip(monkeypatch):
    monkeypatch.setenv("HG_LMSTUDIO_BASE_URL", "http://100.64.1.5:1234/v1")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_lmstudio_endpoint
    cfg = load_runtime_config()
    check = check_lmstudio_endpoint(cfg)
    assert check.is_tailscale_ip is True


def test_check_lan_ip(monkeypatch):
    monkeypatch.setenv("HG_LMSTUDIO_BASE_URL", "http://192.168.1.100:1234/v1")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_lmstudio_endpoint
    cfg = load_runtime_config()
    check = check_lmstudio_endpoint(cfg)
    assert check.is_lan_ip is True


def test_model_allowed():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_model_allowed
    cfg = load_runtime_config()
    allowed, forbidden, reason = check_model_allowed("google/gemma-4-e4b", cfg)
    assert allowed is True
    assert forbidden is False


def test_model_forbidden_deepseek():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_model_allowed
    cfg = load_runtime_config()
    allowed, forbidden, reason = check_model_allowed("deepseek-coder-v2", cfg)
    assert allowed is False
    assert forbidden is True
    assert "deepseek" in reason.lower()


def test_model_forbidden_offensive():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_model_allowed
    cfg = load_runtime_config()
    allowed, forbidden, reason = check_model_allowed("offensive-security-llm", cfg)
    assert forbidden is True


def test_model_forbidden_uncensored():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_model_allowed
    cfg = load_runtime_config()
    allowed, forbidden, reason = check_model_allowed("llama-uncensored-7b", cfg)
    assert forbidden is True


def test_model_not_in_allowlist():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.lmstudio_networking import check_model_allowed
    cfg = load_runtime_config()
    allowed, forbidden, reason = check_model_allowed("unknown-model-3b", cfg)
    assert allowed is False
    assert forbidden is False


def test_probe_health_unreachable():
    from hg_runtime.deployment.lmstudio_networking import probe_lmstudio_health
    reachable, models = probe_lmstudio_health("http://192.0.2.1:9999/v1")
    assert reachable is False
    assert models == []
