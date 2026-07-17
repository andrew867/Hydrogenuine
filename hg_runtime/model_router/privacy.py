"""Privacy-tier records and checks.

Privacy-sensitive input must never leave for an external provider. Sensitive/secret
tiers are external-forbidden; an external provider also requires explicit privacy
clearance before it may be considered at all.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.model_router.schemas import (
    EXTERNAL_FORBIDDEN_TIERS,
    MODEL_PRIVACY_TIER_SCHEMA,
    PRIVACY_TIERS,
    ModelRouterError,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def define_privacy_tier(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("tier",))
    data = dict(payload)
    reject_authority_payload(data)
    tier = str(data["tier"]).strip().lower()
    if tier not in PRIVACY_TIERS:
        raise ModelRouterError(f"schema_violation:unknown_privacy_tier:{tier}")
    # Sensitive/secret tiers can never be marked external-allowed.
    external_allowed = False if tier in EXTERNAL_FORBIDDEN_TIERS else bool(data.get("external_allowed", False))
    return {
        "schema": MODEL_PRIVACY_TIER_SCHEMA,
        "tier": tier,
        "external_allowed": external_allowed,
        **neutral_flags(),
    }


def check_privacy(privacy_tier: Mapping[str, Any], provider: Mapping[str, Any]) -> None:
    """Refuse routing privacy-sensitive input to an external provider."""
    tier = str(privacy_tier.get("tier", "")).strip().lower()
    is_external = str(provider.get("residency")) == "external"
    if is_external:
        if tier in EXTERNAL_FORBIDDEN_TIERS or not privacy_tier.get("external_allowed"):
            if tier in EXTERNAL_FORBIDDEN_TIERS:
                raise ModelRouterError("privacy_sensitive_input_blocks_external_model")
            raise ModelRouterError("external_provider_requires_privacy_clearance")


__all__ = ["check_privacy", "define_privacy_tier"]
