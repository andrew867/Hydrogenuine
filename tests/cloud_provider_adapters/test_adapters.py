"""Cloud provider adapter tests."""

import os
from pathlib import Path

from hg_runtime.model_provider_fabric.adapters.cloud import OpenAIProviderAdapter, live_cloud_allowed
from hg_runtime.model_provider_fabric.config_loader import load_registry

WORKSPACE = Path(__file__).resolve().parents[2]
CLOUD = WORKSPACE / "configs/model_providers/cloud_providers.example.json"


def test_openai_validate_disabled():
    reg = load_registry(extra_paths=[CLOUD])
    cfg = reg.get("openai-agent0-heavy")
    adapter = OpenAIProviderAdapter()
    v = adapter.validate_config(cfg)
    assert v["ok"] is False or cfg.enabled is False
    assert v["secret_value_included"] is False


def test_missing_key_no_secret_in_output():
    os.environ.pop("OPENAI_API_KEY", None)
    reg = load_registry(extra_paths=[CLOUD])
    cfg = reg.get("openai-agent0-heavy")
    v = OpenAIProviderAdapter().validate_config(cfg)
    assert "sk-" not in str(v)


def test_live_cloud_off_by_default(monkeypatch):
    monkeypatch.delenv("HG_CLOUD_PROVIDERS_ENABLED", raising=False)
    monkeypatch.delenv("HG_ALLOW_LIVE_CLOUD_TEST", raising=False)
    assert live_cloud_allowed() is False
