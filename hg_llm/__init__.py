"""
hg_llm: Multi-provider LLM abstraction with LiteLLM backbone.

Use ProviderRegistry and complete() / stream_complete() for all chat completions.
Cloud and vLLM go through LiteLLM; custom adapters (e.g. OpenVINO) when needed.
"""

from hg_llm.abstraction import (
    CompletionRequest,
    CompletionResponse,
    ProviderRegistry,
    get_default_registry,
)
from hg_llm.adapters import register_default_adapters

__all__ = [
    "CompletionRequest",
    "CompletionResponse",
    "ProviderRegistry",
    "get_default_registry",
    "register_default_adapters",
]
