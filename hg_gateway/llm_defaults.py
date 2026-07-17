"""Shared default LLM provider/model resolution without store/orchestration cycles."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

SAFE_LOCAL_ONLY_ENV = "SAFE_LOCAL_ONLY"
SAFE_LOCAL_PROVIDER = "stub"
SAFE_LOCAL_MODEL = "local-deterministic"

DEFAULT_PROVIDER = "anthropic"
DEFAULT_PROVIDER_MODELS: Dict[str, str] = {
    "google": "gemini-2.0-flash",
    "openai": "gpt-4.1-mini",
    "xai": "grok-3-fast",
    "anthropic": "claude-haiku-4-5",
    "vllm": "openai/gpt-4.1-mini",
    SAFE_LOCAL_PROVIDER: SAFE_LOCAL_MODEL,
}
DEFAULT_PROVIDER_MODEL_CANDIDATES: Dict[str, List[str]] = {
    "google": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"],
    "openai": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"],
    "xai": ["grok-3-fast", "grok-3-mini", "grok-2-1212"],
    "anthropic": ["claude-haiku-4-5", "claude-sonnet-4-20250514", "claude-3-7-sonnet-latest"],
    "vllm": ["openai/gpt-4.1-mini", "meta-llama/Llama-3.1-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"],
    SAFE_LOCAL_PROVIDER: [SAFE_LOCAL_MODEL],
}
PROVIDER_KEY_ENVS: Dict[str, str] = {
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "xai": "XAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "vllm": "OPENAI_API_KEY",
}
PROVIDER_BASE_URL_ENVS: Dict[str, tuple[str, ...]] = {
    "google": (),
    "openai": ("OPENAI_BASE_URL",),
    "xai": ("XAI_BASE_URL", "OPENAI_BASE_URL"),
    "anthropic": ("ANTHROPIC_BASE_URL",),
    "vllm": ("HG_VLLM_BASE_URL", "VLLM_BASE_URL", "OPENAI_BASE_URL"),
}


def is_safe_local_only() -> bool:
    value = (os.environ.get(SAFE_LOCAL_ONLY_ENV) or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_default_provider() -> str:
    if is_safe_local_only():
        return SAFE_LOCAL_PROVIDER
    return (os.environ.get("HG_DEFAULT_PROVIDER") or DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER


def get_default_model(provider: Optional[str] = None) -> str:
    resolved_provider = (provider or get_default_provider()).strip().lower() or DEFAULT_PROVIDER
    if is_safe_local_only():
        return (os.environ.get("HG_STUB_MODEL") or SAFE_LOCAL_MODEL).strip() or SAFE_LOCAL_MODEL
    env_candidates = {
        "google": ("HG_GOOGLE_MODEL", "GOOGLE_MODEL"),
        "openai": ("HG_OPENAI_MODEL", "OPENAI_MODEL", "HG_DEFAULT_MODEL", "LITELLM_MODEL"),
        "xai": ("HG_XAI_MODEL", "XAI_MODEL"),
        "anthropic": ("HG_ANTHROPIC_MODEL", "ANTHROPIC_MODEL"),
        "vllm": ("HG_VLLM_MODEL", "VLLM_MODEL", "HG_DEFAULT_MODEL", "LITELLM_MODEL"),
    }.get(resolved_provider, ("HG_DEFAULT_MODEL", "LITELLM_MODEL"))
    for env_name in env_candidates:
        value = (os.environ.get(env_name) or "").strip()
        if value:
            return value
    return DEFAULT_PROVIDER_MODELS.get(resolved_provider, DEFAULT_PROVIDER_MODELS[DEFAULT_PROVIDER])


def get_default_base_url(provider: Optional[str] = None) -> Optional[str]:
    if is_safe_local_only():
        return None
    resolved_provider = (provider or get_default_provider()).strip().lower() or DEFAULT_PROVIDER
    for env_name in PROVIDER_BASE_URL_ENVS.get(resolved_provider, ()):
        value = (os.environ.get(env_name) or "").strip()
        if value:
            return value.rstrip("/")
    return None


def get_model_candidates(provider: Optional[str] = None) -> List[str]:
    resolved_provider = (provider or get_default_provider()).strip().lower() or DEFAULT_PROVIDER
    if is_safe_local_only():
        stub_model = (os.environ.get("HG_STUB_MODEL") or SAFE_LOCAL_MODEL).strip() or SAFE_LOCAL_MODEL
        return [stub_model]
    explicit_envs = {
        "google": ("HG_GOOGLE_MODEL_CANDIDATES", "GOOGLE_MODEL_CANDIDATES"),
        "openai": ("HG_OPENAI_MODEL_CANDIDATES", "OPENAI_MODEL_CANDIDATES"),
        "xai": ("HG_XAI_MODEL_CANDIDATES", "XAI_MODEL_CANDIDATES"),
        "anthropic": ("HG_ANTHROPIC_MODEL_CANDIDATES", "ANTHROPIC_MODEL_CANDIDATES"),
        "vllm": ("HG_VLLM_MODEL_CANDIDATES", "VLLM_MODEL_CANDIDATES"),
    }.get(resolved_provider, ())
    seen: set[str] = set()
    out: List[str] = []

    def _add(value: str) -> None:
        item = value.strip()
        if item and item not in seen:
            out.append(item)
            seen.add(item)

    for env_name in explicit_envs:
        raw = (os.environ.get(env_name) or "").strip()
        if not raw:
            continue
        for item in raw.split(","):
            _add(item)
    _add(get_default_model(resolved_provider))
    for item in DEFAULT_PROVIDER_MODEL_CANDIDATES.get(resolved_provider, []):
        _add(item)
    return out
