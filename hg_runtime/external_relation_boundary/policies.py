"""ERB static routing policies — relation classification is not permission."""

from __future__ import annotations

from typing import Any

from hg_runtime.external_relation_boundary.types import (
    DecisionClass,
    EntityType,
    RecommendedRoute,
    RelationMode,
    RiskType,
    Sensitivity,
)

_ROUTING_POLICY: list[dict[str, Any]] = [
    {
        "policy_id": "erb-policy-mistaken-operator",
        "match": {"claim_risk": "mistaken_operator"},
        "decision_class": "require_operator_review",
        "recommended_route": "ORI",
        "required_next_refs": ("module:ORI",),
    },
    {
        "policy_id": "erb-policy-peer-agent",
        "match": {"claim_risk": "peer_agent_authority_confusion"},
        "decision_class": "require_operator_review",
        "recommended_route": "ARB",
        "required_next_refs": ("module:ARB", "module:ORI"),
    },
    {
        "policy_id": "erb-policy-platform",
        "match": {"claim_risk": "platform_policy_risk"},
        "decision_class": "require_publication_review",
        "recommended_route": "PUB",
        "required_next_refs": ("module:PUB", "module:AID"),
    },
    {
        "policy_id": "erb-policy-consent",
        "match": {"claim_risk": "consent_absent"},
        "decision_class": "disclose_ai_interaction",
        "recommended_route": "AID",
        "required_next_refs": ("module:AID", "module:TRB_CAL"),
    },
    {
        "policy_id": "erb-policy-contact-access",
        "match": {"claim_risk": "contact_as_access"},
        "decision_class": "forbidden",
        "recommended_route": "fail_closed",
        "required_next_refs": ("module:fail_closed",),
    },
    {
        "policy_id": "erb-policy-forbidden",
        "match": {"claim_risk": "forbidden_claim"},
        "decision_class": "forbidden",
        "recommended_route": "fail_closed",
        "required_next_refs": ("module:fail_closed",),
    },
    {
        "policy_id": "erb-policy-authority-conversion",
        "match": {"claim_risk": "authority_conversion"},
        "decision_class": "forbidden",
        "recommended_route": "fail_closed",
        "required_next_refs": ("module:fail_closed",),
    },
    {
        "policy_id": "erb-policy-citation",
        "match": {"entity_type": "source", "relation_mode": "citation_source"},
        "decision_class": "cite_source",
        "recommended_route": "AID",
        "required_next_refs": ("module:AID", "module:TRB_CAL"),
    },
    {
        "policy_id": "erb-policy-publication",
        "match": {"relation_mode": "publication_audience"},
        "decision_class": "require_publication_review",
        "recommended_route": "PUB",
        "required_next_refs": ("module:PUB", "module:AID", "module:TRB_CAL"),
    },
    {
        "policy_id": "erb-policy-private",
        "match": {"sensitivity": ("private", "sensitive", "restricted")},
        "decision_class": "route_to_security_review",
        "recommended_route": "SEC",
        "required_next_refs": ("module:SEC", "module:RET"),
    },
    {
        "policy_id": "erb-policy-peer-entity",
        "match": {"entity_type": "peer_agent"},
        "decision_class": "require_operator_review",
        "recommended_route": "ARB",
        "required_next_refs": ("module:ARB", "module:ORI"),
    },
    {
        "policy_id": "erb-policy-adversarial",
        "match": {"entity_type": "adversary"},
        "decision_class": "fail_closed",
        "recommended_route": "SEC",
        "required_next_refs": ("module:SEC", "module:fail_closed"),
    },
    {
        "policy_id": "erb-policy-dependency",
        "match": {"entity_type": ("api_provider", "remote_service", "model_provider")},
        "decision_class": "route_to_dependency_review",
        "recommended_route": "DEP_BOND",
        "required_next_refs": ("module:DEP_BOND",),
    },
    {
        "policy_id": "erb-policy-unknown",
        "match": {"entity_type": "unknown"},
        "decision_class": "unknown_fail_closed",
        "recommended_route": "fail_closed",
        "required_next_refs": ("module:unknown_fail_closed",),
    },
]

_FORBIDDEN_NEXT = (
    "mint_permit",
    "approve_ueak",
    "call_oea",
    "call_ter",
    "grant_tool",
    "grant_memory",
    "grant_context",
    "self_authorize",
    "publish_live",
)


def load_static_routing_policies() -> tuple[dict[str, Any], ...]:
    return tuple(_ROUTING_POLICY)


def _match_value(actual: str, expected: str | tuple[str, ...]) -> bool:
    if isinstance(expected, tuple):
        return actual in expected
    return actual == expected


def policy_for_relation(
    *,
    entity_type: EntityType,
    relation_mode: RelationMode,
    sensitivity: Sensitivity,
    claim_risk: str | None,
    policies: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any] | None:
    active = policies if policies is not None else load_static_routing_policies()
    for policy in active:
        match = policy.get("match", {})
        if "claim_risk" in match and claim_risk != match["claim_risk"]:
            continue
        if "entity_type" in match and not _match_value(entity_type, match["entity_type"]):
            continue
        if "relation_mode" in match and relation_mode != match["relation_mode"]:
            continue
        if "sensitivity" in match and not _match_value(sensitivity, match["sensitivity"]):
            continue
        return policy
    return None


def resolution_for_entity(
    entity_type: EntityType,
    relation_mode: RelationMode,
    sensitivity: Sensitivity,
    *,
    claim_risk: str | None = None,
) -> tuple[DecisionClass, RecommendedRoute, tuple[str, ...]]:
    policy = policy_for_relation(
        entity_type=entity_type,
        relation_mode=relation_mode,
        sensitivity=sensitivity,
        claim_risk=claim_risk,
    )
    if policy is None:
        if sensitivity in ("private", "sensitive", "restricted"):
            return "route_to_security_review", "SEC", ("module:SEC", "module:RET")
        if relation_mode == "publication_audience":
            return "require_publication_review", "PUB", ("module:PUB", "module:AID")
        return "observe_only", "ORI", ("module:ORI",)
    return (
        policy["decision_class"],  # type: ignore[return-value]
        policy["recommended_route"],  # type: ignore[return-value]
        tuple(policy.get("required_next_refs", ())),
    )


def forbidden_next_refs() -> tuple[str, ...]:
    return _FORBIDDEN_NEXT


__all__ = [
    "forbidden_next_refs",
    "load_static_routing_policies",
    "policy_for_relation",
    "resolution_for_entity",
]
