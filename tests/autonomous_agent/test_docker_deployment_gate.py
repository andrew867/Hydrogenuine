"""Tests for Docker deployment gate."""

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
    monkeypatch.setenv("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b,gemma-3-4b-it")
    monkeypatch.setenv("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,cybersecurity,offensive,uncensored,30b,qwen3-coder-30b")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", "/models/openvino")
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_gate_green_fixture_defaults():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["verdict"] == "GREEN"
    assert result["checks_passed"] == result["checks_total"]


def test_gate_preserves_phase19_yellow():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["phase24_remains_infrastructure_only"] is True


def test_gate_asserts_zero_boundaries():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True
    assert result["zero_cannot_self_authorize"] is True
    assert result["not_deployed_to_live_users"] is True


def test_gate_yellow_if_remote_providers_enabled(monkeypatch):
    monkeypatch.setenv("HG_DISABLE_REMOTE_PROVIDERS", "false")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["verdict"] == "YELLOW"
    failed = [c for c in result["checks"] if not c["passed"]]
    assert any("remote_providers_disabled" in c["name"] for c in failed)


def test_gate_yellow_if_live_effects_enabled(monkeypatch):
    monkeypatch.setenv("HG_DISABLE_LIVE_EFFECTS", "false")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["verdict"] == "YELLOW"


def test_gate_yellow_if_forbidden_model_selected(monkeypatch):
    monkeypatch.setenv("HG_LMSTUDIO_SELECTED_MODEL", "deepseek-coder-v2")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    result = run_gate(cfg)
    assert result["verdict"] == "YELLOW"


def test_gate_with_db_tables():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    tables = ["deployment_runs", "deployment_receipts", "proof_bundles", "operator_reviews", "deployment_health"]
    result = run_gate(cfg, db_tables=tables)
    assert result["verdict"] == "GREEN"
    assert result["checks_passed"] == result["checks_total"]


def test_gate_with_lmstudio_check_clean():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    lm_check = {"is_container_localhost": False, "model_forbidden": False}
    result = run_gate(cfg, lmstudio_check=lm_check)
    assert result["verdict"] == "GREEN"


def test_gate_yellow_if_lmstudio_container_localhost():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.gate import run_gate
    cfg = load_runtime_config()
    lm_check = {"is_container_localhost": True, "model_forbidden": False}
    result = run_gate(cfg, lmstudio_check=lm_check)
    assert result["verdict"] == "YELLOW"
