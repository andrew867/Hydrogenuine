"""
LLM abstraction: request/response types and ProviderRegistry.

All completions go through the registry; adapters implement complete() and stream_complete().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol

from hg_gateway.llm_defaults import get_default_model, is_safe_local_only

# Message shape compatible with OpenAI / LiteLLM
MessageDict = Dict[str, Any]  # {"role": str, "content": str, ...}


@dataclass
class CompletionRequest:
    """Input for a single completion call."""

    messages: List[MessageDict]
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    provider: Optional[str] = None  # e.g. openai, anthropic, vllm
    base_url: Optional[str] = None  # for vLLM or custom OpenAI-compatible endpoints
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None  # env var name if api_key not set
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResponse:
    """Result of a non-streaming completion."""

    content: str
    usage: Optional[Dict[str, int]] = None  # prompt_tokens, completion_tokens, total_tokens
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw: Optional[Any] = None


class LLMAdapter(Protocol):
    """Protocol for provider adapters: complete and optional stream_complete."""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        ...

    def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Yield content chunks (async)."""
        ...


class ProviderRegistry:
    """
    Maps provider id (+ optional model) to adapter. Resolves LiteLLM model string
    and delegates to LiteLLM or custom adapters.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, Any] = {}  # provider_id -> adapter
        self._litellm_providers: set = {"openai", "anthropic", "google", "xai", "vllm"}

    def register(self, provider_id: str, adapter: Any) -> None:
        self._adapters[provider_id] = adapter

    def get_adapter(self, provider_id: str) -> Any:
        adapter = self._adapters.get(provider_id)
        if adapter is None:
            raise KeyError(f"Unknown provider: {provider_id}. Registered: {list(self._adapters)}")
        return adapter

    def list_providers(self) -> List[str]:
        return list(self._adapters)

    def complete(
        self,
        messages: List[MessageDict],
        model: str,
        *,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        """Single completion. Resolves provider from model prefix (e.g. openai/gpt-4o) or provider arg."""
        provider_id, model_name = self._resolve_provider_and_model(model, provider)
        req = CompletionRequest(
            messages=messages,
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            provider=provider_id,
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            extra=kwargs,
        )
        adapter = self.get_adapter(provider_id)
        return adapter.complete(req)

    async def stream_complete(
        self,
        messages: List[MessageDict],
        model: str,
        *,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_env: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream completion; yields content chunks."""
        provider_id, model_name = self._resolve_provider_and_model(model, provider)
        req = CompletionRequest(
            messages=messages,
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            provider=provider_id,
            base_url=base_url,
            api_key=api_key,
            api_key_env=api_key_env,
            extra=kwargs,
        )
        adapter = self.get_adapter(provider_id)
        async for chunk in adapter.stream_complete(req):
            yield chunk

    def _resolve_provider_and_model(self, model: str, provider: Optional[str]) -> tuple[str, str]:
        """Return (provider_id, model_name). model may be 'openai/gpt-4o-mini' or just 'gpt-4o-mini'."""
        if is_safe_local_only():
            return "stub", get_default_model("stub")
        if "/" in model and provider is None:
            part = model.split("/", 1)
            return part[0].lower(), part[1]
        if provider:
            return provider.lower(), model
        return "openai", model


# Default global registry; populated by register_default_adapters()
_default_registry: Optional[ProviderRegistry] = None
_default_registry_safe_local: Optional[bool] = None


def get_default_registry() -> ProviderRegistry:
    global _default_registry, _default_registry_safe_local
    safe_local = is_safe_local_only()
    if _default_registry is None or _default_registry_safe_local != safe_local:
        _default_registry = ProviderRegistry()
        from hg_llm.adapters import register_default_adapters
        register_default_adapters(_default_registry)
        _default_registry_safe_local = safe_local
    return _default_registry


def set_default_registry(registry: ProviderRegistry) -> None:
    global _default_registry, _default_registry_safe_local
    _default_registry = registry
    _default_registry_safe_local = is_safe_local_only() if registry is not None else None
