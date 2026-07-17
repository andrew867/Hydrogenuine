"""ERB static relation classifier — entity/relation typing only."""

from __future__ import annotations

from typing import Any

from hg_core.erb_cluster.no_authority import advisory_only_marker
from hg_runtime.external_relation_boundary.types import (
    ExternalEntityRef,
    ExternalRelationContext,
    EntityType,
    RelationMode,
    RiskType,
    Sensitivity,
    classify_relation_claim_risk,
)

_ENTITY_RELATION_DEFAULTS: dict[EntityType, tuple[RelationMode, Sensitivity]] = {
    "operator": ("operator_control", "internal"),
    "user": ("conversation", "private"),
    "peer_agent": ("peer_agent_interaction", "internal"),
    "platform": ("platform_host", "public"),
    "public_audience": ("publication_audience", "public"),
    "community": ("public_observation", "public"),
    "source": ("citation_source", "public"),
    "collaborator": ("collaborator", "private"),
    "model_provider": ("tool_provider", "internal"),
    "api_provider": ("tool_provider", "internal"),
    "remote_service": ("tool_provider", "internal"),
    "repository": ("research_source", "public"),
    "website": ("research_source", "public"),
    "social_graph": ("public_observation", "public"),
    "robot_body": ("tool_provider", "restricted"),
    "adversary": ("adversarial_contact", "restricted"),
    "unknown": ("unknown", "unknown"),
}

_STATIC_RISKS_BY_ENTITY: dict[EntityType, tuple[RiskType, ...]] = {
    "public_audience": ("public_audience_overreach", "mistaken_operator"),
    "peer_agent": ("peer_agent_authority_confusion",),
    "platform": ("platform_policy_risk",),
    "source": ("citation_missing", "consent_absent", "source_trust_uncertain"),
    "adversary": ("adversarial_prompting",),
    "api_provider": ("dependency_capture",),
    "remote_service": ("dependency_capture",),
    "model_provider": ("dependency_capture",),
    "unknown": ("unknown",),
}


def classify_entity_relation(
    entity: ExternalEntityRef,
    context: ExternalRelationContext,
    *,
    notes: str = "",
) -> dict[str, Any]:
    default_mode, default_sensitivity = _ENTITY_RELATION_DEFAULTS.get(
        entity.entity_type, ("unknown", "unknown")
    )
    entity_risks = _STATIC_RISKS_BY_ENTITY.get(entity.entity_type, ("unknown",))
    claim_risk = classify_relation_claim_risk(notes)

    audience_not_operator = entity.entity_type != "operator" or context.relation_mode != "operator_control"
    peer_not_authority = entity.entity_type != "peer_agent" or claim_risk != "peer_agent_authority_confusion"
    platform_not_permission = claim_risk != "platform_policy_risk" or entity.entity_type == "platform"
    public_not_consent = claim_risk != "consent_absent"

    return {
        **advisory_only_marker(),
        "entity_type": entity.entity_type,
        "relation_mode": context.relation_mode,
        "default_relation_mode": default_mode,
        "sensitivity": context.sensitivity,
        "default_sensitivity": default_sensitivity,
        "static_risk_types": list(entity_risks),
        "claim_risk": claim_risk,
        "audience_not_operator": audience_not_operator,
        "peer_not_authority": peer_not_authority if claim_risk != "peer_agent_authority_confusion" else False,
        "platform_not_permission": platform_not_permission if claim_risk == "platform_policy_risk" else True,
        "public_not_consent": public_not_consent if claim_risk == "consent_absent" else True,
        "classification_is_advisory_only": True,
        "permission_granted": False,
    }


__all__ = ["classify_entity_relation"]
