"""
LiteLLM adapter: backbone for OpenAI, Anthropic, Google, xAI, vLLM.

Uses litellm.completion() and litellm.acompletion(..., stream=True).
Model format: provider/model (e.g. openai/gpt-4o-mini, anthropic/claude-3-5-sonnet).
For vLLM, pass base_url in request.extra or request.base_url.

Pack 14: timeouts, bounded retries (429/5xx), circuit breaker, usage metrics,
X-Request-ID propagation, optional OTEL, redaction of sensitive prompt data in logs.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, AsyncIterator, Dict, List

from hg_llm.abstraction import CompletionRequest, CompletionResponse

try:
    import litellm
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    litellm = None  # type: ignore[assignment]

# Optional: use hg_core reliability for circuit breaker and timeout
try:
    from hg_core.runtime.reliability import (
        can_execute_breaker,
        get_llm_timeout_s,
        record_breaker_failure,
        record_breaker_success,
        retry_with_jitter,
    )
    _RELIABILITY_AVAILABLE = True
except ImportError:
    _RELIABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Env: LITELLM_BASE_URL, LITELLM_API_KEY, HG_DEFAULT_MODEL (see spec)
# LITELLM_TIMEOUT_SECONDS overrides HG_LLM_TIMEOUT_S when set
# LITELLM_MAX_RETRIES: max retries for 429/5xx (default 3)


def _get_timeout_s() -> int:
    """LLM call timeout in seconds. LITELLM_TIMEOUT_SECONDS or HG_LLM_TIMEOUT_S or 120."""
    if _RELIABILITY_AVAILABLE:
        base = get_llm_timeout_s()
    else:
        base = max(10, int(os.environ.get("HG_LLM_TIMEOUT_S", "120")))
    override = os.environ.get("LITELLM_TIMEOUT_SECONDS")
    return int(override) if override else base


def _get_max_retries() -> int:
    return max(0, min(10, int(os.environ.get("LITELLM_MAX_RETRIES", "3"))))


def _redact_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a copy of messages with content redacted for safe logging."""
    out = []
    for m in messages:
        copy = dict(m)
        if "content" in copy and isinstance(copy["content"], str):
            copy["content"] = "[redacted]" if copy["content"].strip() else ""
        out.append(copy)
    return out


def _is_retryable_error(e: Exception) -> bool:
    """True for 429 and 5xx so we retry with backoff."""
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    if code is not None:
        if code == 429:
            return True
        if 500 <= int(code) < 600:
            return True
    name = type(e).__name__
    if "RateLimit" in name or "Timeout" in name:
        return True
    if "APIError" in name or "APIConnectionError" in name:
        return True
    return False


def _get_api_key(req: CompletionRequest, env_default: str) -> str | None:
    if req.api_key:
        return req.api_key
    env_name = req.api_key_env or env_default
    return os.environ.get(env_name) or None


def _litellm_model(req: CompletionRequest) -> str:
    """Build LiteLLM model string: provider/model. For vLLM with base_url use hosted_vllm/model."""
    provider = (req.provider or "openai").lower()
    model = req.model
    base_url = req.base_url or req.extra.get("base_url")
    if "/" in model and not (provider == "vllm" and base_url):
        # Already provider/model
        return model
    if provider == "vllm" and base_url:
        return f"openai/{model}"  # OpenAI-compatible; api_base set in _litellm_kwargs
    prefix = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google",
        "gemini": "google",
        "xai": "xai",
        "vllm": "openai",
    }.get(provider, "openai")
    return f"{prefix}/{model}"


def _litellm_kwargs(req: CompletionRequest) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if req.max_tokens is not None:
        kwargs["max_tokens"] = req.max_tokens
    if req.temperature is not None:
        kwargs["temperature"] = req.temperature
    base_url = req.base_url or req.extra.get("base_url")
    if base_url:
        kwargs["api_base"] = base_url.rstrip("/")
    api_key = _get_api_key(req, "OPENAI_API_KEY")
    if api_key and req.provider == "anthropic":
        kwargs["api_key"] = api_key
    elif api_key and req.provider == "google":
        kwargs["api_key"] = api_key
    elif api_key and req.provider == "xai":
        kwargs["api_key"] = api_key
    elif api_key:
        kwargs["api_key"] = api_key
    requested_timeout = req.extra.get("timeout_s") if req.extra else None
    kwargs["timeout"] = max(10, int(requested_timeout)) if requested_timeout is not None else _get_timeout_s()
    request_id = req.extra.get("request_id") if req.extra else None
    if request_id:
        kwargs["metadata"] = {"request_id": str(request_id)}
    return kwargs


