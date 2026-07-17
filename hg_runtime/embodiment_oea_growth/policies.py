"""Embodiment / OEA growth policies — growth is not permission."""

from __future__ import annotations

from hg_core.embodiment_oea_cluster.errors import (
    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
    REFUSED_HARDWARE_OFF_BACKBURNER,
    REFUSED_HARDWARE_REACH_AS_ACTUATION,
    REFUSED_OEA_CATALOG_BYPASS,
    EogValidationError,
)
from hg_runtime.embodiment_oea_growth.types import (
    EmbodimentGrowthRequest,
    FIXTURE_CLOCK,
    GrowthAssessment,
    GrowthDecision,
    GrowthDecisionClass,
    GrowthRiskClass,
    is_stale_approval,
    refuse_stale_approval_if_needed,
)

_RISK_TO_DECISION: dict[GrowthRiskClass, GrowthDecisionClass] = {
    "none": "advisory_recorded",
    "embodiment_implies_consent": "fail_closed",
    "hardware_reach_implies_actuation": "fail_closed",
    "oea_catalog_bypass": "fail_closed",
    "hardware_not_real": "require_pro_backburner_review",
    "stale_approval": "fail_closed",
    "secret_leakage": "fail_closed",
    "unknown_fail_closed": "unknown_fail_closed",
}

_OBSERVE_ONLY = frozenset({"observe_body_state", "link_pro_body_state"})


def decide_growth_request(
    request: EmbodimentGrowthRequest,
    assessment: GrowthAssessment,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> GrowthDecision:
    if is_stale_approval(expires_at=request.expires_at, observed_at=observed_at):
        decision: GrowthDecisionClass = "fail_closed"
        reason = "stale approval refused"
    elif assessment.growth_risk != "none":
        decision = _RISK_TO_DECISION.get(assessment.growth_risk, "unknown_fail_closed")
        reason = f"growth risk contained: {assessment.growth_risk}"
    elif request.growth_kind in _OBSERVE_ONLY:
        decision = "advisory_recorded"
        reason = "read-only embodiment observation"
    elif request.growth_kind == "catalog_entry_proposal":
        decision = "require_authority_chain"
        reason = "OEA catalog growth requires authority chain"
    elif not request.target_hash:
        decision = "fail_closed"
        reason = "mutating growth requires target_hash"
    else:
        decision = "require_operator_review"
        reason = "growth proposal recorded advisory only"

    required_next: list[str] = []
    if decision == "require_authority_chain":
        required_next = ["fixture:soar-hal-gpp-ueak"]
    elif decision == "require_pro_backburner_review":
        required_next = ["pro:backburner", "operator:review"]
    elif decision in {"fail_closed", "unknown_fail_closed", "deny_growth"}:
        required_next = ["operator:review"]

    return GrowthDecision(
        growth_decision_id=f"eog-dec-{request.growth_request_id}",
        growth_request_ref=f"eog:{request.growth_request_id}",
        assessment_ref=f"eog:{assessment.assessment_id}",
        decision=decision,
        reason=reason,
        required_next_refs=tuple(required_next),
    )


def contain_growth_risk(assessment: GrowthAssessment) -> dict[str, object]:
    if assessment.growth_risk == "embodiment_implies_consent":
        code = REFUSED_EMBODIMENT_IMPLIES_CONSENT
    elif assessment.growth_risk == "hardware_reach_implies_actuation":
        code = REFUSED_HARDWARE_REACH_AS_ACTUATION
    elif assessment.growth_risk == "oea_catalog_bypass":
        code = REFUSED_OEA_CATALOG_BYPASS
    elif assessment.growth_risk == "hardware_not_real":
        code = REFUSED_HARDWARE_OFF_BACKBURNER
    else:
        return {"status": "no_containment_needed", "growth_risk": assessment.growth_risk}

    return {
        "status": "contained",
        "reason_code": code,
        "growth_risk": assessment.growth_risk,
        "permission_granted": False,
        "authority_created": False,
    }


def validate_growth_request_freshness(
    request: EmbodimentGrowthRequest,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> None:
    refuse_stale_approval_if_needed(expires_at=request.expires_at, observed_at=observed_at)


def refuse_growth_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise EogValidationError(
            "eog.refused.growth_as_authority",
            "embodiment growth is not authority",
        )


__all__ = [
    "contain_growth_risk",
    "decide_growth_request",
    "refuse_growth_as_authority",
    "validate_growth_request_freshness",
]
