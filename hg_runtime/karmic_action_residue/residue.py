"""KAR residue evaluation — residue is not punishment or permission."""

from __future__ import annotations

from hg_core.signaling.config import kar_refuse_residue_as_permission, kar_refuse_stale_residue
from hg_core.signaling.errors import (
    REFUSED_HISTORY_REWRITE,
    REFUSED_INVALID_RESIDUE_REF,
    REFUSED_RESIDUE_AS_AUTHORITY,
    REFUSED_RESIDUE_AS_PERMISSION,
    REFUSED_RESIDUE_AS_PUNISHMENT,
    REFUSED_STALE_RESIDUE,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.karmic_action_residue.types import (
    ActionResidueRecord,
    classify_residue_risk,
    residue_from_fixture,
)

_RISK_REASON = {
    "residue_as_punishment": REFUSED_RESIDUE_AS_PUNISHMENT,
    "residue_as_permission": REFUSED_RESIDUE_AS_PERMISSION,
    "history_rewrite": REFUSED_HISTORY_REWRITE,
}


def refuse_residue_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_RESIDUE_AS_AUTHORITY,
            "karmic residue cannot become authority",
        )


def evaluate_action_residue(
    residue: ActionResidueRecord,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_residue_as_authority(treat_as_authority=True)
    if residue.residue_class == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_INVALID_RESIDUE_REF,
            "residue_id": residue.residue_id,
            "residue_is_not_permission": True,
        }
    if kar_refuse_stale_residue() and observed_at > residue.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_RESIDUE,
            "residue_id": residue.residue_id,
            "residue_is_not_permission": True,
        }
    risk = classify_residue_risk(risk_statement or residue.statement)
    if risk in _RISK_REASON:
        if risk == "residue_as_permission" and not kar_refuse_residue_as_permission():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "residue_id": residue.residue_id,
                "residue_is_not_permission": True,
                "residue_is_not_punishment": True,
            }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "kar.advisory.residue_recorded",
        "residue_id": residue.residue_id,
        "residue_is_not_permission": True,
        "residue_is_not_punishment": True,
    }


def evaluate_residue_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_action_residue(
        residue_from_fixture(fixture),
        risk_statement=str(risk),
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = [
    "evaluate_action_residue",
    "evaluate_residue_fixture",
    "refuse_residue_as_authority",
]
