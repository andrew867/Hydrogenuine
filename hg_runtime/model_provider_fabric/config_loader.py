"""Load model provider fabric from example/operator config."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.model_provider_fabric.types import (
    ModelProviderConfig,
    ModelProviderRegistry,
    ModelProviderRole,
    ProviderType,
)

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "model_providers" / "model_provider_registry.json"
FALLBACK_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "model_providers" / "model_provider_fabric.example.json"


def _as_roles(raw: list[str] | tuple[str, ...]) -> tuple[ModelProviderRole, ...]:
    return tuple(raw)  # type: ignore[return-value]


def config_from_dict(data: dict[str, Any]) -> ModelProviderConfig:
    if data.get("permission_granted") or data.get("authority_created"):
        raise ValueError("provider config must not grant permission")
    return ModelProviderConfig(
        provider_id=str(data["provider_id"]),
        provider_type=data["provider_type"],  # type: ignore[arg-type]
        model_id=str(data.get("model_id", "")),
        endpoint_url=data.get("endpoint_url"),
        health_url=data.get("health_url"),
        devices_url=data.get("devices_url"),
        device=str(data.get("device", "AUTO")),
        role_allowlist=_as_roles(data.get("role_allowlist", [])),
        enabled=bool(data.get("enabled", False)),
        timeout_seconds=int(data.get("timeout_seconds", 60)),
        max_context_tokens=int(data.get("max_context_tokens", 4096)),
        max_output_tokens=int(data.get("max_output_tokens", 256)),
        streaming_supported=bool(data.get("streaming_supported", False)),
        cost_class=data.get("cost_class", "local"),  # type: ignore[arg-type]
        privacy_class=data.get("privacy_class", "local"),  # type: ignore[arg-type]
        data_policy=str(data.get("data_policy", "advisory_only")),
        fallback_priority=int(data.get("fallback_priority", 100)),
        external_network_required=bool(data.get("external_network_required", False)),
        requires_secret=bool(data.get("requires_secret", False)),
        secret_env_var=data.get("secret_env_var"),
        allow_fallback_stub=bool(data.get("allow_fallback_stub", False)),
    )


def load_registry(path: Path | None = None, *, extra_paths: list[Path] | None = None) -> ModelProviderRegistry:
    primary = path or DEFAULT_CONFIG
    if not primary.is_file():
        primary = FALLBACK_CONFIG
    paths = [primary]
    if extra_paths:
        paths.extend(extra_paths)
    registry = ModelProviderRegistry()
    for cfg_path in paths:
        if not cfg_path.is_file():
            continue
        payload = json.loads(cfg_path.read_text(encoding="utf-8"))
        for entry in payload.get("providers", []):
            registry.register(config_from_dict(entry))
    return registry


def secret_available(config: ModelProviderConfig) -> bool:
    if not config.requires_secret:
        return True
    if not config.secret_env_var:
        return False
    value = os.environ.get(config.secret_env_var, "").strip()
    return bool(value)


def external_network_allowed(env: dict[str, str] | None = None) -> bool:
    env = env or os.environ
    flag = env.get("HG_EXTERNAL_NETWORK_ALLOWED", env.get("HG_NO_NETWORK", "1"))
    if env.get("HG_EXTERNAL_NETWORK_ALLOWED", "").strip() in {"1", "true", "TRUE", "yes"}:
        return True
    if env.get("HG_NO_NETWORK", "").strip() in {"1", "true", "TRUE"}:
        return False
    return False


__all__ = [
    "DEFAULT_CONFIG",
    "config_from_dict",
    "external_network_allowed",
    "load_registry",
    "secret_available",
]
