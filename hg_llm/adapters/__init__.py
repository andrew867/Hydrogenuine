"""
LLM adapters: LiteLLM (backbone) and custom (OpenVINO, etc.).
"""

from hg_gateway.llm_defaults import is_safe_local_only
from hg_llm.abstraction import ProviderRegistry
from hg_llm.adapters.litellm_adapter import LiteLLMAdapter
from hg_llm.adapters.openvino_adapter import OpenVINOAdapter
from hg_llm.adapters.stub_adapter import StubCompletionAdapter


def register_default_adapters(registry: ProviderRegistry) -> None:
    """Register LiteLLM for cloud + vLLM and OpenVINO custom adapter."""
    if is_safe_local_only():
        stub = StubCompletionAdapter()
        for provider in ("stub", "openai", "anthropic", "google", "xai", "vllm"):
            registry.register(provider, stub)
        registry.register("openvino", OpenVINOAdapter())
        return
    litellm = LiteLLMAdapter()
    for provider in ("openai", "anthropic", "google", "xai", "vllm"):
        registry.register(provider, litellm)
    registry.register("openvino", OpenVINOAdapter())
