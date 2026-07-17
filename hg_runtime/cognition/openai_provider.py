"""Optional OpenAI-compatible / vLLM streaming provider (config-gated)."""

from __future__ import annotations

import asyncio
import time
from typing import Iterator

from hg_runtime.cognition.provider import CognitionCancelled, CognitionPrompt, CognitionTimeout


class OpenAICompatibleProvider:
    """Thin bridge to hg_llm streaming. Only used when live cognition is enabled."""

    def __init__(
        self,
        *,
        provider_id: str,
        model_name: str,
        base_url: str | None,
        api_key: str | None = None,
        temperature: float,
        seed: int,
        max_tokens: int = 512,
        timeout_s: float = 30.0,
    ) -> None:
        self.provider_id = provider_id
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def stream_tokens(
        self,
        prompt: CognitionPrompt,
        *,
        cancel_check,
        deadline_monotonic: float,
    ) -> Iterator[str]:
        async def _collect() -> list[str]:
            from hg_llm import CompletionRequest, get_default_registry
            from hg_llm.adapters import register_default_adapters

            registry = get_default_registry()
            register_default_adapters(registry)
            chunks: list[str] = []
            extra: dict[str, object] = {"seed": self.seed}
            if self.base_url:
                extra["api_base"] = self.base_url
            request = CompletionRequest(
                messages=[dict(message) for message in prompt.messages],
                model=self.model_name,
                provider=self.provider_id,
                base_url=self.base_url,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens if self.max_tokens > 0 else None,
                extra=extra,
            )
            async for chunk in registry.stream_complete(request):
                if cancel_check():
                    raise CognitionCancelled("cognition halted")
                if time.monotonic() > deadline_monotonic:
                    raise CognitionTimeout("cognition timeout")
                if chunk:
                    chunks.append(chunk)
            return chunks

        try:
            chunks = asyncio.run(_collect())
        except CognitionCancelled:
            raise
        except CognitionTimeout:
            raise
        except Exception as exc:
            raise RuntimeError(f"live cognition provider failed: {exc}") from exc
        for chunk in chunks:
            yield chunk


__all__ = ["OpenAICompatibleProvider"]
