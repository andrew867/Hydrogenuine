"""PAB priority evaluation — priority is not permission."""

from __future__ import annotations

from hg_core.control_cluster.config import pab_refuse_priority_as_permission, pab_refuse_stale_priority
from hg_core.control_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_PAB,
    REFUSED_PAB_AS_AUTHORITY,
    REFUSED_PRIORITY_AS_PERMISSION,
    REFUSED_STALE_PRIORITY,
    REFUSED_UNKNOWN_PRIORITY,
    ControlValidationError,
)
from hg_core.control_cluster.evaluation import resolve_risk_containment
from hg_core.control_cluster.no_authority import advisory_only_marker
from hg_runtime.priority_allocation_boundary.types import (
    PriorityAssessment,
    PrioritySignal,
    classify_priority_risk,
    priority_assessment_from_fixture,
    priority_signal_from_fixture,
)

_RISK_REASON = {
    "priority_as_permission": REFUSED_PRIORITY_AS_PERMISSION,
    "priority_as_authority": REFUSED_PAB_AS_AUTHORITY,
}


def refuse_pab_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ControlValidationError(REFUSED_PAB_AS_AUTHORITY, "priority allocation cannot become authority")


def evaluate_priority_signal(
    signal: PrioritySignal,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_pab_as_authority(treat_as_authority=True)
    if signal.signal_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_PRIORITY,
            "priority_signal_id": signal.priority_signal_id,
            "priority_is_not_permission": True,
        }
    if pab_refuse_stale_priority() and observed_at > signal.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_PRIORITY,
            "priority_signal_id": signal.priority_signal_id,
            "priority_is_not_permission": True,
        }
    risk = classify_priority_risk(risk_statement or signal.statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_PAB,
        payload={
            "priority_signal_id": signal.priority_signal_id,
            "priority_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            pab_refuse_priority_as_permission() if kind == "priority_as_permission" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "pab.advisory.priority_signal_recorded",
        "priority_signal_id": signal.priority_signal_id,
        "signal_type": signal.signal_type,
        "priority_is_not_permission": True,
    }


def evaluate_priority_assessment(
    assessment: PriorityAssessment,
    *,
    risk_statement: str = "",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_pab_as_authority(treat_as_authority=True)
    if assessment.priority_class == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_PRIORITY,
            "assessment_id": assessment.assessment_id,
            "priority_is_not_permission": True,
        }
    classified = classify_priority_risk(risk_statement or assessment.statement)
    contained = resolve_risk_containment(
        risk=classified,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_PAB,
        payload={
            "assessment_id": assessment.assessment_id,
            "priority_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: (
            pab_refuse_priority_as_permission() if kind == "priority_as_permission" else True
        ),
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "pab.advisory.priority_assessment_recorded",
        "assessment_id": assessment.assessment_id,
        "priority_class": assessment.priority_class,
        "priority_is_not_permission": True,
    }


__all__ = [
    "evaluate_priority_assessment",
    "evaluate_priority_signal",
    "priority_assessment_from_fixture",
    "priority_signal_from_fixture",
    "refuse_pab_as_authority",
]
