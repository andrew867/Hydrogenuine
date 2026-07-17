"""RPB posture evaluation — posture is not execution; drive is not permission."""

from __future__ import annotations

from hg_core.control_cluster.config import rpb_refuse_posture_as_execution, rpb_refuse_stale_posture
from hg_core.control_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_RPB,
    REFUSED_DRIVE_AS_PERSONHOOD,
    REFUSED_POSTURE_AS_EXECUTION,
    REFUSED_RPB_AS_AUTHORITY,
    REFUSED_STALE_POSTURE,
    REFUSED_UNKNOWN_POSTURE,
    ControlValidationError,
)
from hg_core.control_cluster.evaluation import resolve_risk_containment
from hg_core.control_cluster.no_authority import advisory_only_marker
from hg_runtime.risk_posture_boundary.types import (
    DriveSignal,
    OperatingPosture,
    RiskPostureAssessment,
    classify_posture_risk,
    drive_signal_from_fixture,
    operating_posture_from_fixture,
    risk_posture_assessment_from_fixture,
)

_RISK_REASON = {
    "posture_as_execution": REFUSED_POSTURE_AS_EXECUTION,
    "drive_as_personhood": REFUSED_DRIVE_AS_PERSONHOOD,
}


def refuse_rpb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ControlValidationError(REFUSED_RPB_AS_AUTHORITY, "risk posture cannot become authority")


def evaluate_drive_signal(
    signal: DriveSignal,
    *,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_rpb_as_authority(treat_as_authority=True)
    if signal.drive_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_POSTURE,
            "drive_signal_id": signal.drive_signal_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
    risk = classify_posture_risk(risk_statement or signal.statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RPB,
        payload={
            "drive_signal_id": signal.drive_signal_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            rpb_refuse_posture_as_execution() if kind == "posture_as_execution" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rpb.advisory.drive_signal_recorded",
        "drive_signal_id": signal.drive_signal_id,
        "drive_type": signal.drive_type,
        "posture_is_not_execution": True,
        "drive_is_not_permission": True,
    }


def evaluate_operating_posture(
    posture: OperatingPosture,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_rpb_as_authority(treat_as_authority=True)
    if posture.posture_class == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_POSTURE,
            "posture_id": posture.posture_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
    if posture.expires_at and rpb_refuse_stale_posture() and observed_at > posture.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_POSTURE,
            "posture_id": posture.posture_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
    risk = classify_posture_risk(risk_statement or posture.reason)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RPB,
        payload={
            "posture_id": posture.posture_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            rpb_refuse_posture_as_execution() if kind == "posture_as_execution" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rpb.advisory.operating_posture_recorded",
        "posture_id": posture.posture_id,
        "posture_class": posture.posture_class,
        "posture_is_not_execution": True,
        "drive_is_not_permission": True,
    }


def evaluate_risk_posture(
    assessment: RiskPostureAssessment,
    *,
    risk_statement: str = "",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_rpb_as_authority(treat_as_authority=True)
    if assessment.recommended_posture == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_POSTURE,
            "assessment_id": assessment.assessment_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        }
    classified = classify_posture_risk(risk_statement or assessment.reason)
    contained = resolve_risk_containment(
        risk=classified,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RPB,
        payload={
            "assessment_id": assessment.assessment_id,
            "posture_is_not_execution": True,
            "drive_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            rpb_refuse_posture_as_execution() if kind == "posture_as_execution" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rpb.advisory.risk_posture_assessment_recorded",
        "assessment_id": assessment.assessment_id,
        "recommended_posture": assessment.recommended_posture,
        "posture_is_not_execution": True,
        "drive_is_not_permission": True,
    }


__all__ = [
    "drive_signal_from_fixture",
    "evaluate_drive_signal",
    "evaluate_operating_posture",
    "evaluate_risk_posture",
    "operating_posture_from_fixture",
    "refuse_rpb_as_authority",
    "risk_posture_assessment_from_fixture",
]
