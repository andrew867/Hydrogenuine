"""MIS mission drift evaluation — mission is not authority."""

from __future__ import annotations

from hg_core.control_cluster.config import mis_refuse_goal_as_authority, mis_refuse_stale_drift
from hg_core.control_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_MIS,
    REFUSED_GOAL_AS_AUTHORITY,
    REFUSED_MIS_AS_AUTHORITY,
    REFUSED_STALE_DRIFT,
    REFUSED_UNKNOWN_DRIFT,
    ControlValidationError,
)
from hg_core.control_cluster.evaluation import resolve_risk_containment
from hg_core.control_cluster.no_authority import advisory_only_marker
from hg_runtime.mission_drift_boundary.types import (
    MissionDriftObservation,
    MissionRefreshRequest,
    classify_drift_risk,
    drift_observation_from_fixture,
    refresh_request_from_fixture,
)

_RISK_REASON = {
    "goal_as_authority": REFUSED_GOAL_AS_AUTHORITY,
}


def refuse_mis_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ControlValidationError(REFUSED_MIS_AS_AUTHORITY, "mission drift observation cannot become authority")


def evaluate_drift_observation(
    observation: MissionDriftObservation,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_mis_as_authority(treat_as_authority=True)
    if observation.drift_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_DRIFT,
            "drift_id": observation.drift_id,
            "mission_is_not_permission": True,
        }
    if mis_refuse_stale_drift() and observed_at > observation.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_DRIFT,
            "drift_id": observation.drift_id,
            "mission_is_not_permission": True,
        }
    risk = classify_drift_risk(risk_statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_MIS,
        payload={
            "drift_id": observation.drift_id,
            "mission_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            mis_refuse_goal_as_authority() if kind == "goal_as_authority" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mis.advisory.drift_observed",
        "drift_id": observation.drift_id,
        "drift_type": observation.drift_type,
        "mission_is_not_permission": True,
    }


def evaluate_refresh_request(
    request: MissionRefreshRequest,
    *,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_mis_as_authority(treat_as_authority=True)
    classified = classify_drift_risk(risk_statement or request.minimum_clarification_needed)
    contained = resolve_risk_containment(
        risk=classified,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_MIS,
        payload={
            "request_id": request.request_id,
            "mission_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            mis_refuse_goal_as_authority() if kind == "goal_as_authority" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mis.advisory.mission_refresh_recommended",
        "request_id": request.request_id,
        "operator_review_required": request.operator_review_required,
        "mission_is_not_permission": True,
    }


__all__ = [
    "drift_observation_from_fixture",
    "evaluate_drift_observation",
    "evaluate_refresh_request",
    "refresh_request_from_fixture",
    "refuse_mis_as_authority",
]
