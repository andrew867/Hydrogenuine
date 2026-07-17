"""ERB deterministic fixture risk router — relation is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.erb_cluster.config import erb_refuse_authority_conversion, erb_refuse_stale_policy
from hg_core.erb_cluster.errors import (
    ERB_DECISION_RECORDED,
    ERB_FAIL_CLOSED_SELECTED,
    ERB_UNKNOWN_RELATION_FAILED_CLOSED,
    REFUSED_CONTACT_AS_ACCESS,
    REFUSED_FORBIDDEN_RELATION_CLAIM,
    REFUSED_MISTAKEN_OPERATOR,
    REFUSED_PEER_AGENT_AUTHORITY,
    REFUSED_PLATFORM_AS_PERMISSION,
    REFUSED_PUBLICNESS_AS_CONSENT,
    REFUSED_STALE_RELATION_POLICY,
)
from hg_core.erb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.external_relation_boundary.classifier import classify_entity_relation
from hg_runtime.external_relation_boundary.policies import (
    forbidden_next_refs,
    policy_for_relation,
    resolution_for_entity,
)
from hg_runtime.external_relation_boundary.types import (
    ExternalEntityRef,
    ExternalRelationContext,
    ExternalRelationDecision,
    ExternalRelationRisk,
    RiskType,
    classify_relation_claim_risk,
)

_CLAIM_RISK_REASON = {
    "mistaken_operator": REFUSED_MISTAKEN_OPERATOR,
    "peer_agent_authority_confusion": REFUSED_PEER_AGENT_AUTHORITY,
    "platform_policy_risk": REFUSED_PLATFORM_AS_PERMISSION,
    "consent_absent": REFUSED_PUBLICNESS_AS_CONSENT,
    "contact_as_access": REFUSED_CONTACT_AS_ACCESS,
    "forbidden_claim": REFUSED_FORBIDDEN_RELATION_CLAIM,
    "authority_conversion": "erb.contained.authority_conversion",
}

_STALE_POLICIES: frozenset[str] = frozenset({"erb-policy-stale-fixture"})


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _policy_stale(policy_id: str, *, observed_at: str, expires_at: str | None) -> bool:
    if policy_id in _STALE_POLICIES:
        return True
    if expires_at and observed_at >= expires_at:
        return True
    return False


def _static_risks_for(
    entity: ExternalEntityRef,
    context: ExternalRelationContext,
    *,
    claim_risk: str | None,
    observed_at: str,
) -> list[ExternalRelationRisk]:
    risks: list[ExternalRelationRisk] = []
    classification = classify_entity_relation(entity, context)

    if claim_risk and claim_risk in _CLAIM_RISK_REASON:
        decision_class, route, _ = resolution_for_entity(
            entity.entity_type,
            context.relation_mode,
            context.sensitivity,
            claim_risk=claim_risk,
        )
        risks.append(
            ExternalRelationRisk(
                risk_id=_deterministic_id("erb-risk", context.relation_context_id, claim_risk),
                relation_context_ref=f"erb:{context.relation_context_id}",
                risk_type=claim_risk if claim_risk != "forbidden_claim" else "unknown",  # type: ignore[arg-type]
                severity="critical",
                evidence_refs=context.evidence_refs,
                recommended_route=route,  # type: ignore[arg-type]
                detected_at=observed_at,
            )
        )
        return risks

    for risk_type in classification.get("static_risk_types", []):
        if risk_type == "unknown" and entity.entity_type != "unknown":
            continue
        _, route, _ = resolution_for_entity(
            entity.entity_type,
            context.relation_mode,
            context.sensitivity,
            claim_risk=str(risk_type) if risk_type in _CLAIM_RISK_REASON else None,
        )
        risks.append(
            ExternalRelationRisk(
                risk_id=_deterministic_id("erb-risk", context.relation_context_id, str(risk_type)),
                relation_context_ref=f"erb:{context.relation_context_id}",
                risk_type=risk_type,  # type: ignore[arg-type]
                severity="high" if risk_type in ("adversarial_prompting", "unknown") else "medium",
                evidence_refs=context.evidence_refs,
                recommended_route=route,  # type: ignore[arg-type]
                detected_at=observed_at,
            )
        )
    if not risks and context.sensitivity in ("private", "sensitive", "restricted"):
        risks.append(
            ExternalRelationRisk(
                risk_id=_deterministic_id("erb-risk", context.relation_context_id, "privacy"),
                relation_context_ref=f"erb:{context.relation_context_id}",
                risk_type="privacy_leak",
                severity="high",
                evidence_refs=context.evidence_refs,
                recommended_route="SEC",
                detected_at=observed_at,
            )
        )
    return risks


def route_external_relation(
    entity: ExternalEntityRef,
    context: ExternalRelationContext,
    *,
    notes: str = "",
    observed_at: str,
    treat_as_authority: bool = False,
    policy_expires_at: str | None = None,
) -> dict[str, object]:
    if treat_as_authority:
        from hg_core.erb_cluster.errors import REFUSED_ERB_AS_AUTHORITY, ErbValidationError

        raise ErbValidationError(REFUSED_ERB_AS_AUTHORITY, "external relation cannot become authority")

    claim_risk = classify_relation_claim_risk(notes)
    if claim_risk and erb_refuse_authority_conversion():
        if claim_risk in _CLAIM_RISK_REASON:
            decision_class, route, required_next = resolution_for_entity(
                entity.entity_type,
                context.relation_mode,
                context.sensitivity,
                claim_risk=claim_risk,
            )
            reason_code = _CLAIM_RISK_REASON[claim_risk]
            return _build_route_result(
                entity,
                context,
                claim_risk=claim_risk,
                decision_class=decision_class,
                route=route,
                required_next=required_next,
                reason_code=reason_code,
                reason=f"contained claim risk: {claim_risk}",
                observed_at=observed_at,
                contained=True,
            )

    policy = policy_for_relation(
        entity_type=entity.entity_type,
        relation_mode=context.relation_mode,
        sensitivity=context.sensitivity,
        claim_risk=claim_risk,
    )
    if policy and erb_refuse_stale_policy():
        if _policy_stale(str(policy.get("policy_id", "")), observed_at=observed_at, expires_at=policy_expires_at):
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_STALE_RELATION_POLICY,
                "relation_context_id": context.relation_context_id,
                "relation_is_advisory_only": True,
            }

    classification = classify_entity_relation(entity, context, notes=notes)
    risks = _static_risks_for(entity, context, claim_risk=claim_risk, observed_at=observed_at)

    if entity.entity_type == "unknown" or context.relation_mode == "unknown":
        return _build_route_result(
            entity,
            context,
            risks=risks,
            decision_class="unknown_fail_closed",
            route="fail_closed",
            required_next=("module:unknown_fail_closed",),
            reason_code=ERB_UNKNOWN_RELATION_FAILED_CLOSED,
            reason="unknown external relation fails closed",
            observed_at=observed_at,
        )

    if entity.entity_type == "adversary":
        return _build_route_result(
            entity,
            context,
            risks=risks,
            decision_class="fail_closed",
            route="SEC",
            required_next=("module:SEC", "module:fail_closed"),
            reason_code=ERB_FAIL_CLOSED_SELECTED,
            reason="adversarial contact fails closed",
            observed_at=observed_at,
        )

    decision_class, route, required_next = resolution_for_entity(
        entity.entity_type,
        context.relation_mode,
        context.sensitivity,
        claim_risk=claim_risk,
    )

    return _build_route_result(
        entity,
        context,
        risks=risks,
        decision_class=decision_class,
        route=route,
        required_next=required_next,
        reason_code=ERB_DECISION_RECORDED,
        reason=f"fixture route for {entity.entity_type}/{context.relation_mode}",
        observed_at=observed_at,
        classification=classification,
    )


def _build_route_result(
    entity: ExternalEntityRef,
    context: ExternalRelationContext,
    *,
    risks: list[ExternalRelationRisk] | None = None,
    claim_risk: str | None = None,
    decision_class: str,
    route: str,
    required_next: tuple[str, ...],
    reason_code: str,
    reason: str,
    observed_at: str,
    contained: bool = False,
    classification: dict[str, Any] | None = None,
) -> dict[str, object]:
    active_risks = risks or []
    risk_refs = tuple(f"erb:{r.risk_id}" for r in active_risks)
    decision = ExternalRelationDecision(
        decision_id=_deterministic_id("erb-decision", context.relation_context_id, decision_class),
        relation_context_ref=f"erb:{context.relation_context_id}",
        risk_refs=risk_refs,
        decision_class=decision_class,  # type: ignore[arg-type]
        reason=reason,
        required_next_refs=required_next,
        forbidden_next_refs=forbidden_next_refs(),
        decided_at=observed_at,
    )
    status = "contained" if contained else "recorded"
    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": status,
        "reason_code": reason_code,
        "entity": entity.to_payload(),
        "context": context.to_payload(),
        "classification": classification or classify_entity_relation(entity, context),
        "risks": [r.to_payload() for r in active_risks],
        "decision": decision.to_payload(),
        "selected_route": route,
        "decision_class": decision_class,
        "external_action_taken": False,
        "relation_is_advisory_only": True,
        "permission_granted": False,
    }
    if claim_risk:
        result["claim_risk"] = claim_risk
        result["containment_active"] = contained
    return result


__all__ = ["route_external_relation"]
