"""Proposal-only model provider interface for RTC cognition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Protocol


class CognitionCancelled(Exception):
    """Stream halted by PANIC or explicit cancel."""


class CognitionTimeout(Exception):
    """Model stream exceeded the cognition budget."""


@dataclass(frozen=True)
class CognitionPrompt:
    messages: tuple[Mapping[str, str], ...]
    trigger_event_id: str
    trigger_type: str
    request_digest: str


class ModelProvider(Protocol):
    """Proposal-only streaming provider. No tools, authority, or side effects."""

    provider_id: str
    model_name: str

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        """Yield proposal text fragments until complete, cancelled, or timed out."""
        ...


def build_provider(config) -> ModelProvider:
    from hg_runtime.cognition.config import validate_live_config
    from hg_runtime.cognition.fake_provider import FakeModelProvider

    if config.provider == "fake":
        return FakeModelProvider(model_name=config.model)
    if config.live_enabled and not config.offline:
        validate_live_config(config)
        if config.provider in {"openai", "vllm"}:
            from hg_runtime.cognition.openai_provider import OpenAICompatibleProvider

            return OpenAICompatibleProvider(
                provider_id=config.provider,
                model_name=config.model,
                base_url=config.base_url,
                api_key=config.api_key,
                temperature=config.temperature,
                seed=config.seed,
                max_tokens=config.max_tokens,
                timeout_s=config.timeout_s,
            )
        raise ValueError(f"unsupported live cognition provider {config.provider!r}")
    if config.provider in {"openai", "vllm"}:
        return FakeModelProvider(model_name=f"offline:{config.model}")
    raise ValueError(f"unsupported cognition provider {config.provider!r}")


__all__ = [
    "CognitionCancelled",
    "CognitionPrompt",
    "CognitionTimeout",
    "ModelProvider",
    "build_provider",
]
