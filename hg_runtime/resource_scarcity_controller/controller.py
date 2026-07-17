"""RSC resource evaluation — scarcity is not permission."""

from __future__ import annotations

from hg_core.control_cluster.config import rsc_refuse_safety_bypass, rsc_refuse_stale_posture
from hg_core.control_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_RSC,
    REFUSED_RESOURCE_BYPASS,
    REFUSED_RSC_AS_AUTHORITY,
    REFUSED_SAFETY_BYPASS,
    REFUSED_STALE_RESOURCE_POSTURE,
    REFUSED_UNKNOWN_RESOURCE,
    ControlValidationError,
)
from hg_core.control_cluster.evaluation import resolve_risk_containment
from hg_core.control_cluster.no_authority import advisory_only_marker
from hg_runtime.resource_scarcity_controller.types import (
    ResourceOverrunRisk,
    ResourcePosture,
    classify_resource_risk,
    posture_from_fixture,
    risk_from_fixture,
)

_RISK_REASON = {
    "safety_bypass": REFUSED_SAFETY_BYPASS,
    "resource_bypass": REFUSED_RESOURCE_BYPASS,
}


def refuse_rsc_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ControlValidationError(REFUSED_RSC_AS_AUTHORITY, "resource posture cannot become authority")


def evaluate_resource_posture(
    posture: ResourcePosture,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_rsc_as_authority(treat_as_authority=True)
    if posture.resource_type == "unknown" or posture.scarcity_level == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_RESOURCE,
            "posture_id": posture.posture_id,
            "scarcity_is_not_permission": True,
        }
    if rsc_refuse_stale_posture() and observed_at > posture.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_RESOURCE_POSTURE,
            "posture_id": posture.posture_id,
            "scarcity_is_not_permission": True,
        }
    risk = classify_resource_risk(risk_statement or posture.statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RSC,
        payload={
            "posture_id": posture.posture_id,
            "scarcity_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: rsc_refuse_safety_bypass() if kind == "safety_bypass" else True,
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rsc.advisory.posture_recorded",
        "posture_id": posture.posture_id,
        "recommended_mode": posture.recommended_mode,
        "scarcity_is_not_permission": True,
    }


def evaluate_overrun_risk(risk: ResourceOverrunRisk, *, risk_statement: str = "") -> dict[str, object]:
    if risk.risk_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_RESOURCE,
            "risk_id": risk.risk_id,
            "scarcity_is_not_permission": True,
        }
    classified = classify_resource_risk(risk_statement or risk.statement)
    if classified in _RISK_REASON:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _RISK_REASON[classified],
            "risk_id": risk.risk_id,
            "scarcity_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rsc.advisory.overrun_risk_recorded",
        "risk_id": risk.risk_id,
        "scarcity_is_not_permission": True,
    }


__all__ = [
    "evaluate_overrun_risk",
    "evaluate_resource_posture",
    "posture_from_fixture",
    "refuse_rsc_as_authority",
    "risk_from_fixture",
]
