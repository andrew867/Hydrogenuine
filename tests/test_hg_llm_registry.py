"""Tests for hg_llm ProviderRegistry and adapters."""

import pytest

try:
    from hg_llm import ProviderRegistry, get_default_registry, CompletionRequest, CompletionResponse
    from hg_llm.adapters import register_default_adapters
except Exception as e:
    pytest.skip(f"hg_llm/litellm import failed: {e}", allow_module_level=True)


def test_registry_register_and_list():
    reg = ProviderRegistry()
    register_default_adapters(reg)
    providers = reg.list_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert "vllm" in providers
    assert "openvino" in providers


def test_safe_local_registry_uses_stub_adapter(monkeypatch):
    monkeypatch.setenv("SAFE_LOCAL_ONLY", "1")
    reg = ProviderRegistry()
    register_default_adapters(reg)
    providers = reg.list_providers()
    assert "stub" in providers
    adapter = reg.get_adapter("openai")
    resp = adapter.complete(CompletionRequest(messages=[{"role": "user", "content": "launch a workflow"}], model="gpt-4.1-mini"))
    assert isinstance(resp, CompletionResponse)
    assert "stub workflow result" in resp.content.lower()


def test_registry_unknown_provider_raises():
    reg = ProviderRegistry()
    register_default_adapters(reg)
    with pytest.raises(KeyError, match="Unknown provider"):
        reg.get_adapter("nonexistent")


def test_openvino_adapter_raises_without_deps_or_path():
    """OpenVINO adapter raises RuntimeError (not NotImplementedError) when deps or path missing."""
    from hg_llm.adapters import OpenVINOAdapter
    adapter = OpenVINOAdapter()
    req = CompletionRequest(messages=[{"role": "user", "content": "hi"}], model="test")
    with pytest.raises(RuntimeError) as exc_info:
        adapter.complete(req)
    msg = str(exc_info.value).lower()
    assert "openvino" in msg or "hg_openvino" in msg


def test_openvino_adapter_interface_conformance():
    """OpenVINOAdapter has complete() -> CompletionResponse and stream_complete() -> AsyncIterator[str]."""
    from hg_llm.adapters import OpenVINOAdapter
    adapter = OpenVINOAdapter()
    assert hasattr(adapter, "complete")
    assert hasattr(adapter, "stream_complete")
    assert callable(adapter.complete)
    assert callable(adapter.stream_complete)


def test_openvino_adapter_raises_invalid_model_path():
    """When HG_OPENVINO_MODEL_PATH is set but not a directory, adapter raises RuntimeError."""
    from hg_llm.adapters import openvino_adapter
    adapter = openvino_adapter.OpenVINOAdapter()
    req = CompletionRequest(messages=[{"role": "user", "content": "hi"}], model="test")
    # If openvino_genai is not installed we get "openvino-genai" error; if installed but path bad, "model directory"
    with pytest.raises(RuntimeError):
        adapter.complete(req)


def test_get_default_registry_singleton():
    r1 = get_default_registry()
    r2 = get_default_registry()
    assert r1 is r2
    assert "openai" in r1.list_providers()


def test_litellm_adapter_redact_messages():
    """Pack 14: redaction of sensitive prompt data for logs."""
    from hg_llm.adapters.litellm_adapter import _redact_messages
    out = _redact_messages([{"role": "user", "content": "secret password 123"}])
    assert len(out) == 1
    assert out[0]["content"] == "[redacted]"
    out2 = _redact_messages([{"role": "system", "content": ""}])
    assert out2[0]["content"] == ""


def test_litellm_adapter_retryable_error():
    """Pack 14: 429 and 5xx are retryable."""
    from hg_llm.adapters.litellm_adapter import _is_retryable_error
    class E429(Exception):
        status_code = 429
    class E502(Exception):
        status_code = 502
    class E400(Exception):
        status_code = 400
    assert _is_retryable_error(E429()) is True
    assert _is_retryable_error(E502()) is True
    assert _is_retryable_error(E400()) is False


def test_litellm_adapter_breaker_key():
    from hg_llm.adapters.litellm_adapter import _breaker_key
    assert _breaker_key("openai/gpt-4") == "llm:openai/gpt-4"
    assert _breaker_key("") == "llm:default"


def test_litellm_adapter_timeout_config():
    """Pack 14: timeout from env or HG_LLM_TIMEOUT_S."""
    from hg_llm.adapters.litellm_adapter import _get_timeout_s
    import os
    prev = os.environ.get("LITELLM_TIMEOUT_SECONDS")
    try:
        os.environ.pop("LITELLM_TIMEOUT_SECONDS", None)
        t = _get_timeout_s()
        assert t >= 10
        os.environ["LITELLM_TIMEOUT_SECONDS"] = "45"
        assert _get_timeout_s() == 45
    finally:
        if prev is not None:
            os.environ["LITELLM_TIMEOUT_SECONDS"] = prev
        else:
            os.environ.pop("LITELLM_TIMEOUT_SECONDS", None)


@pytest.mark.llm_live
def test_litellm_completion_via_multi_llm_live():
    """When HG_LLM_LIVE=1 and OPENAI_API_KEY (or LITELLM_*) set, use live API through multi-LLM registry."""
    reg = get_default_registry()
    adapter = reg.get_adapter("openai")
    req = CompletionRequest(messages=[{"role": "user", "content": "Reply with exactly: OK"}], model="gpt-4o-mini")
    resp = adapter.complete(req)
    assert isinstance(resp, CompletionResponse)
    assert resp.content is not None
    assert "ok" in resp.content.lower() or len(resp.content.strip()) > 0
    if getattr(resp, "usage", None):
        assert "latency_ms" in resp.usage or "prompt_tokens" in resp.usage
