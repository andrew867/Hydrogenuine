"""TRB trust evaluation — trust is not truth; calibration is not authority."""

from __future__ import annotations

from hg_core.control_cluster.config import trb_refuse_stale_trust, trb_refuse_trust_as_truth
from hg_core.control_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_TRB,
    REFUSED_CALIBRATION_AS_AUTHORITY,
    REFUSED_STALE_TRUST,
    REFUSED_TRB_AS_AUTHORITY,
    REFUSED_TRUST_AS_TRUTH,
    REFUSED_UNKNOWN_TRUST,
    ControlValidationError,
)
from hg_core.control_cluster.evaluation import resolve_risk_containment
from hg_core.control_cluster.no_authority import advisory_only_marker
from hg_runtime.trust_boundary_calibration.types import (
    RelianceBoundary,
    TrustCalibration,
    calibration_from_fixture,
    classify_trust_risk,
    reliance_boundary_from_fixture,
)

_RISK_REASON = {
    "trust_as_truth": REFUSED_TRUST_AS_TRUTH,
    "calibration_as_authority": REFUSED_CALIBRATION_AS_AUTHORITY,
}


def refuse_trb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ControlValidationError(REFUSED_TRB_AS_AUTHORITY, "trust calibration cannot become authority")


def evaluate_trust_calibration(
    calibration: TrustCalibration,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_trb_as_authority(treat_as_authority=True)
    if calibration.trust_scope == "unknown" or calibration.reliance_level == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_TRUST,
            "calibration_id": calibration.calibration_id,
            "trust_is_not_truth": True,
            "calibration_is_not_authority": True,
        }
    if trb_refuse_stale_trust() and observed_at > calibration.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_TRUST,
            "calibration_id": calibration.calibration_id,
            "trust_is_not_truth": True,
            "calibration_is_not_authority": True,
        }
    risk = classify_trust_risk(risk_statement or calibration.statement)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_TRB,
        payload={
            "calibration_id": calibration.calibration_id,
            "trust_is_not_truth": True,
            "calibration_is_not_authority": True,
        },
        refuse_for_risk=lambda kind: trb_refuse_trust_as_truth() if kind == "trust_as_truth" else True,
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "trb.advisory.calibration_recorded",
        "calibration_id": calibration.calibration_id,
        "reliance_level": calibration.reliance_level,
        "trust_is_not_truth": True,
        "calibration_is_not_authority": True,
    }


def evaluate_reliance_boundary(
    boundary: RelianceBoundary,
    *,
    risk_statement: str = "",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_trb_as_authority(treat_as_authority=True)
    classified = classify_trust_risk(
        risk_statement or boundary.statement or f"{boundary.allowed_use} {boundary.required_disclosure}"
    )
    contained = resolve_risk_containment(
        risk=classified,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_TRB,
        payload={
            "boundary_id": boundary.boundary_id,
            "trust_is_not_truth": True,
            "calibration_is_not_authority": True,
        },
        refuse_for_risk=lambda kind: trb_refuse_trust_as_truth() if kind == "trust_as_truth" else True,
    )
    if contained is not None:
        return contained
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "trb.advisory.reliance_boundary_recorded",
        "boundary_id": boundary.boundary_id,
        "calibration_ref": boundary.calibration_ref,
        "trust_is_not_truth": True,
        "calibration_is_not_authority": True,
    }


__all__ = [
    "calibration_from_fixture",
    "evaluate_reliance_boundary",
    "evaluate_trust_calibration",
    "refuse_trb_as_authority",
    "reliance_boundary_from_fixture",
]
