"""Provider selection with local-first failover chain."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.model_provider_fabric.adapters.cloud import cloud_providers_enabled
from hg_runtime.model_provider_fabric.config_loader import (
    external_network_allowed,
    load_registry,
    secret_available,
)
from hg_runtime.model_provider_fabric.openvino_probe import probe_openvino_health
from hg_runtime.model_provider_fabric.types import ModelProviderConfig, ProviderHealth

WORKSPACE = Path(__file__).resolve().parents[2]
REGISTRY_PATH = WORKSPACE / "configs/model_providers/model_provider_registry.json"


@dataclass(frozen=True)
class ProviderSelection:
    provider_id: str
    provider_type: str
    model_id: str
    endpoint_url: str | None
    source: str
    health: ProviderHealth | None = None
    cloud_backup: bool = False


def _probe_config(config: ModelProviderConfig) -> ProviderHealth | None:
    if config.provider_type == "openvino_windows":
        return probe_openvino_health(config)
    return None


def _cloud_eligible(config: ModelProviderConfig) -> bool:
    if not config.enabled:
        return False
    if not cloud_providers_enabled():
        return False
    if config.external_network_required and not external_network_allowed():
        return False
    if config.requires_secret and not secret_available(config):
        return False
    return True


def select_provider_for_role(role: str, *, registry_path: Path | None = None) -> ProviderSelection | None:
    """Select best provider: local OpenVINO first, then xAI → Anthropic → OpenAI when enabled."""
    registry = load_registry(registry_path or REGISTRY_PATH)
    role_upper = role.strip().upper()
    candidates = list(registry.providers.values())
    candidates = [c for c in candidates if c.enabled and role_upper in {str(r).upper() for r in c.role_allowlist}]
    candidates.sort(key=lambda c: c.fallback_priority)

    for config in candidates:
        if config.provider_type == "openvino_windows":
            health = _probe_config(config)
            if health and health.reachable and health.healthy and health.model_loaded:
                return ProviderSelection(
                    provider_id=config.provider_id,
                    provider_type=config.provider_type,
                    model_id=config.model_id,
                    endpoint_url=config.endpoint_url,
                    source="local_openvino",
                    health=health,
                    cloud_backup=False,
                )
            if health and health.reachable and health.healthy and health.fallback_stub:
                continue
        elif config.provider_type in ("xai_compatible", "anthropic_compatible", "openai_compatible"):
            if _cloud_eligible(config):
                return ProviderSelection(
                    provider_id=config.provider_id,
                    provider_type=config.provider_type,
                    model_id=config.model_id,
                    endpoint_url=config.endpoint_url,
                    source="cloud_backup",
                    health=None,
                    cloud_backup=True,
                )
    return None


def selection_summary(role: str = "AGENT_TURN_DECISION") -> dict[str, Any]:
    sel = select_provider_for_role(role)
    if sel is None:
        return {
            "selected": False,
            "role": role,
            "cloud_providers_enabled": cloud_providers_enabled(),
            "external_network_allowed": external_network_allowed(),
        }
    return {
        "selected": True,
        "role": role,
        "provider_id": sel.provider_id,
        "provider_type": sel.provider_type,
        "model_id": sel.model_id,
        "endpoint_url": sel.endpoint_url,
        "source": sel.source,
        "cloud_backup": sel.cloud_backup,
        "openvino_verdict": sel.health.openvino_verdict if sel.health else None,
        "model_loaded": sel.health.model_loaded if sel.health else None,
        "resolved_device": sel.health.resolved_device if sel.health else None,
    }


__all__ = ["ProviderSelection", "select_provider_for_role", "selection_summary"]
