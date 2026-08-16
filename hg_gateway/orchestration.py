from __future__ import annotations

import logging
import os
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from hg_gateway.llm_defaults import (
    DEFAULT_PROVIDER,
    PROVIDER_KEY_ENVS,
    get_default_base_url,
    get_default_model,
    get_default_provider,
    get_model_candidates,
    is_safe_local_only,
)
from hg_gateway.store import MessageRow, get_store

logger = logging.getLogger(__name__)

LLM_UNAVAILABLE_MSG = "(Local model not available; configure a local OpenAI-compatible endpoint or use safe local mode.)"


def get_fallback_chain(
    preferred_provider: Optional[str] = None,
    preferred_model: Optional[str] = None,
    preferred_base_url: Optional[str] = None,
    preferred_key_env: Optional[str] = None,
) -> List[Tuple[str, str, str, Optional[str]]]:
    if is_safe_local_only():
        return [("stub", get_default_model("stub"), "", None)]
    provider = (preferred_provider or get_default_provider() or DEFAULT_PROVIDER).strip().lower()
    model = (preferred_model or get_default_model(provider)).strip()
    key_env = (preferred_key_env or PROVIDER_KEY_ENVS.get(provider, "")).strip()
    base_url = preferred_base_url or get_default_base_url(provider)
    chain = [(provider, model, key_env, base_url)]

    # A configured cloud provider is an available fallback, not a global
    # prerequisite. Providers without credentials are omitted silently; the
    # selected provider still produces the precise error if its own credential
    # is missing.
    for fallback_provider, fallback_key_env in PROVIDER_KEY_ENVS.items():
        if fallback_provider in {provider, "vllm"}:
            continue
        if not fallback_key_env or not os.environ.get(fallback_key_env, "").strip():
            continue
        fallback_base_url = get_default_base_url(fallback_provider)
        for fallback_model in get_model_candidates(fallback_provider):
            chain.append((fallback_provider, fallback_model, fallback_key_env, fallback_base_url))
    if provider != "vllm":
        chain.append(("vllm", get_default_model("vllm"), PROVIDER_KEY_ENVS.get("vllm", ""), get_default_base_url("vllm")))
    chain.append(("stub", get_default_model("stub"), "", None))
    out: List[Tuple[str, str, str, Optional[str]]] = []
    seen: set[Tuple[str, str, str, Optional[str]]] = set()
    for item in chain:
        if item[1] and item not in seen:
            out.append(item)
            seen.add(item)
    return out


async def _stream_model(
    messages: List[Dict[str, str]],
    *,
    provider: Optional[str],
    model: Optional[str],
    base_url: Optional[str],
    api_key_env: Optional[str],
    max_tokens: int,
    temperature: float,
) -> AsyncIterator[str]:
    try:
        from hg_llm import get_default_registry

        registry = get_default_registry()
    except Exception as exc:
        logger.debug("model registry unavailable: %s", exc)
        registry = None
    if registry is None:
        yield LLM_UNAVAILABLE_MSG
        return

    for prov, mod, key_env, resolved_base_url in get_fallback_chain(provider, model, base_url, api_key_env):
        if prov not in {"vllm", "stub"} and key_env and not os.environ.get(key_env, "").strip():
            continue
        if prov == "vllm" and not resolved_base_url:
            continue
        parts: List[str] = []
        try:
            async for chunk in registry.stream_complete(
                messages=messages,
                model=mod,
                provider=prov,
                base_url=resolved_base_url,
                api_key_env=key_env,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                parts.append(chunk)
                yield chunk
            if parts:
                return
        except Exception as exc:
            logger.debug("model attempt failed for %s/%s: %s", prov, mod, exc)
            continue
    yield LLM_UNAVAILABLE_MSG


async def run_turn(
    tenant_id: str,
    chat_id: str,
    agent_id: str,
    agent_label: str,
    messages_for_llm: List[Dict[str, str]],
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key_env: Optional[str] = None,
    emit: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    prompt_id: str = "default",
    model_config_id: str = "default",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    steering_profiles_resolved: Optional[List[Dict[str, Any]]] = None,
    final_payload_extra: Optional[Dict[str, Any]] = None,
) -> MessageRow:
    store = get_store()
    if emit:
        emit("agent.status", {"agent_id": agent_id, "label": agent_label, "status": "working"})
    store.agent_upsert(tenant_id, chat_id, agent_id, agent_label, "working", parent_agent_id=None)
    parts: List[str] = []
    async for chunk in _stream_model(
        messages_for_llm,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
        max_tokens=max_tokens,
        temperature=temperature,
    ):
        parts.append(chunk)
        if emit:
            emit("message.delta", {"delta": chunk, "agent_id": agent_id})
    content = "".join(parts).strip() or LLM_UNAVAILABLE_MSG
    row = store.message_add(tenant_id, chat_id, "assistant", content, agent_id=agent_id)
    if hasattr(store, "turn_provenance_add"):
        store.turn_provenance_add(tenant_id, row.message_id, prompt_id, model_config_id, {"max_tokens": max_tokens, "temperature": temperature})
    store.agent_upsert(tenant_id, chat_id, agent_id, agent_label, "idle", parent_agent_id=None)
    if emit:
        emit("agent.status", {"agent_id": agent_id, "label": agent_label, "status": "idle"})
        emit("message.final", {"message_id": row.message_id, "chat_id": chat_id, "content": content, **(final_payload_extra or {})})
    return row
