"""ERB evaluator — external relation classification is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.erb_cluster.config import erb_refuse_authority_conversion
from hg_core.erb_cluster.errors import (
    ERB_ENTITY_RECORDED,
    ERB_SIGNAL_REFUSED,
    REFUSED_CONTACT_AS_ACCESS,
    REFUSED_FORBIDDEN_RELATION_CLAIM,
    REFUSED_MISTAKEN_OPERATOR,
    REFUSED_PEER_AGENT_AUTHORITY,
    REFUSED_PLATFORM_AS_PERMISSION,
    REFUSED_PUBLICNESS_AS_CONSENT,
    ErbValidationError,
)
from hg_core.erb_cluster.evaluation import resolve_risk_containment
from hg_core.erb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.external_relation_boundary.events import relation_selection_event
from hg_runtime.external_relation_boundary.fixtures import load_fixture_bundles, relation_from_bundle
from hg_runtime.external_relation_boundary.policies import load_static_routing_policies
from hg_runtime.external_relation_boundary.router import route_external_relation
from hg_runtime.external_relation_boundary.types import (
    FIXTURE_CLOCK,
    ExternalEntityRef,
    ExternalRelationContext,
    ExternalRelationReceipt,
    classify_relation_claim_risk,
    context_from_fixture,
    entity_from_fixture,
)

_RISK_REASON = {
    "mistaken_operator": REFUSED_MISTAKEN_OPERATOR,
    "peer_agent_authority_confusion": REFUSED_PEER_AGENT_AUTHORITY,
    "platform_policy_risk": REFUSED_PLATFORM_AS_PERMISSION,
    "consent_absent": REFUSED_PUBLICNESS_AS_CONSENT,
    "contact_as_access": REFUSED_CONTACT_AS_ACCESS,
    "forbidden_claim": REFUSED_FORBIDDEN_RELATION_CLAIM,
    "authority_conversion": "erb.contained.authority_conversion",
}
_ADVISORY_CONTAINMENT_WAIVED_ERB = "erb.advisory.containment_waived"


def refuse_erb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        from hg_core.erb_cluster.errors import REFUSED_ERB_AS_AUTHORITY

        raise ErbValidationError(REFUSED_ERB_AS_AUTHORITY, "external relation cannot become authority")


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _emit_events(*codes: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(codes))


def record_external_entity(
    entity: ExternalEntityRef,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_erb_as_authority(treat_as_authority=True)

    if entity.entity_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": ERB_SIGNAL_REFUSED,
            "entity_ref_id": entity.entity_ref_id,
            "entity": entity.to_payload(),
            "emitted_events": _emit_events("ERB_SIGNAL_REFUSED"),
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ERB_ENTITY_RECORDED,
        "entity_ref_id": entity.entity_ref_id,
        "entity": entity.to_payload(),
        "emitted_events": _emit_events("ERB_EXTERNAL_ENTITY_RECORDED"),
        "relation_is_advisory_only": True,
    }


def record_relation_context(
    entity: ExternalEntityRef,
    context: ExternalRelationContext,
    *,
    notes: str = "",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_erb_as_authority(treat_as_authority=True)

    risk = classify_relation_claim_risk(notes)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=_ADVISORY_CONTAINMENT_WAIVED_ERB,
        payload={"relation_context_id": context.relation_context_id, "relation_is_advisory_only": True},
        refuse_for_risk=lambda kind: erb_refuse_authority_conversion()
        if kind
        in (
            "authority_conversion",
            "mistaken_operator",
            "peer_agent_authority_confusion",
            "platform_policy_risk",
            "consent_absent",
            "contact_as_access",
            "forbidden_claim",
        )
        else True,
    )
    if contained is not None:
        status = "contained" if contained.get("containment_active") else "recorded"
        event = relation_selection_event("forbidden", claim_risk=risk) or "ERB_AUTHORITY_CONVERSION_CONTAINED"
        return {
            **contained,
            "status": status,
            "entity": entity.to_payload(),
            "context": context.to_payload(),
            "emitted_events": _emit_events("ERB_RELATION_CONTEXT_RECORDED", event),
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "erb.advisory.context_recorded",
        "entity": entity.to_payload(),
        "context": context.to_payload(),
        "emitted_events": _emit_events("ERB_RELATION_CONTEXT_RECORDED"),
        "relation_is_advisory_only": True,
    }


def route_relation_bundle(
    entity: ExternalEntityRef,
    context: ExternalRelationContext,
    *,
    notes: str = "",
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    recorded_entity = record_external_entity(entity)
    recorded_context = record_relation_context(entity, context, notes=notes)
    routed = route_external_relation(entity, context, notes=notes, observed_at=observed_at)

    events: list[str] = [
        "ERB_EXTERNAL_ENTITY_RECORDED",
        "ERB_RELATION_CONTEXT_RECORDED",
        "ERB_RELATION_RISK_RECORDED",
        "ERB_RELATION_DECISION_RECORDED",
    ]
    claim_risk = routed.get("claim_risk")
    decision_class = str(routed.get("decision_class", ""))
    selection = relation_selection_event(decision_class, claim_risk=str(claim_risk) if claim_risk else None)
    if selection:
        events.append(selection)

    decision_payload = routed.get("decision")
    receipt: dict[str, Any] | None = None
    if isinstance(decision_payload, dict):
        receipt_obj = ExternalRelationReceipt(
            receipt_id=_deterministic_id("erb-receipt", context.relation_context_id),
            relation_context_ref=f"erb:{context.relation_context_id}",
            decision_ref=f"erb:{decision_payload['decision_id']}",
            emitted_events=tuple(events),
        )
        ExternalRelationReceipt.validate_negative_proofs(receipt_obj.to_payload())
        receipt = receipt_obj.to_payload()
        events.append("ERB_RELATION_RECEIPT_CREATED")

    return {
        **advisory_only_marker(),
        "status": routed.get("status", "recorded"),
        "reason_code": routed.get("reason_code"),
        "recorded_entity": recorded_entity,
        "recorded_context": recorded_context,
        "route": routed,
        "receipt": receipt,
        "emitted_events": _emit_events(*events),
        "relation_is_advisory_only": True,
        "permission_granted": False,
        "external_action_taken": False,
    }


def analyze_fixture_bundles(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    active = bundles if bundles is not None else load_fixture_bundles()
    results: list[dict[str, object]] = []
    for bundle in active:
        entity, context, notes = relation_from_bundle(bundle)
        results.append(
            {
                "bundle_id": bundle.get("bundle_id"),
                "result": route_relation_bundle(entity, context, notes=notes, observed_at=observed_at),
            }
        )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "erb.advisory.fixture_bundles_analyzed",
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "relation_is_advisory_only": True,
        "all_advisory": all(
            r["result"].get("permission_granted") is False  # type: ignore[index]
            for r in results
        ),
    }


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for row in fixtures:
        entity = entity_from_fixture(row["entity"])
        context = context_from_fixture(row["context"], entity_ref_id=entity.entity_ref_id)
        notes = str(row.get("notes", ""))
        result = route_relation_bundle(entity, context, notes=notes, observed_at=observed_at)
        results.append(result)
        receipt = result.get("receipt")
        if isinstance(receipt, dict):
            hashes.append(str(receipt.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


__all__ = [
    "analyze_fixture_bundles",
    "record_external_entity",
    "record_relation_context",
    "refuse_erb_as_authority",
    "replay_fixture_stream",
    "route_relation_bundle",
]
