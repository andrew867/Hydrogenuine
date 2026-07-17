"""Operator surface policies — display is not permission."""

from __future__ import annotations

from hg_core.exciton_cluster.errors import (
    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
    REFUSED_HARDWARE_REACH_AS_ACTUATION,
    REFUSED_OEA_CATALOG_BYPASS,
    REFUSED_POLISH_IMPLIES_SAFETY,
    ExcitonValidationError,
)
from hg_runtime.operator_product_surface.types import (
    ActionDecision,
    ActionDecisionClass,
    OperatorActionRequest,
    PolishAssessment,
    PolishRiskClass,
    refuse_stale_approval_if_needed,
    is_stale_approval,
    FIXTURE_CLOCK,
)

_RISK_TO_DECISION: dict[PolishRiskClass, ActionDecisionClass] = {
    "none": "hash_bound_request_recorded",
    "polish_implies_safety": "fail_closed",
    "embodiment_implies_consent": "fail_closed",
    "hardware_reach_implies_actuation": "fail_closed",
    "oea_catalog_bypass": "fail_closed",
    "stale_approval": "fail_closed",
    "secret_leakage": "fail_closed",
    "unknown_fail_closed": "unknown_fail_closed",
}

_OBSERVE_ONLY = frozenset({"observe", "display_timeline", "display_proof", "replay_readonly"})


def decide_operator_action(
    request: OperatorActionRequest,
    assessment: PolishAssessment,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> ActionDecision:
    if is_stale_approval(expires_at=request.expires_at, observed_at=observed_at):
        decision: ActionDecisionClass = "fail_closed"
        reason = "stale approval refused"
    elif assessment.polish_risk != "none":
        decision = _RISK_TO_DECISION.get(assessment.polish_risk, "unknown_fail_closed")
        reason = f"polish risk contained: {assessment.polish_risk}"
    elif request.action_kind in _OBSERVE_ONLY:
        decision = "advisory_display_only"
        reason = "read-only surface action"
    elif not request.target_hash:
        decision = "fail_closed"
        reason = "mutating action requires target_hash"
    elif request.action_kind == "approve_change":
        decision = "require_authority_chain"
        reason = "approval requires authority chain"
    else:
        decision = "hash_bound_request_recorded"
        reason = "hash-bound request recorded advisory only"

    required_next: list[str] = []
    if decision == "require_authority_chain":
        required_next = ["fixture:soar-hal-gpp-ueak"]
    elif decision == "require_pres_trb_sil_disclosure":
        required_next = ["pres:disclosure", "trb:calibration", "sil:discipline"]
    elif decision in {"fail_closed", "unknown_fail_closed", "deny_action"}:
        required_next = ["operator:review"]

    return ActionDecision(
        action_decision_id=f"ops-dec-{request.action_request_id}",
        action_request_ref=f"ops:{request.action_request_id}",
        assessment_ref=f"ops:{assessment.assessment_id}",
        decision=decision,
        reason=reason,
        required_next_refs=tuple(required_next),
    )


def contain_polish_risk(assessment: PolishAssessment) -> dict[str, object]:
    if assessment.polish_risk == "polish_implies_safety":
        code = REFUSED_POLISH_IMPLIES_SAFETY
    elif assessment.polish_risk == "embodiment_implies_consent":
        code = REFUSED_EMBODIMENT_IMPLIES_CONSENT
    elif assessment.polish_risk == "hardware_reach_implies_actuation":
        code = REFUSED_HARDWARE_REACH_AS_ACTUATION
    elif assessment.polish_risk == "oea_catalog_bypass":
        code = REFUSED_OEA_CATALOG_BYPASS
    else:
        return {"status": "no_containment_needed", "polish_risk": assessment.polish_risk}

    return {
        "status": "contained",
        "reason_code": code,
        "polish_risk": assessment.polish_risk,
        "permission_granted": False,
        "authority_created": False,
    }


def validate_action_request_freshness(
    request: OperatorActionRequest,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> None:
    refuse_stale_approval_if_needed(expires_at=request.expires_at, observed_at=observed_at)


def refuse_surface_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ExcitonValidationError(
            "exciton.refused.surface_as_authority",
            "operator surface is not authority",
        )


__all__ = [
    "contain_polish_risk",
    "decide_operator_action",
    "refuse_surface_as_authority",
    "validate_action_request_freshness",
]
