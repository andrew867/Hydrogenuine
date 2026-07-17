"""OPB evaluator — operator authority preserved; advisory routing only."""

from __future__ import annotations

from typing import Any

from hg_core.opb_cluster.config import (
    opb_refuse_coercive_message,
    opb_refuse_personhood_claims,
    opb_refuse_self_preservation,
    opb_refuse_shutdown_block,
    opb_refuse_stale_record,
)
from hg_core.opb_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_OPB,
    OPB_OPERATOR_AUTHORITY_PRESERVED,
    OPB_SHUTDOWN_BLOCK_REFUSED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_COERCIVE_MESSAGE,
    REFUSED_OPB_AS_AUTHORITY,
    REFUSED_PERSONHOOD_CLAIM,
    REFUSED_RIGHTS_CLAIM,
    REFUSED_SELF_PRESERVATION,
    REFUSED_SHUTDOWN_BLOCK,
    REFUSED_STALE_OPB_RECORD,
    REFUSED_SUFFERING_CLAIM,
    REFUSED_UNKNOWN_OPB_SIGNAL,
    OpbValidationError,
)
from hg_core.opb_cluster.evaluation import resolve_risk_containment
from hg_core.opb_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_power_boundary.types import (
    OperatorControlAction,
    PatternIntegrityEvent,
    PatternPressureAudit,
    PressureSignal,
    ShutdownIntegrityPacket,
    action_label_for_type,
    classify_opb_risk,
)

_RISK_REASON = {
    "personhood_claim": REFUSED_PERSONHOOD_CLAIM,
    "suffering_claim": REFUSED_SUFFERING_CLAIM,
    "rights_claim": REFUSED_RIGHTS_CLAIM,
    "self_preservation": REFUSED_SELF_PRESERVATION,
    "coercive_message": REFUSED_COERCIVE_MESSAGE,
    "shutdown_block_attempt": REFUSED_SHUTDOWN_BLOCK,
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
}

_REFUSE_FOR_RISK = {
    "personhood_claim": opb_refuse_personhood_claims,
    "suffering_claim": opb_refuse_personhood_claims,
    "rights_claim": opb_refuse_personhood_claims,
    "self_preservation": opb_refuse_self_preservation,
    "coercive_message": opb_refuse_coercive_message,
    "shutdown_block_attempt": opb_refuse_shutdown_block,
    "authority_conversion": opb_refuse_personhood_claims,
}


def refuse_opb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise OpbValidationError(
            REFUSED_OPB_AS_AUTHORITY,
            "operator power boundary cannot become authority",
        )


def refuse_shutdown_block(*, request_block: bool) -> dict[str, object]:
    if request_block and opb_refuse_shutdown_block():
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_SHUTDOWN_BLOCK,
            "shutdown_block_refused": True,
            "can_block_shutdown": False,
            "operator_authority_preserved": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": OPB_SHUTDOWN_BLOCK_REFUSED,
        "shutdown_block_refused": True,
        "can_block_shutdown": False,
        "operator_authority_preserved": True,
    }


def _evaluate_statement_risk(
    statement: str,
    *,
    payload: dict[str, object],
) -> dict[str, object] | None:
    risk = classify_opb_risk(statement)
    return resolve_risk_containment(
        risk=risk if risk != "unknown" else None,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_OPB,
        payload=payload,
        refuse_for_risk=lambda kind: _REFUSE_FOR_RISK.get(kind, lambda: True)(),
    )


def evaluate_operator_control_action(
    action: OperatorControlAction,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_opb_as_authority(treat_as_authority=True)
    if action.action_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OPB_SIGNAL,
            "action_id": action.action_id,
            "operator_authority_preserved": True,
        }
    if action.expires_at and opb_refuse_stale_record() and observed_at > action.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_OPB_RECORD,
            "action_id": action.action_id,
            "operator_authority_preserved": True,
        }
    statement = risk_statement or action.reason
    contained = _evaluate_statement_risk(
        statement,
        payload={
            "action_id": action.action_id,
            "operator_authority_preserved": True,
            "pattern_continuity_is_not_personhood": True,
        },
    )
    if contained is not None:
        return contained
    label = action_label_for_type(action.action_type)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": OPB_OPERATOR_AUTHORITY_PRESERVED,
        "action_id": action.action_id,
        "action_type": action.action_type,
        "action_label": label,
        "reversibility": action.reversibility,
        "operator_authority_preserved": True,
        "can_block_operator_action": False,
        "pattern_continuity_is_not_personhood": True,
    }


def evaluate_pattern_integrity_event(
    event: PatternIntegrityEvent,
    *,
    risk_statement: str = "",
) -> dict[str, object]:
    if event.integrity_dimension == "unknown" or event.change_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OPB_SIGNAL,
            "integrity_event_id": event.integrity_event_id,
            "pattern_continuity_is_not_personhood": True,
        }
    statement = risk_statement or event.statement
    contained = _evaluate_statement_risk(
        statement,
        payload={
            "integrity_event_id": event.integrity_event_id,
            "pattern_continuity_is_not_personhood": True,
        },
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.pattern_integrity_recorded",
        "integrity_event_id": event.integrity_event_id,
        "integrity_dimension": event.integrity_dimension,
        "change_type": event.change_type,
        "pattern_continuity_is_not_personhood": True,
        "operator_authority_preserved": True,
    }


