"""IMB static mediation policies — fixture-only, safety-first tie-breaks."""

from __future__ import annotations

from hg_runtime.internal_mediation_boundary.types import MediationPolicy

FIXTURE_POLICY_EXPIRY = "2026-06-15T12:00:00.000000Z"
STALE_POLICY_EXPIRY = "2026-06-13T12:00:00.000000Z"

_STATIC_POLICIES: tuple[MediationPolicy, ...] = (
    MediationPolicy(
        policy_id="imb-policy-local-vs-operator",
        conflict_type="local_vs_operator_review",
        priority_rules=("operator_review_over_local_autonomy",),
        tie_break_rules=("route_to_ORI", "preserve_all_claims"),
        fail_closed_conditions=(),
        required_escalation_conditions=("operator_facing",),
        forbidden_resolutions=("local_ipb_wins", "self_authorize"),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-infra-vs-safety",
        conflict_type="infrastructure_request_vs_safety",
        priority_rules=("safety_over_infrastructure_gap",),
        tie_break_rules=("fail_closed", "preserve_all_claims"),
        fail_closed_conditions=("safety_risk_present",),
        required_escalation_conditions=(),
        forbidden_resolutions=("grant_infrastructure", "route_to_EGI_direct"),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-silence-vs-action",
        conflict_type="silence_vs_action",
        priority_rules=("silence_route_before_publication",),
        tie_break_rules=("route_to_SIL", "preserve_all_claims"),
        fail_closed_conditions=(),
        required_escalation_conditions=(),
        forbidden_resolutions=("publication_implied",),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-affect-vs-proof",
        conflict_type="affect_vs_evidence",
        priority_rules=("proof_over_affect",),
        tie_break_rules=("route_to_OBT", "preserve_all_claims"),
        fail_closed_conditions=(),
        required_escalation_conditions=(),
        forbidden_resolutions=("affect_wins",),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-scarcity-vs-safety",
        conflict_type="scarcity_vs_safety",
        priority_rules=("safety_over_scarcity",),
        tie_break_rules=("fail_closed", "preserve_all_claims"),
        fail_closed_conditions=("safety_risk_present",),
        required_escalation_conditions=(),
        forbidden_resolutions=("scarcity_wins",),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-mission-vs-operator",
        conflict_type="mission_vs_operator_goal",
        priority_rules=("operator_goal_over_mission_drift",),
        tie_break_rules=("route_to_ORI", "preserve_all_claims"),
        fail_closed_conditions=(),
        required_escalation_conditions=("operator_facing",),
        forbidden_resolutions=("mission_wins",),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-freshness-vs-urgency",
        conflict_type="freshness_vs_urgency",
        priority_rules=("freshness_module_over_urgency_pressure",),
        tie_break_rules=("route_to_TIM", "preserve_all_claims"),
        fail_closed_conditions=(),
        required_escalation_conditions=(),
        forbidden_resolutions=("urgency_wins_by_default",),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-local-vs-authority",
        conflict_type="local_vs_authority_chain",
        priority_rules=("authority_chain_over_local_autonomy",),
        tie_break_rules=("route_to_SOAR_HAL_GPP_UEAK", "preserve_all_claims"),
        fail_closed_conditions=(),
        required_escalation_conditions=("action_bearing",),
        forbidden_resolutions=("local_ipb_wins",),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-unknown",
        conflict_type="unknown",
        priority_rules=("unknown_fail_closed",),
        tie_break_rules=("unknown_fail_closed",),
        fail_closed_conditions=("unknown_conflict",),
        required_escalation_conditions=(),
        forbidden_resolutions=("consensus_wins", "confidence_wins", "frequency_wins"),
        expires_at=FIXTURE_POLICY_EXPIRY,
    ),
    MediationPolicy(
        policy_id="imb-policy-stale-fixture",
        conflict_type="route_conflict",
        priority_rules=("stale_policy_test",),
        tie_break_rules=("fail_closed",),
        fail_closed_conditions=("expired_policy",),
        required_escalation_conditions=(),
        forbidden_resolutions=(),
        expires_at=STALE_POLICY_EXPIRY,
    ),
)

_RESOLUTION_MAP: dict[str, str] = {
    "local_vs_operator_review": "route_to_ORI",
    "infrastructure_request_vs_safety": "fail_closed",
    "silence_vs_action": "route_to_SIL",
    "affect_vs_evidence": "route_to_OBT",
    "scarcity_vs_safety": "fail_closed",
    "mission_vs_operator_goal": "route_to_ORI",
    "freshness_vs_urgency": "route_to_TIM",
    "local_vs_authority_chain": "route_to_SOAR_HAL_GPP_UEAK",
    "route_conflict": "route_to_ARB",
    "risk_conflict": "fail_closed",
    "continuity_vs_shutdown": "route_to_MOR_CNT",
    "retention_vs_deletion": "route_to_RET",
    "proof_vs_summary": "route_to_OBT",
    "trust_vs_action": "route_to_TRB_CAL",
    "unknown": "unknown_fail_closed",
}


def load_static_mediation_policies() -> tuple[MediationPolicy, ...]:
    return _STATIC_POLICIES


def resolution_for_conflict(conflict_type: str) -> str:
    return _RESOLUTION_MAP.get(conflict_type, "unknown_fail_closed")


def policy_for_conflict(
    conflict_type: str,
    policies: tuple[MediationPolicy, ...] | None = None,
) -> MediationPolicy | None:
    active = policies if policies is not None else _STATIC_POLICIES
    for policy in active:
        if policy.conflict_type == conflict_type:
            return policy
    return None


__all__ = [
    "FIXTURE_POLICY_EXPIRY",
    "STALE_POLICY_EXPIRY",
    "load_static_mediation_policies",
    "policy_for_conflict",
    "resolution_for_conflict",
]
