"""Optional live cloud provider probes — tiny token budget, advisory only."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from hg_runtime.model_provider_fabric.adapters.cloud import AnthropicProviderAdapter, OpenAIProviderAdapter, XAIProviderAdapter
from hg_runtime.model_provider_fabric.config_loader import load_registry

WORKSPACE = Path(__file__).resolve().parents[2]
CLOUD = WORKSPACE / "configs/model_providers/cloud_providers.example.json"


def _assert_no_secrets(payload: object) -> None:
    text = str(payload)
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"):
        val = os.environ.get(key, "")
        if val and len(val) > 8 and val in text:
            raise AssertionError(f"secret value leaked for {key}")
    for prefix in ("sk-", "sk-ant-"):
        assert prefix not in text


@pytest.mark.cloud_live
def test_live_openai_tiny_probe():
    reg = load_registry(extra_paths=[CLOUD])
    cfg = reg.get("openai-agent0-heavy")
    assert cfg is not None
    cfg = replace(cfg, enabled=True)
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY not set in container env")
    adapter = OpenAIProviderAdapter()
    v = adapter.validate_config(cfg)
    assert v["secret_value_included"] is False
    result = adapter.inference(cfg, prompt="Reply with exactly: pong", request_id="live-test-openai", max_tokens=8)
    _assert_no_secrets(result)
    assert result["schema"] in {"cloud-inference-result", "cloud-inference-denied"}
    if result["schema"] == "cloud-inference-result":
        assert result.get("executed") is True


@pytest.mark.cloud_live
def test_live_anthropic_tiny_probe():
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        pytest.skip("ANTHROPIC_API_KEY not set")
    reg = load_registry(extra_paths=[CLOUD])
    cfg = reg.get("anthropic-agent0-heavy")
    assert cfg is not None
    cfg = replace(cfg, enabled=True)
    result = AnthropicProviderAdapter().inference(cfg, prompt="Reply with exactly: pong", request_id="live-test-anthropic", max_tokens=8)
    _assert_no_secrets(result)
    assert result["schema"] in {"cloud-inference-result", "cloud-inference-denied"}


@pytest.mark.cloud_live
def test_live_xai_tiny_probe():
    if not os.environ.get("XAI_API_KEY", "").strip():
        pytest.skip("XAI_API_KEY not set")
    reg = load_registry(extra_paths=[CLOUD])
    cfg = reg.get("xai-agent0-heavy")
    assert cfg is not None
    cfg = replace(cfg, enabled=True)
    result = XAIProviderAdapter().inference(cfg, prompt="Reply with exactly: pong", request_id="live-test-xai", max_tokens=8)
    _assert_no_secrets(result)
    assert result["schema"] in {"cloud-inference-result", "cloud-inference-denied"}
    if result["schema"] == "cloud-inference-result" and result.get("executed"):
        assert result.get("result", {}).get("ok") is True
