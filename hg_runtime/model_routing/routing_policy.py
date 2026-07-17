"""P32 routing policy — defines how model selection works (advisory only)."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import assert_neutral
from hg_runtime.model_routing.schemas import (
    MODEL_ROLES,
    ROUTING_MODES,
    PROVIDER_STATES,
    ModelRoutingBoundaryError,
)


def create_routing_policy(
    *,
    routing_mode: str = "fixture_only",
    provider_state: str = "disabled",
    allowed_roles: frozenset[str] | None = None,
) -> dict[str, Any]:
    if routing_mode not in ROUTING_MODES:
        raise ModelRoutingBoundaryError(f"invalid routing_mode: {routing_mode}")
    if provider_state not in PROVIDER_STATES:
        raise ModelRoutingBoundaryError(f"invalid provider_state: {provider_state}")

    roles = sorted(allowed_roles or MODEL_ROLES)
    for r in roles:
        if r not in MODEL_ROLES:
            raise ModelRoutingBoundaryError(f"invalid role: {r}")

    record = {
        "schema": "routing_policy_v1",
        "routing_mode": routing_mode,
        "provider_state": provider_state,
        "model_roles": roles,
        "model_selection_is_not_authority": True,
        "routing_recommendation_is_advisory": True,
        "no_route_enables_providers": True,
        "no_route_reads_hg_local": True,
        "no_route_prints_secrets": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record, "policy_hash")
