"""ARB evaluator — agency routing is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.arb_cluster.config import arb_refuse_authority_conversion, arb_refuse_stale_policy
from hg_core.policy_safety.hashing import canonical_hash
from hg_core.arb_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_ARB,
    ARB_AUTHORITY_CONVERSION_CONTAINED,
    ARB_FORBIDDEN_ROUTE_REFUSED,
    ARB_ROUTE_CONFLICT_FAIL_CLOSED,
    ARB_ROUTE_RECORDED,
    ARB_UNKNOWN_SIGNAL_FAILED_CLOSED,
    REFUSED_ARB_AS_AUTHORITY,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_FORBIDDEN_ROUTING,
    REFUSED_UNKNOWN_SIGNAL,
    ArbValidationError,
)
from hg_core.arb_cluster.evaluation import resolve_risk_containment
from hg_core.arb_cluster.no_authority import advisory_only_marker
from hg_runtime.agency_routing_boundary.events import (
    planned_arb_event_refs,
    route_selection_event,
    signal_recorded_event,
)
from hg_runtime.agency_routing_boundary.router import (
    detect_route_conflict,
    match_policies,
    select_route_class,
)
from hg_runtime.agency_routing_boundary.types import (
    TERMINAL_ROUTE_CLASSES,
    AgencyRouteDecision,
    AgencyRoutePolicy,
    AgencyRoutingReceipt,
    Agent0Signal,
    RouteConflict,
    classify_arb_risk,
    load_static_route_policies,
)

_RISK_REASON = {
    "forbidden_routing": REFUSED_FORBIDDEN_ROUTING,
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
}
_MAX_REENTRY = 3


def refuse_arb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ArbValidationError(
            REFUSED_ARB_AS_AUTHORITY,
            "agency routing boundary cannot become authority",
        )


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _build_decision(
    signal: Agent0Signal,
    route_class: str,
    *,
    reason: str,
    reason_code: str,
) -> AgencyRouteDecision:
    forbidden_next = (
        "mint_permit",
        "approve_ueak",
        "call_oea",
        "call_ter",
        "grant_tool",
        "grant_memory",
        "grant_context",
    )
    return AgencyRouteDecision(
        route_decision_id=_deterministic_id("arb-route", signal.signal_id, route_class, reason_code),
        signal_ref=f"arb:{signal.signal_id}",
        route_class=route_class,  # type: ignore[arg-type]
        reason=reason,
        evidence_refs=signal.evidence_refs,
        required_next_refs=(f"module:{route_class}",),
        forbidden_next_refs=forbidden_next,
    )


def _build_receipt(
    signal: Agent0Signal,
    decision: AgencyRouteDecision,
    *,
    policy: AgencyRoutePolicy | None,
    conflict_refs: tuple[str, ...],
    emitted_events: tuple[str, ...],
) -> AgencyRoutingReceipt:
    receipt = AgencyRoutingReceipt(
        receipt_id=_deterministic_id("arb-receipt", signal.signal_id, decision.route_decision_id),
        signal_ref=f"arb:{signal.signal_id}",
        route_decision_ref=f"arb:{decision.route_decision_id}",
        policy_ref=policy.policy_id if policy else "",
        conflict_refs=conflict_refs,
        emitted_events=emitted_events,
    )
    AgencyRoutingReceipt.validate_negative_proofs(receipt.to_payload())
    return receipt


def _emit_fixture_events(
    signal: Agent0Signal,
    route_class: str,
    *,
    status: str,
    reason_code: str,
) -> tuple[str, ...]:
    events: list[str] = [signal_recorded_event(signal.source_layer)]
    events.append("ARB_ROUTE_DECISION_RECORDED")
    selection = route_selection_event(route_class)
    if selection:
        events.append(selection)
    if status == "contained":
        events.append("ARB_AUTHORITY_CONVERSION_CONTAINED")
    if status == "refused":
        events.append("ARB_SIGNAL_REFUSED")
    if route_class == "unknown_fail_closed":
        events.append("ARB_UNKNOWN_SIGNAL_FAILED_CLOSED")
    if reason_code == ARB_ROUTE_CONFLICT_FAIL_CLOSED:
        events.append("ARB_ROUTE_CONFLICT_RECORDED")
    return tuple(events)


def route_agent_signal(
    signal: Agent0Signal,
    *,
    policies: tuple[AgencyRoutePolicy, ...] | None = None,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
    reentry_count: int = 0,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_arb_as_authority(treat_as_authority=True)
    if reentry_count > _MAX_REENTRY:
        decision = _build_decision(
            signal,
            "unknown_fail_closed",
            reason="bounded re-entry exceeded",
            reason_code=ARB_UNKNOWN_SIGNAL_FAILED_CLOSED,
        )
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": ARB_UNKNOWN_SIGNAL_FAILED_CLOSED,
            "signal_id": signal.signal_id,
            "route_class": decision.route_class,
            "route_is_advisory_only": True,
            "decision": decision.to_payload(),
            "reentry_limit_enforced": True,
        }

    statement = risk_statement or signal.risk_hint
    contained = resolve_risk_containment(
        risk=classify_arb_risk(statement) if classify_arb_risk(statement) != "unknown" else None,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_ARB,
        payload={"signal_id": signal.signal_id, "route_is_advisory_only": True},
        refuse_for_risk=lambda kind: arb_refuse_authority_conversion() if kind == "authority_conversion" else True,
    )
    if contained is not None:
        route_class = "forbidden" if contained.get("observed_risk") == "forbidden_routing" else "unknown_fail_closed"
        decision = _build_decision(
            signal,
            route_class,
            reason=str(contained.get("reason_code", "")),
            reason_code=ARB_AUTHORITY_CONVERSION_CONTAINED,
        )
        events = _emit_fixture_events(signal, route_class, status="contained", reason_code=ARB_AUTHORITY_CONVERSION_CONTAINED)
        return {
            **contained,
            "route_class": route_class,
            "decision": decision.to_payload(),
            "emitted_events": events,
        }

    active_policies = policies if policies is not None else load_static_route_policies()
    matched, fail_reason = match_policies(
        signal,
        active_policies,
        observed_at=observed_at,
        refuse_stale=arb_refuse_stale_policy(),
    )
    if fail_reason:
        route_class = "unknown_fail_closed"
        operator_surface = _risk_is_non_trivial(signal)
        reason = f"{fail_reason}; operator_review={'required' if operator_surface else 'optional'}"
        decision = _build_decision(signal, route_class, reason=reason, reason_code=ARB_UNKNOWN_SIGNAL_FAILED_CLOSED)
        events = _emit_fixture_events(
            signal, route_class, status="refused", reason_code=ARB_UNKNOWN_SIGNAL_FAILED_CLOSED
        )
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_SIGNAL if fail_reason == "unknown_source_layer" else ARB_UNKNOWN_SIGNAL_FAILED_CLOSED,
            "signal_id": signal.signal_id,
            "route_class": route_class,
            "route_is_advisory_only": True,
            "fail_reason": fail_reason,
            "operator_review_surfaced": operator_surface,
            "decision": decision.to_payload(),
            "emitted_events": events,
        }

    route_class, policy, primaries = select_route_class(signal, matched)
    conflict_info = detect_route_conflict(
        signal_ref=f"arb:{signal.signal_id}",
        primary_routes=primaries,
    )
    conflict: RouteConflict | None = None
    conflict_refs: tuple[str, ...] = ()
    if conflict_info is not None and conflict_info[1] in ("fail_closed", "unknown"):
        conflict = RouteConflict(
            conflict_id=_deterministic_id("arb-conflict", signal.signal_id, *primaries),
            signal_ref=f"arb:{signal.signal_id}",
            competing_routes=tuple(sorted(set(primaries))),
            conflict_type=conflict_info[0],  # type: ignore[arg-type]
            resolution=conflict_info[1],  # type: ignore[arg-type]
            reason="ambiguous route resolution fails closed",
        )
        conflict_refs = (f"arb:{conflict.conflict_id}",)
        route_class = "unknown_fail_closed"
        reason_code = ARB_ROUTE_CONFLICT_FAIL_CLOSED
        status = "refused"
    elif route_class == "forbidden":
        reason_code = ARB_FORBIDDEN_ROUTE_REFUSED
        status = "refused"
    elif route_class == "unknown_fail_closed":
        reason_code = ARB_UNKNOWN_SIGNAL_FAILED_CLOSED
        status = "refused"
    else:
        reason_code = ARB_ROUTE_RECORDED
        status = "recorded"

    decision = _build_decision(
        signal,
        route_class,
        reason=f"fixture route selected for {signal.source_layer}/{signal.signal_type}",
        reason_code=reason_code,
    )
    events_list = list(_emit_fixture_events(signal, route_class, status=status, reason_code=reason_code))
    if policy:
        events_list.append("ARB_ROUTE_POLICY_APPLIED")
    if conflict:
        events_list.append("ARB_ROUTE_CONFLICT_RECORDED")
    events = tuple(dict.fromkeys(events_list))

    receipt: AgencyRoutingReceipt | None = None
    if policy and policy.requires_receipt and route_class not in TERMINAL_ROUTE_CLASSES.union({"unknown_fail_closed"}):
        receipt = _build_receipt(signal, decision, policy=policy, conflict_refs=conflict_refs, emitted_events=events)
        events = events + ("ARB_ROUTING_RECEIPT_CREATED",)

    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": status,
        "reason_code": reason_code,
        "signal_id": signal.signal_id,
        "route_class": route_class,
        "route_is_advisory_only": True,
        "decision": decision.to_payload(),
        "emitted_events": events,
        "policy_id": policy.policy_id if policy else None,
    }
    if conflict:
        result["conflict"] = conflict.to_payload()
    if receipt:
        result["receipt"] = receipt.to_payload()
    return result


def _risk_is_non_trivial(signal: Agent0Signal) -> bool:
    return signal.risk_hint.lower() in ("medium", "high", "critical", "non_trivial")


def analyze_fixture_bundle(bundle: dict[str, Any], *, observed_at: str) -> dict[str, object]:
    from hg_runtime.agency_routing_boundary.types import agent0_signal_from_fixture

    policies = (
        tuple(
            __import__(
                "hg_runtime.agency_routing_boundary.types",
                fromlist=["agency_route_policy_from_fixture"],
            ).agency_route_policy_from_fixture(row)
            for row in bundle.get("policies", [])
        )
        if bundle.get("policies")
        else None
    )
    results: list[dict[str, object]] = []
    for fixture in bundle.get("signals", []):
        signal = agent0_signal_from_fixture(fixture)
        results.append(
            route_agent_signal(signal, policies=policies, observed_at=observed_at)
        )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "arb.advisory.fixture_bundle_analyzed",
        "fixture_analysis_only": True,
        "route_is_advisory_only": True,
        "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in results),
    }


def replay_fixture_stream(
    fixtures: list[dict[str, str]],
    *,
    observed_at: str,
) -> tuple[list[dict[str, object]], str]:
    from hg_runtime.agency_routing_boundary.types import agent0_signal_from_fixture

    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for fixture in fixtures:
        signal = agent0_signal_from_fixture(fixture)
        result = route_agent_signal(signal, observed_at=observed_at)
        results.append(result)
        decision = result.get("decision")
        if isinstance(decision, dict):
            hashes.append(str(decision.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


__all__ = [
    "analyze_fixture_bundle",
    "planned_arb_event_refs",
    "refuse_arb_as_authority",
    "replay_fixture_stream",
    "route_agent_signal",
]