def _breaker_key(model: str) -> str:
    return f"llm:{model or 'default'}"


class LiteLLMAdapter:
    """Single adapter for all LiteLLM-backed providers (openai, anthropic, google, xai, vllm)."""

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not _LITELLM_AVAILABLE or litellm is None:
            raise RuntimeError("litellm is required. Install with: pip install litellm")
        model = _litellm_model(request)
        kwargs = _litellm_kwargs(request)
        breaker_key = _breaker_key(model)

        if _RELIABILITY_AVAILABLE and not can_execute_breaker(breaker_key):
            raise RuntimeError(f"Circuit breaker open for {breaker_key}; LLM calls temporarily disabled")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("LiteLLM completion request (redacted): model=%s messages=%s", model, _redact_messages(request.messages))

        start = time.perf_counter()

        def _call() -> Any:
            return litellm.completion(
                model=model,
                messages=request.messages,
                stream=False,
                **kwargs,
            )

        requested_retries = request.extra.get("max_retries") if request.extra else None
        max_retries = (
            max(0, min(10, int(requested_retries)))
            if requested_retries is not None
            else _get_max_retries()
        )
        try:
            if _RELIABILITY_AVAILABLE and max_retries > 0:
                response = retry_with_jitter(
                    _call,
                    max_retries=max_retries,
                    base_delay_s=1.0,
                    max_delay_s=30.0,
                    is_retryable=_is_retryable_error,
                )
            else:
                response = _call()
        except Exception as e:
            if _RELIABILITY_AVAILABLE:
                record_breaker_failure(breaker_key)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("LiteLLM completion failed (redacted): model=%s error=%s", model, str(e))
            raise RuntimeError(f"LiteLLM completion failed: {e}") from e

        if _RELIABILITY_AVAILABLE:
            record_breaker_success(breaker_key)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        choice = response.choices[0] if response.choices else None
        content = (choice.message.content or "") if choice and choice.message else ""
        usage: Dict[str, int] | None = None
        if getattr(response, "usage", None):
            u = response.usage
            usage = {}
            if getattr(u, "prompt_tokens", None) is not None:
                usage["prompt_tokens"] = u.prompt_tokens
            if getattr(u, "completion_tokens", None) is not None:
                usage["completion_tokens"] = u.completion_tokens
            if getattr(u, "total_tokens", None) is not None:
                usage["total_tokens"] = u.total_tokens
            usage["latency_ms"] = elapsed_ms
        else:
            usage = {"latency_ms": elapsed_ms}
        return CompletionResponse(
            content=content,
            usage=usage,
            model=getattr(response, "model", None),
            finish_reason=getattr(choice, "finish_reason", None) if choice else None,
            raw=response,
        )

    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        if not _LITELLM_AVAILABLE or litellm is None:
            raise RuntimeError("litellm is required. Install with: pip install litellm")
        model = _litellm_model(request)
        kwargs = _litellm_kwargs(request)
        breaker_key = _breaker_key(model)
        if _RELIABILITY_AVAILABLE and not can_execute_breaker(breaker_key):
            raise RuntimeError(f"Circuit breaker open for {breaker_key}; LLM calls temporarily disabled")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("LiteLLM stream request (redacted): model=%s messages=%s", model, _redact_messages(request.messages))
        try:
            stream = await litellm.acompletion(
                model=model,
                messages=request.messages,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            if _RELIABILITY_AVAILABLE:
                record_breaker_success(breaker_key)
        except Exception as e:
            if _RELIABILITY_AVAILABLE:
                record_breaker_failure(breaker_key)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("LiteLLM stream failed (redacted): model=%s error=%s", model, str(e))
            raise RuntimeError(f"LiteLLM stream completion failed: {e}") from e
