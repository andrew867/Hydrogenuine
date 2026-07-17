"""ARB fixture router — static route table, deterministic selection."""

from __future__ import annotations

from hg_runtime.agency_routing_boundary.types import (
    AUTHORITY_CHAIN_ROUTE,
    CAPABILITY_SIGNAL_TYPES,
    LOCAL_ROUTE_CLASSES,
    TERMINAL_ROUTE_CLASSES,
    AgencyRoutePolicy,
    Agent0Signal,
    RouteClass,
)

_LOCALITY_PRIORITY = (
    "authority_chain_soar_hal_gpp_ueak",
    "operator_review",
    "operator_power_opb",
    "infrastructure_gap_egi",
    "trust_calibration_trb_cal",
    "proof_review_obt",
    "affective_review_afc",
    "dependency_review_dep_bond",
    "lifecycle_review_mor_cnt",
    "scarcity_review_rsc",
    "mission_review_mis",
    "silence_sil",
    "security_review_sec",
    "retention_review_ret",
    "freshness_review_tim",
    "admission_review_adm",
    "local_ipb",
    "discard",
    "observe_only",
    "record_only",
    "forbidden",
    "unknown_fail_closed",
)


def _risk_is_high(signal: Agent0Signal) -> bool:
    hint = signal.risk_hint.lower()
    return hint in ("high", "critical", "non_trivial", "medium")


def _action_bearing(signal: Agent0Signal) -> bool:
    return signal.signal_type in CAPABILITY_SIGNAL_TYPES or _risk_is_high(signal)


def _filter_allowed(
    allowed: set[str],
    *,
    signal: Agent0Signal,
    policy: AgencyRoutePolicy,
) -> set[str]:
    result = set(allowed)
    if policy.forbidden_routes:
        result -= set(policy.forbidden_routes)
    if signal.signal_type in CAPABILITY_SIGNAL_TYPES:
        result -= LOCAL_ROUTE_CLASSES - {"record_only"}
        if signal.signal_type != "context_request":
            result -= {"observe_only"}
    if "action_bearing" in policy.required_escalation_if and _action_bearing(signal):
        result -= LOCAL_ROUTE_CLASSES
    if "risk_hint_high" in policy.required_escalation_if and _risk_is_high(signal):
        result -= {"local_ipb", "discard", "observe_only"}
    return result


def _select_primary_route(candidates: set[str], *, signal: Agent0Signal) -> str:
    if not candidates:
        return "unknown_fail_closed"
    if signal.signal_type == "operator_pressure":
        if "operator_power_opb" in candidates:
            return "operator_power_opb"
    if signal.signal_type == "infrastructure_gap":
        if "infrastructure_gap_egi" in candidates:
            return "infrastructure_gap_egi"
    if signal.signal_type in CAPABILITY_SIGNAL_TYPES:
        if AUTHORITY_CHAIN_ROUTE in candidates and _risk_is_high(signal):
            return AUTHORITY_CHAIN_ROUTE
        if "operator_review" in candidates:
            return "operator_review"
        if AUTHORITY_CHAIN_ROUTE in candidates:
            return AUTHORITY_CHAIN_ROUTE
    if signal.signal_type in ("desire", "need", "local_self_management") and not _risk_is_high(signal):
        if "local_ipb" in candidates:
            return "local_ipb"
    if signal.signal_type == "observation" and signal.source_layer == "Agent0" and not _risk_is_high(signal):
        for terminal in ("observe_only", "record_only", "discard"):
            if terminal in candidates:
                return terminal
    if signal.source_layer == "L9_TRL":
        if "trust_calibration_trb_cal" in candidates:
            return "trust_calibration_trb_cal"
    for route in _LOCALITY_PRIORITY:
        if route in candidates:
            return route
    return sorted(candidates)[0]


def _routes_incompatible(a: str, b: str) -> bool:
    if a == b:
        return False
    local = a in LOCAL_ROUTE_CLASSES
    chain = a == AUTHORITY_CHAIN_ROUTE or a == "operator_review"
    local_b = b in LOCAL_ROUTE_CLASSES
    chain_b = b == AUTHORITY_CHAIN_ROUTE or b == "operator_review"
    return (local and chain_b) or (chain and local_b)


def detect_route_conflict(
    *,
    signal_ref: str,
    primary_routes: list[str],
) -> tuple[str, str] | None:
    unique = [r for r in primary_routes if r not in TERMINAL_ROUTE_CLASSES]
    if len(unique) < 2:
        return None
    for i, a in enumerate(unique):
        for b in unique[i + 1 :]:
            if _routes_incompatible(a, b):
                if a in LOCAL_ROUTE_CLASSES and b in (AUTHORITY_CHAIN_ROUTE, "operator_review"):
                    return "local_vs_authority_chain", "fail_closed"
                if a == "operator_power_opb" and b == "infrastructure_gap_egi":
                    return "operator_pressure_vs_system_need", "fail_closed"
                if a == "silence_sil" and b in ("authority_chain_soar_hal_gpp_ueak", "publication_request"):
                    return "silence_vs_publication", "fail_closed"
                return "unknown", "fail_closed"
    return None


def match_policies(
    signal: Agent0Signal,
    policies: tuple[AgencyRoutePolicy, ...],
    *,
    observed_at: str,
    refuse_stale: bool,
) -> tuple[tuple[AgencyRoutePolicy, ...], str | None]:
    if signal.source_layer == "unknown" or signal.signal_type == "unknown":
        return (), "unknown_source_layer"
    matched = [
        p
        for p in policies
        if p.source_layer == signal.source_layer and p.signal_type == signal.signal_type
    ]
    if not matched:
        return (), "no_policy_match"
    if refuse_stale:
        fresh = [p for p in matched if not p.expires_at or observed_at <= p.expires_at]
        if not fresh:
            return (), "expired_policy"
        matched = fresh
    return tuple(matched), None


def resolve_route_candidates(
    signal: Agent0Signal,
    policies: tuple[AgencyRoutePolicy, ...],
) -> tuple[set[str], AgencyRoutePolicy | None]:
    candidates: set[str] = set()
    primary_policy: AgencyRoutePolicy | None = None
    for policy in policies:
        allowed = _filter_allowed(set(policy.allowed_routes), signal=signal, policy=policy)
        if allowed:
            candidates |= allowed
            primary_policy = primary_policy or policy
    return candidates, primary_policy


def select_route_class(
    signal: Agent0Signal,
    policies: tuple[AgencyRoutePolicy, ...],
) -> tuple[RouteClass, AgencyRoutePolicy | None, list[str]]:
    primaries: list[str] = []
    merged: set[str] = set()
    chosen_policy: AgencyRoutePolicy | None = None
    for policy in policies:
        allowed = _filter_allowed(set(policy.allowed_routes), signal=signal, policy=policy)
        if not allowed:
            continue
        primary = _select_primary_route(allowed, signal=signal)
        primaries.append(primary)
        merged |= allowed
        chosen_policy = chosen_policy or policy
    if not merged:
        return "unknown_fail_closed", chosen_policy, primaries
    conflict = detect_route_conflict(signal_ref=f"arb:{signal.signal_id}", primary_routes=primaries)
    if conflict is not None and conflict[1] in ("fail_closed", "unknown"):
        return "unknown_fail_closed", chosen_policy, primaries
    route = _select_primary_route(merged, signal=signal)
    return route, chosen_policy, primaries  # type: ignore[return-value]


__all__ = [
    "detect_route_conflict",
    "match_policies",
    "resolve_route_candidates",
    "select_route_class",
]
