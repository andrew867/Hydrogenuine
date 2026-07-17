"""P32 model registry — enumerates available models (fixture only, no live providers)."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import assert_neutral
from hg_runtime.model_routing.schemas import (
    MODEL_ROLES,
    MODEL_TIERS,
    PROVIDER_STATES,
    ModelRoutingBoundaryError,
)


def create_registry_entry(
    *,
    model_id: str,
    role: str,
    tier: str = "local_fixture",
    provider_state: str = "disabled",
    capabilities: dict[str, bool] | None = None,
) -> dict[str, Any]:
    if role not in MODEL_ROLES:
        raise ModelRoutingBoundaryError(f"invalid role: {role}")
    if tier not in MODEL_TIERS:
        raise ModelRoutingBoundaryError(f"invalid tier: {tier}")
    if provider_state not in PROVIDER_STATES:
        raise ModelRoutingBoundaryError(f"invalid provider_state: {provider_state}")

    record = {
        "schema": "model_registry_entry_v1",
        "model_id": model_id,
        "role": role,
        "tier": tier,
        "provider_state": provider_state,
        "capabilities": capabilities or {},
        "model_output_is_not_truth": True,
        "model_selection_is_not_authority": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record, "entry_hash")


def builtin_registry() -> list[dict[str, Any]]:
    entries = []
    for role in sorted(MODEL_ROLES):
        entries.append(create_registry_entry(
            model_id=f"fixture_{role}_v1",
            role=role,
            tier="local_fixture",
            provider_state="disabled",
        ))
    return entries


def preflight_check(registry: list[dict[str, Any]]) -> dict[str, Any]:
    roles_covered = {e["role"] for e in registry}
    missing_roles = MODEL_ROLES - roles_covered
    providers_enabled = any(
        e.get("provider_state") not in ("disabled", "fixture_only_local_only")
        for e in registry
    )
    return {
        "roles_covered": sorted(roles_covered),
        "missing_roles": sorted(missing_roles),
        "all_roles_covered": len(missing_roles) == 0,
        "providers_enabled": providers_enabled,
        "preflight_ok": len(missing_roles) == 0 and not providers_enabled,
        "preflight_is_not_authority": True,
    }
