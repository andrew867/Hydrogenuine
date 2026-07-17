"""Tests for OpenVINO model helper."""

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
    monkeypatch.setenv("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b")
    monkeypatch.setenv("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,cybersecurity,offensive,uncensored,30b")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", "/models/openvino")
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_is_model_forbidden_deepseek():
    from hg_runtime.deployment.openvino_models import is_model_forbidden
    assert is_model_forbidden("deepseek-coder-v2") is True


def test_is_model_forbidden_offensive():
    from hg_runtime.deployment.openvino_models import is_model_forbidden
    assert is_model_forbidden("offensive-sec-model") is True


def test_is_model_forbidden_uncensored():
    from hg_runtime.deployment.openvino_models import is_model_forbidden
    assert is_model_forbidden("llama-uncensored") is True


def test_is_model_forbidden_30b():
    from hg_runtime.deployment.openvino_models import is_model_forbidden
    assert is_model_forbidden("qwen3-coder-30b") is True


def test_safe_model_not_forbidden():
    from hg_runtime.deployment.openvino_models import is_model_forbidden
    assert is_model_forbidden("gemma-4-e4b") is False


def test_is_large_model():
    from hg_runtime.deployment.openvino_models import is_large_model
    assert is_large_model("llama-70b") is True
    assert is_large_model("gemma-4b") is False


def test_downloads_disabled_by_default():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.openvino_models import is_download_allowed
    cfg = load_runtime_config()
    assert is_download_allowed(cfg) is False


def test_request_download_rejected_forbidden():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.openvino_models import request_model_download
    cfg = load_runtime_config()
    prov = request_model_download("deepseek-v3", "huggingface", cfg)
    assert prov.rejected is True
    assert prov.download_performed is False


def test_request_download_rejected_large():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.openvino_models import request_model_download
    cfg = load_runtime_config()
    prov = request_model_download("llama-70b-instruct", "huggingface", cfg)
    assert prov.rejected is True
    assert "30B-class" in prov.rejection_reason


def test_request_download_rejected_disabled():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.openvino_models import request_model_download
    cfg = load_runtime_config()
    prov = request_model_download("gemma-4-e4b", "huggingface", cfg)
    assert prov.rejected is True
    assert "false" in prov.rejection_reason.lower()


def test_dry_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "true")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", str(tmp_path / "models"))
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.openvino_models import request_model_download
    cfg = load_runtime_config()
    prov = request_model_download("gemma-4-e4b", "huggingface", cfg, dry_run=True)
    assert prov.rejected is False
    assert prov.download_performed is False


def test_list_model_dir_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", str(tmp_path / "models"))
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.openvino_models import list_model_dir
    cfg = load_runtime_config()
    assert list_model_dir(cfg) == []
