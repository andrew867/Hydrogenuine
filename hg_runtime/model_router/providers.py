"""Provider registry and the fully-functional fake local provider.

Only the fake local provider runs in tests: it performs no network, no shell, and
no real model loading -- it just emits planned/dry-run records. Network providers
refuse by default; credential-bearing provider config is rejected.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.model_router.schemas import (
    EXTERNAL_PROVIDER_KINDS,
    LOCAL_PROVIDER_KINDS,
    MODEL_PROVIDER_SCHEMA,
    PROVIDER_KINDS,
    REFUSING_PROVIDER_KINDS,
    ModelRouterError,
    locator_is_credential,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def register_provider(payload: Mapping[str, Any], *, allow_network: bool = False) -> dict[str, Any]:
    require_fields(payload, ("provider_id", "kind"))
    data = dict(payload)
    reject_authority_payload(data)
    kind = str(data["kind"])
    if kind not in PROVIDER_KINDS:
        raise ModelRouterError(f"schema_violation:unknown_provider_kind:{kind}")

    endpoint = str(data.get("endpoint", ""))
    if endpoint and locator_is_credential(endpoint):
        raise ModelRouterError("credential_provider_read_rejected")
    for value in data.get("config", {}).values() if isinstance(data.get("config"), Mapping) else []:
        if isinstance(value, str) and locator_is_credential(value):
            raise ModelRouterError("credential_provider_read_rejected")

    if kind in EXTERNAL_PROVIDER_KINDS and not allow_network:
        raise ModelRouterError("network_provider_refuses_by_default")

    residency = "external" if kind in EXTERNAL_PROVIDER_KINDS else "local"
    return {
        "schema": MODEL_PROVIDER_SCHEMA,
        "provider_id": data["provider_id"],
        "kind": kind,
        "residency": residency,
        "dry_run": kind != "fake_local",
        "enabled": kind not in REFUSING_PROVIDER_KINDS,
        "supports_load": kind in LOCAL_PROVIDER_KINDS,
        **neutral_flags(),
    }


class FakeLocalProvider:
    """A fully-functional, side-effect-free local provider for tests.

    It never touches the network or shell and never loads a real model; it returns
    planned residency records and synthetic health checks only.
    """

    kind = "fake_local"
    dry_run = False  # fully functional, but purely in-memory

    def __init__(self, provider_id: str = "fake-local-1") -> None:
        self.provider_id = provider_id

    def plan_load(self, model_id: str) -> dict[str, Any]:
        return {"provider_id": self.provider_id, "model_id": model_id, "executed": True, "real_call": False, "network": False}

    def plan_unload(self, model_id: str) -> dict[str, Any]:
        return {"provider_id": self.provider_id, "model_id": model_id, "executed": True, "real_call": False, "network": False}

    def health_check(self, model_id: str, *, healthy: bool = True) -> dict[str, Any]:
        return {"provider_id": self.provider_id, "model_id": model_id, "healthy": healthy, "network": False}


__all__ = ["FakeLocalProvider", "register_provider"]
