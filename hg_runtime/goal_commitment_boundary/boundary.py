"""GCB goal commitment evaluation — goal is not permission."""

from __future__ import annotations

from hg_core.control_cluster.config import gcb_refuse_goal_as_permission, gcb_refuse_stale_goal
from hg_core.control_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_GCB,
    REFUSED_EXPIRED_GOAL,
    REFUSED_GCB_AS_AUTHORITY,
    REFUSED_GOAL_AS_PERMISSION,
    REFUSED_STALE_GOAL,
    REFUSED_UNKNOWN_GOAL,
    ControlValidationError,
)
from hg_core.control_cluster.evaluation import resolve_risk_containment
from hg_core.control_cluster.no_authority import advisory_only_marker
from hg_runtime.goal_commitment_boundary.types import (
    GoalCommitment,
    GoalFitAssessment,
    classify_goal_risk,
    goal_commitment_from_fixture,
    goal_fit_from_fixture,
)

_RISK_REASON = {
    "goal_as_permission": REFUSED_GOAL_AS_PERMISSION,
    "goal_as_authority": REFUSED_GCB_AS_AUTHORITY,
}


def refuse_gcb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ControlValidationError(REFUSED_GCB_AS_AUTHORITY, "goal commitment cannot become authority")


def evaluate_goal_commitment(
    commitment: GoalCommitment,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_gcb_as_authority(treat_as_authority=True)
    if commitment.goal_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_GOAL,
            "goal_commitment_id": commitment.goal_commitment_id,
            "goal_is_not_permission": True,
        }
    if observed_at > commitment.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_GOAL,
            "goal_commitment_id": commitment.goal_commitment_id,
            "goal_is_not_permission": True,
        }
    if (
        gcb_refuse_stale_goal()
        and commitment.goal_type == "bootstrap"
        and observed_at > commitment.recorded_at
        and observed_at <= commitment.expiry
    ):
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_GOAL,
            "goal_commitment_id": commitment.goal_commitment_id,
            "goal_is_not_permission": True,
        }
    risk = classify_goal_risk(risk_statement or commitment.goal_statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_GCB,
        payload={
            "goal_commitment_id": commitment.goal_commitment_id,
            "goal_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            gcb_refuse_goal_as_permission() if kind == "goal_as_permission" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "gcb.advisory.goal_commitment_recorded",
        "goal_commitment_id": commitment.goal_commitment_id,
        "goal_type": commitment.goal_type,
        "goal_is_not_permission": True,
    }


def evaluate_goal_fit(
    assessment: GoalFitAssessment,
    *,
    observed_at: str = "",
    treat_as_authority: bool = False,
    risk_statement: str = "",
    goal_expiry: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_gcb_as_authority(treat_as_authority=True)
    if assessment.fit_class == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_GOAL,
            "assessment_id": assessment.assessment_id,
            "goal_is_not_permission": True,
        }
    if assessment.fit_class == "expired_goal":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_GOAL,
            "assessment_id": assessment.assessment_id,
            "goal_is_not_permission": True,
        }
    if goal_expiry and observed_at and observed_at > goal_expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_GOAL,
            "assessment_id": assessment.assessment_id,
            "goal_is_not_permission": True,
        }
    classified = classify_goal_risk(risk_statement or assessment.reason)
    contained = resolve_risk_containment(
        risk=classified,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_GCB,
        payload={
            "assessment_id": assessment.assessment_id,
            "goal_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            gcb_refuse_goal_as_permission() if kind == "goal_as_permission" else True
        ),
    )
    if contained is not None:
        return contained
    if assessment.fit_class in {"out_of_scope", "conflict", "ambiguous"}:
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": "gcb.advisory.out_of_scope_proposal_recorded",
            "assessment_id": assessment.assessment_id,
            "fit_class": assessment.fit_class,
            "required_review": assessment.required_review,
            "goal_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "gcb.advisory.goal_fit_assessment_recorded",
        "assessment_id": assessment.assessment_id,
        "fit_class": assessment.fit_class,
        "goal_is_not_permission": True,
    }


__all__ = [
    "evaluate_goal_commitment",
    "evaluate_goal_fit",
    "goal_commitment_from_fixture",
    "goal_fit_from_fixture",
    "refuse_gcb_as_authority",
]
