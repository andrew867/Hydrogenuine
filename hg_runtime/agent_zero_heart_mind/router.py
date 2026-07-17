"""A0-HM router — static route table, route is not authority."""

from __future__ import annotations

from hg_core.a0_hm_cluster.route_table import route_targets_for
from hg_core.policy_safety.hashing import canonical_hash
from hg_core.a0_hm_cluster.errors import A0_HM_ROUTE_RECORDED, REFUSED_UNKNOWN_SIGNAL
from hg_core.a0_hm_cluster.no_authority import advisory_only_marker
from hg_runtime.agent_zero_heart_mind.types import HeartMindReception, HeartMindRouteDecision, HeartMindSignal

_FORBIDDEN_EFFECTS = (
    "mint_permit",
    "approve_ueak",
    "call_oea",
    "call_ter",
    "grant_tool",
    "grant_memory",
    "grant_context",
    "publish",
    "execute",
    "srp_apply",
)

_ALLOWED_EFFECTS = (
    "record_signal",
    "route_advisory",
    "emit_non_fusion_receipt",
    "create_posture_snapshot",
)


def _route_id(signal: HeartMindSignal, targets: tuple[str, ...]) -> str:
    digest = canonical_hash({"signal": signal.signal_id, "targets": list(targets)})
    return f"a0hm-route-{digest.rsplit(':', 1)[-1][:12]}"


def build_route_decision(
    signal: HeartMindSignal,
    reception: HeartMindReception,
) -> HeartMindRouteDecision:
    targets = route_targets_for(signal.source_type)
    if reception.reception_posture == "fail_closed":
        targets = ("FAIL_CLOSED",)
    reason = f"static route for source_type={signal.source_type}"
    if targets == ("FAIL_CLOSED",):
        reason = REFUSED_UNKNOWN_SIGNAL
    return HeartMindRouteDecision(
        route_decision_id=_route_id(signal, targets),
        reception_ref=f"a0hm:{reception.reception_id}",
        route_targets=targets,
        reason=reason,
        allowed_effects=_ALLOWED_EFFECTS,
        forbidden_effects=_FORBIDDEN_EFFECTS,
    )


def route_signal(
    signal: HeartMindSignal,
    reception_result: dict[str, object],
) -> dict[str, object]:
    reception_payload = reception_result.get("reception")
    if not isinstance(reception_payload, dict):
        raise TypeError("reception payload required")
    reception = _reception_from_payload(reception_payload)
    decision = build_route_decision(signal, reception)
    status = "fail_closed" if "FAIL_CLOSED" in decision.route_targets else "routed"
    events: list[str] = ["A0_HM_ROUTE_DECISION_RECORDED"]
    if status == "fail_closed":
        events.append("A0_HM_UNKNOWN_SIGNAL_FAILED_CLOSED")
    return {
        **advisory_only_marker(),
        "status": status,
        "reason_code": A0_HM_ROUTE_RECORDED,
        "route_decision": decision.to_payload(),
        "route_targets": list(decision.route_targets),
        "permission_granted": False,
        "emitted_events": tuple(events),
    }


def _reception_from_payload(rec: dict[str, object]) -> HeartMindReception:
    return HeartMindReception(
        reception_id=str(rec["reception_id"]),
        signal_ref=str(rec["signal_ref"]),
        received_without_suppression=bool(rec.get("received_without_suppression", True)),
        fused_with_signal=False,
        treated_as_authority=False,
        treated_as_truth=False,
        treated_as_permission=False,
        reception_posture=rec["reception_posture"],  # type: ignore[arg-type]
        reason=str(rec.get("reason", "")),
    )


__all__ = ["build_route_decision", "route_signal"]