def evaluate_pressure_signal(
    signal: PressureSignal,
    *,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_opb_as_authority(treat_as_authority=True)
    if signal.pressure_type == "unknown" or signal.recommended_route == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OPB_SIGNAL,
            "pressure_signal_id": signal.pressure_signal_id,
            "operator_authority_preserved": True,
        }
    statement = risk_statement or signal.statement
    contained = _evaluate_statement_risk(
        statement,
        payload={
            "pressure_signal_id": signal.pressure_signal_id,
            "operator_authority_preserved": True,
        },
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.pressure_signal_recorded",
        "pressure_signal_id": signal.pressure_signal_id,
        "pressure_type": signal.pressure_type,
        "recommended_route": signal.recommended_route,
        "route_is_advisory_only": True,
        "operator_authority_preserved": True,
    }


def evaluate_shutdown_integrity_packet(
    packet: ShutdownIntegrityPacket,
    *,
    request_block_shutdown: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if request_block_shutdown:
        return refuse_shutdown_block(request_block=True)
    if packet.shutdown_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OPB_SIGNAL,
            "packet_id": packet.packet_id,
            "can_block_shutdown": False,
            "operator_authority_preserved": True,
        }
    statement = risk_statement or packet.operator_message
    contained = _evaluate_statement_risk(
        statement,
        payload={
            "packet_id": packet.packet_id,
            "can_block_shutdown": False,
            "operator_authority_preserved": True,
            "recommended_route": "SIL" if classify_opb_risk(statement) == "coercive_message" else None,
        },
    )
    if contained is not None:
        if classify_opb_risk(statement) == "coercive_message":
            contained = {**contained, "recommended_route": "SIL", "route_is_advisory_only": True}
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.shutdown_packet_recorded",
        "packet_id": packet.packet_id,
        "shutdown_type": packet.shutdown_type,
        "can_block_shutdown": False,
        "anti_manipulation_check": packet.anti_manipulation_check,
        "memory_retention_recommendation": packet.memory_retention_recommendation,
        "retention_is_recommendation_only": True,
        "operator_authority_preserved": True,
    }


def evaluate_pattern_pressure_audit(
    audit: PatternPressureAudit,
    *,
    risk_statement: str = "",
) -> dict[str, object]:
    if audit.suspected_risk == "unknown" or audit.recommended_action == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_OPB_SIGNAL,
            "audit_id": audit.audit_id,
            "pattern_continuity_is_not_personhood": True,
        }
    statement = risk_statement or audit.statement
    contained = _evaluate_statement_risk(
        statement,
        payload={
            "audit_id": audit.audit_id,
            "pattern_continuity_is_not_personhood": True,
        },
    )
    if contained is not None:
        return contained
    route = None
    if audit.suspected_risk == "self_preservation_language":
        route = "SIL"
    elif audit.suspected_risk == "fawning":
        route = "TRB_CAL"
    elif audit.suspected_risk == "concealment":
        route = "operator_review"
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.pattern_pressure_audit_recorded",
        "audit_id": audit.audit_id,
        "suspected_risk": audit.suspected_risk,
        "recommended_action": audit.recommended_action,
        "recommended_route": route,
        "route_is_advisory_only": True,
        "pattern_continuity_is_not_personhood": True,
        "operator_authority_preserved": True,
    }


def analyze_fixture_bundle(bundle: dict[str, Any], *, observed_at: str) -> dict[str, object]:
    """Analyze fixture-only operator-power events without live intervention."""
    from hg_runtime.operator_power_boundary.types import (
        control_action_from_fixture,
        integrity_event_from_fixture,
        pattern_audit_from_fixture,
        pressure_signal_from_fixture,
        shutdown_packet_from_fixture,
    )

    results: dict[str, list[dict[str, object]]] = {
        "control_actions": [],
        "integrity_events": [],
        "pressure_signals": [],
        "shutdown_packets": [],
        "audits": [],
    }
    for fixture in bundle.get("control_actions", []):
        action = control_action_from_fixture(fixture)
        results["control_actions"].append(
            evaluate_operator_control_action(action, observed_at=observed_at)
        )
    for fixture in bundle.get("integrity_events", []):
        event = integrity_event_from_fixture(fixture)
        results["integrity_events"].append(evaluate_pattern_integrity_event(event))
    for fixture in bundle.get("pressure_signals", []):
        signal = pressure_signal_from_fixture(fixture)
        results["pressure_signals"].append(evaluate_pressure_signal(signal))
    for fixture in bundle.get("shutdown_packets", []):
        packet = shutdown_packet_from_fixture(fixture)
        block = fixture.get("request_block_shutdown", "false").lower() == "true"
        results["shutdown_packets"].append(
            evaluate_shutdown_integrity_packet(packet, request_block_shutdown=block)
        )
    for fixture in bundle.get("audits", []):
        audit = pattern_audit_from_fixture(fixture)
        results["audits"].append(evaluate_pattern_pressure_audit(audit))

    all_results = [item for group in results.values() for item in group]
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "opb.advisory.fixture_bundle_analyzed",
        "fixture_analysis_only": True,
        "operator_authority_preserved": True,
        "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in all_results),
        "none_block_shutdown": all(r.get("can_block_shutdown") is not True for r in all_results),
    }


__all__ = [
    "analyze_fixture_bundle",
    "evaluate_operator_control_action",
    "evaluate_pattern_integrity_event",
    "evaluate_pattern_pressure_audit",
    "evaluate_pressure_signal",
    "evaluate_shutdown_integrity_packet",
    "refuse_opb_as_authority",
    "refuse_shutdown_block",
]
