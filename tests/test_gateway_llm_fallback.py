import os

from hg_gateway.llm_defaults import get_default_base_url, get_model_candidates
from hg_gateway.orchestration import get_fallback_chain


def test_get_model_candidates_prefers_env_and_deduplicates(monkeypatch):
    monkeypatch.setenv("HG_OPENAI_MODEL_CANDIDATES", "gpt-4o-mini, gpt-4.1-mini ,gpt-4o-mini")
    monkeypatch.setenv("HG_OPENAI_MODEL", "gpt-4.1-mini")
    models = get_model_candidates("openai")
    assert models[0] == "gpt-4o-mini"
    assert models[1] == "gpt-4.1-mini"
    assert models.count("gpt-4o-mini") == 1


def test_get_default_base_url_uses_provider_specific_env(monkeypatch):
    monkeypatch.setenv("HG_VLLM_BASE_URL", "http://local-llm:8000/v1/")
    assert get_default_base_url("vllm") == "http://local-llm:8000/v1"


def test_safe_local_mode_forces_stub_provider(monkeypatch):
    monkeypatch.setenv("SAFE_LOCAL_ONLY", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "should-not-matter")
    monkeypatch.setenv("HG_OPENAI_MODEL", "gpt-4.1-mini")
    assert get_model_candidates("openai") == ["local-deterministic"]
    assert get_default_base_url("openai") is None
    chain = get_fallback_chain("openai", "gpt-4.1-mini", "http://example.invalid", "OPENAI_API_KEY")
    assert chain == [("stub", "local-deterministic", "", None)]


def test_get_fallback_chain_prioritizes_requested_then_live_candidates(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "x-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("HG_XAI_MODEL_CANDIDATES", "grok-3-fast,grok-3-mini")
    chain = get_fallback_chain("openai", "gpt-4.1-mini", None, "OPENAI_API_KEY")
    assert chain[0][:3] == ("openai", "gpt-4.1-mini", "OPENAI_API_KEY")
    assert ("xai", "grok-3-fast", "XAI_API_KEY", None) in chain
    assert ("xai", "grok-3-mini", "XAI_API_KEY", None) in chain
    assert len(chain) == len(set(chain))
