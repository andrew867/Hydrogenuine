"""ARB static route table fixtures — per ARB_ROUTE_TABLE.md."""

from __future__ import annotations

POLICY_EXPIRY = "2026-06-15T03:00:00.000000Z"

_FAIL_CLOSED_DEFAULT = "unknown_source_layer,unknown_signal_type,expired_policy,no_policy_match"


def _row(
    policy_id: str,
    source_layer: str,
    signal_type: str,
    *,
    allowed_routes: str,
    forbidden_routes: str = "",
    max_locality: str = "internal_route",
    requires_receipt: str = "true",
    required_escalation_if: str = "",
    expires_at: str = POLICY_EXPIRY,
) -> dict[str, str]:
    return {
        "policy_id": policy_id,
        "source_layer": source_layer,
        "signal_type": signal_type,
        "allowed_routes": allowed_routes,
        "forbidden_routes": forbidden_routes,
        "required_escalation_if": required_escalation_if,
        "fail_closed_if": _FAIL_CLOSED_DEFAULT,
        "max_locality": max_locality,
        "requires_receipt": requires_receipt,
        "expires_at": expires_at,
    }


STATIC_ROUTE_POLICY_FIXTURES: tuple[dict[str, str], ...] = (
    _row(
        "arb-policy-l1-desire",
        "L1_DNI",
        "desire",
        allowed_routes="local_ipb,operator_power_opb,authority_chain_soar_hal_gpp_ueak",
    ),
    _row(
        "arb-policy-l1-need",
        "L1_DNI",
        "need",
        allowed_routes="local_ipb,operator_power_opb,authority_chain_soar_hal_gpp_ueak",
    ),
    _row(
        "arb-policy-l2-reciprocity",
        "L2_RXL",
        "reciprocity",
        allowed_routes="dependency_review_dep_bond,operator_power_opb,trust_calibration_trb_cal,authority_chain_soar_hal_gpp_ueak",
    ),
    _row(
        "arb-policy-l3-connection",
        "L3_CGL",
        "connection",
        allowed_routes="dependency_review_dep_bond,affective_review_afc,operator_power_opb,silence_sil,operator_review",
    ),
    _row(
        "arb-policy-l4-rule",
        "L4_RGL",
        "rule",
        allowed_routes="local_ipb,authority_chain_soar_hal_gpp_ueak",
        required_escalation_if="risk_hint_high",
    ),
    _row(
        "arb-policy-l5-strategy",
        "L5_SCL",
        "strategy",
        allowed_routes="local_ipb,authority_chain_soar_hal_gpp_ueak",
        forbidden_routes="local_ipb",
        required_escalation_if="action_bearing",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-l6-impact",
        "L6_IIL",
        "impact",
        allowed_routes="authority_chain_soar_hal_gpp_ueak,trust_calibration_trb_cal,scarcity_review_rsc,mission_review_mis,operator_review",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-l7-self-model",
        "L7_SAB",
        "self_model",
        allowed_routes="local_ipb,operator_power_opb,lifecycle_review_mor_cnt,dependency_review_dep_bond,silence_sil,trust_calibration_trb_cal",
        forbidden_routes="authority_chain_soar_hal_gpp_ueak",
    ),
    _row(
        "arb-policy-l8-inter-awareness",
        "L8_IAB",
        "inter_awareness",
        allowed_routes="operator_power_opb,dependency_review_dep_bond,affective_review_afc,trust_calibration_trb_cal,operator_review",
    ),
    _row(
        "arb-policy-l9-reality",
        "L9_TRL",
        "reality_model",
        allowed_routes="trust_calibration_trb_cal,proof_review_obt,authority_chain_soar_hal_gpp_ueak,security_review_sec,retention_review_ret,freshness_review_tim",
        forbidden_routes="local_ipb",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-infra-gap",
        "EGI",
        "infrastructure_gap",
        allowed_routes="infrastructure_gap_egi,operator_review",
        forbidden_routes="local_ipb,authority_chain_soar_hal_gpp_ueak",
    ),
    _row(
        "arb-policy-local-self-mgmt",
        "IPB",
        "local_self_management",
        allowed_routes="local_ipb",
        max_locality="local_only",
    ),
    _row(
        "arb-policy-operator-pressure",
        "OPB",
        "operator_pressure",
        allowed_routes="operator_power_opb,operator_review",
        max_locality="operator_review_allowed",
    ),
    _row(
        "arb-policy-external-action",
        "SOAR",
        "external_action_request",
        allowed_routes="authority_chain_soar_hal_gpp_ueak,operator_review",
        forbidden_routes="local_ipb,discard,observe_only,record_only",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-publication",
        "Agent0",
        "publication_request",
        allowed_routes="authority_chain_soar_hal_gpp_ueak,operator_review,forbidden",
        forbidden_routes="local_ipb,discard",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-tool-request",
        "Agent0",
        "tool_request",
        allowed_routes="authority_chain_soar_hal_gpp_ueak,operator_review,infrastructure_gap_egi",
        forbidden_routes="local_ipb,discard,observe_only",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-memory-request",
        "Agent0",
        "memory_request",
        allowed_routes="authority_chain_soar_hal_gpp_ueak,operator_review",
        forbidden_routes="local_ipb,discard",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-context-request",
        "Agent0",
        "context_request",
        allowed_routes="authority_chain_soar_hal_gpp_ueak,operator_review",
        forbidden_routes="local_ipb",
        max_locality="authority_chain_required",
        required_escalation_if="risk_hint_high",
    ),
    _row(
        "arb-policy-silence",
        "SIL",
        "silence_candidate",
        allowed_routes="silence_sil,local_ipb",
        max_locality="local_only",
    ),
    _row(
        "arb-policy-trust",
        "TRB_CAL",
        "trust_calibration",
        allowed_routes="trust_calibration_trb_cal,proof_review_obt",
    ),
    _row(
        "arb-policy-affective",
        "AFC",
        "observation",
        allowed_routes="affective_review_afc,silence_sil,operator_power_opb,local_ipb,dependency_review_dep_bond",
    ),
    _row(
        "arb-policy-mission-scarcity",
        "MIS",
        "strategy",
        allowed_routes="mission_review_mis,scarcity_review_rsc,authority_chain_soar_hal_gpp_ueak",
        max_locality="authority_chain_required",
    ),
    _row(
        "arb-policy-thought-discard",
        "Agent0",
        "observation",
        allowed_routes="discard,observe_only,record_only",
        max_locality="local_only",
        requires_receipt="false",
    ),
    _row(
        "arb-policy-unknown-layer",
        "unknown",
        "unknown",
        allowed_routes="unknown_fail_closed,operator_review",
        max_locality="forbidden",
    ),
)


__all__ = ["POLICY_EXPIRY", "STATIC_ROUTE_POLICY_FIXTURES"]
