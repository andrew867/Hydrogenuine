"""Tests for Docker deployment runtime config, profiles, and health."""

from __future__ import annotations

import os
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
    monkeypatch.setenv("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b,gemma-3-4b-it")
    monkeypatch.setenv("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,cybersecurity,offensive,uncensored,30b")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", "/models/openvino")
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_load_runtime_config_fixture_defaults():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    cfg = load_runtime_config()
    assert cfg.mode == "fixture"
    assert cfg.profile == "fixture"
    assert cfg.disable_remote_providers is True
    assert cfg.disable_live_effects is True
    assert cfg.require_operator_review is True
    assert cfg.allow_model_downloads is False
    assert cfg.provider_openvino_configured is False
    assert cfg.cognitive_soak_active is True


def test_load_runtime_config_lmstudio_fields():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    cfg = load_runtime_config()
    assert cfg.lmstudio_base_url == "http://host.docker.internal:1234/v1"
    assert cfg.lmstudio_selected_model == "google/gemma-4-e4b"
    assert "google/gemma-4-e4b" in cfg.lmstudio_allowed_models
    assert "deepseek" in cfg.lmstudio_forbidden_patterns


def test_redacted_config_hides_db_url():
    from hg_runtime.deployment.runtime_config import load_runtime_config, redacted_config
    cfg = load_runtime_config()
    redacted = redacted_config(cfg)
    assert redacted["db_url"] == "***REDACTED***"
    assert redacted["mode"] == "fixture"


def test_required_env_keys_not_empty():
    from hg_runtime.deployment.runtime_config import required_env_keys
    keys = required_env_keys()
    assert len(keys) > 10
    assert "HG_MODE" in keys
    assert "HG_DISABLE_REMOTE_PROVIDERS" in keys


def test_bool_env_parsing(monkeypatch):
    from hg_runtime.deployment.runtime_config import _bool_env
    monkeypatch.setenv("TEST_BOOL", "true")
    assert _bool_env("TEST_BOOL", False) is True
    monkeypatch.setenv("TEST_BOOL", "0")
    assert _bool_env("TEST_BOOL", True) is False
    monkeypatch.setenv("TEST_BOOL", "yes")
    assert _bool_env("TEST_BOOL", False) is True
    monkeypatch.setenv("TEST_BOOL", "")
    assert _bool_env("TEST_BOOL", True) is True


def test_profile_fixture_exists():
    from hg_runtime.deployment.docker_profiles import PROFILES
    assert "fixture" in PROFILES
    assert PROFILES["fixture"]["safe_for_demo"] is True
    assert PROFILES["fixture"]["requires_lmstudio"] is False


def test_profile_lmstudio_requires_lmstudio():
    from hg_runtime.deployment.docker_profiles import PROFILES
    assert PROFILES["lmstudio"]["requires_lmstudio"] is True


def test_profile_openvino_requires_openvino():
    from hg_runtime.deployment.docker_profiles import PROFILES
    assert PROFILES["openvino"]["requires_openvino"] is True


def test_all_profiles_defined():
    from hg_runtime.deployment.docker_profiles import PROFILES
    for name in ("fixture", "lmstudio", "openvino", "db", "demo", "dev"):
        assert name in PROFILES


def test_health_check_fixture_safe():
    from hg_runtime.deployment.health import run_health_check
    result = run_health_check()
    assert result["healthy"] is True
    assert result["mode"] == "fixture"
    assert result["fixture_safe"] is True
    assert result["remote_providers_disabled"] is True
    assert result["live_effects_disabled"] is True
