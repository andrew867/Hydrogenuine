"""RTC cognition service configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


class LiveCognitionConfigError(ValueError):
    """Raised when HG_RTC_COGNITION_LIVE=1 but required provider settings are missing."""


@dataclass(frozen=True)
class CognitionConfig:
    provider: str = "fake"
    model: str = "rtc-fake-model"
    timeout_s: float = 30.0
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 512
    live_enabled: bool = False
    offline: bool = True

    @property
    def uses_live_model(self) -> bool:
        return self.provider in {"openai", "vllm"} and self.live_enabled and not self.offline


def _resolve_timeout_s() -> float:
    for key in ("HG_RTC_COGNITION_TIMEOUT_SECONDS", "HG_RTC_COGNITION_TIMEOUT_S"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return float(raw)
    return 30.0


def _resolve_api_key(provider: str) -> str | None:
    explicit = os.environ.get("HG_RTC_COGNITION_API_KEY", "").strip()
    if explicit:
        return explicit
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY", "").strip() or None
    if provider == "vllm":
        return os.environ.get("OPENAI_API_KEY", "").strip() or "EMPTY"
    return None


def validate_live_config(config: CognitionConfig) -> None:
    """Fail clearly when live cognition is requested but misconfigured."""
    if not config.live_enabled or config.offline:
        return
    if config.provider not in {"openai", "vllm"}:
        raise LiveCognitionConfigError(
            f"HG_RTC_COGNITION_LIVE=1 requires HG_RTC_COGNITION_PROVIDER=openai or vllm "
            f"(got {config.provider!r})"
        )
    if not config.model:
        raise LiveCognitionConfigError(
            "HG_RTC_COGNITION_MODEL is required when HG_RTC_COGNITION_LIVE=1"
        )
    if config.provider == "vllm" and not config.base_url:
        raise LiveCognitionConfigError(
            "HG_RTC_COGNITION_BASE_URL (or HG_VLLM_BASE_URL) is required for vllm "
            "when HG_RTC_COGNITION_LIVE=1"
        )
    if config.provider == "openai" and not config.api_key:
        raise LiveCognitionConfigError(
            "HG_RTC_COGNITION_API_KEY or OPENAI_API_KEY is required for openai "
            "when HG_RTC_COGNITION_LIVE=1"
        )


def load_cognition_config() -> CognitionConfig:
    provider = os.environ.get("HG_RTC_COGNITION_PROVIDER", "fake").strip().lower()
    model = os.environ.get("HG_RTC_COGNITION_MODEL", "").strip()
    if not model:
        if provider == "vllm":
            model = os.environ.get("HG_VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
        elif provider == "openai":
            model = os.environ.get("HG_OPENAI_MODEL", "gpt-4o-mini").strip()
        else:
            model = "rtc-fake-model"
    base_url = os.environ.get("HG_RTC_COGNITION_BASE_URL", "").strip() or None
    if provider == "vllm" and base_url is None:
        base_url = (
            os.environ.get("HG_VLLM_BASE_URL", "").strip()
            or os.environ.get("VLLM_BASE_URL", "").strip()
            or None
        )
    temp_raw = os.environ.get("HG_RTC_COGNITION_TEMPERATURE", "0").strip()
    seed_raw = os.environ.get("HG_RTC_COGNITION_SEED", "0").strip()
    max_tokens_raw = os.environ.get("HG_RTC_COGNITION_MAX_TOKENS", "512").strip()
    live_enabled = os.environ.get("HG_RTC_COGNITION_LIVE", "").strip() == "1"
    offline_flag = os.environ.get("HG_RTC_COGNITION_OFFLINE", "").strip().lower()
    offline = provider == "fake" or offline_flag in {"1", "true", "yes"} or not live_enabled
    config = CognitionConfig(
        provider=provider,
        model=model,
        timeout_s=_resolve_timeout_s(),
        base_url=base_url,
        api_key=_resolve_api_key(provider),
        temperature=float(temp_raw),
        seed=int(seed_raw),
        max_tokens=int(max_tokens_raw),
        live_enabled=live_enabled,
        offline=offline,
    )
    if config.uses_live_model:
        validate_live_config(config)
    return config


__all__ = [
    "CognitionConfig",
    "LiveCognitionConfigError",
    "load_cognition_config",
    "validate_live_config",
]
