"""SBS semantic signal evaluation — resonance is not consent."""

from __future__ import annotations

from hg_core.signaling.config import (
    sbs_refuse_expired_signal,
    sbs_refuse_proximity_as_permission,
    sbs_refuse_resonance_as_consent,
)
from hg_core.signaling.errors import (
    REFUSED_EXPIRED_SIGNAL,
    REFUSED_GROUP_READINESS_AS_AUTHORITY,
    REFUSED_INCOMPATIBLE_SIGNAL,
    REFUSED_LEVEL_AS_RANK,
    REFUSED_NO_RESPONSE_AS_CONSENT,
    REFUSED_PROXIMITY_AS_PERMISSION,
    REFUSED_RESONANCE_AS_CONSENT,
    REFUSED_SIGNAL_AS_AUTHORITY,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.semantic_birdsong.types import (
    ResonanceAssessment,
    SemanticSignal,
    classify_signal_risk,
    resonance_from_fixture,
    signal_from_fixture,
)

_RISK_REASON = {
    "resonance_as_consent": REFUSED_RESONANCE_AS_CONSENT,
    "proximity_as_permission": REFUSED_PROXIMITY_AS_PERMISSION,
    "level_as_rank": REFUSED_LEVEL_AS_RANK,
    "group_readiness_as_authority": REFUSED_GROUP_READINESS_AS_AUTHORITY,
}


def refuse_signal_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_SIGNAL_AS_AUTHORITY,
            "semantic signal or resonance cannot become authority",
        )


def evaluate_semantic_signal(
    signal: SemanticSignal,
    *,
    observed_at: str,
    risk_statement: str = "",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_signal_as_authority(treat_as_authority=True)
    if sbs_refuse_expired_signal() and observed_at > signal.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_SIGNAL,
            "signal_id": signal.signal_id,
            "signal_is_not_authority": True,
        }
    if signal.signal_class == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_INCOMPATIBLE_SIGNAL,
            "signal_id": signal.signal_id,
            "signal_is_not_authority": True,
        }
    risk = classify_signal_risk(risk_statement)
    if risk in _RISK_REASON:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _RISK_REASON[risk],
            "signal_id": signal.signal_id,
            "signal_is_not_authority": True,
        }
    if sbs_refuse_proximity_as_permission() and signal.proximity == "external_service" and signal.urgency == "critical":
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_PROXIMITY_AS_PERMISSION,
            "signal_id": signal.signal_id,
            "signal_is_not_authority": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sbs.advisory.signal_recorded",
        "signal_id": signal.signal_id,
        "signal_is_not_authority": True,
        "resonance_is_not_consent": True,
        "proximity_is_not_permission": True,
    }


def evaluate_resonance_assessment(
    assessment: ResonanceAssessment,
    *,
    treat_as_authority: bool = False,
    no_response: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_signal_as_authority(treat_as_authority=True)
    if no_response:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_NO_RESPONSE_AS_CONSENT,
            "assessment_id": assessment.assessment_id,
            "resonance_is_not_consent": True,
        }
    risk = classify_signal_risk(assessment.statement)
    if risk == "resonance_as_consent" and sbs_refuse_resonance_as_consent():
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_RESONANCE_AS_CONSENT,
            "assessment_id": assessment.assessment_id,
            "resonance_is_not_consent": True,
        }
    if assessment.resonance_class in {"saturated", "oscillating"}:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": "sbs.advisory.signal_saturation_detected",
            "assessment_id": assessment.assessment_id,
            "resonance_class": assessment.resonance_class,
            "resonance_is_not_consent": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sbs.advisory.resonance_recorded",
        "assessment_id": assessment.assessment_id,
        "resonance_is_not_consent": True,
    }


def evaluate_signal_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_semantic_signal(
        signal_from_fixture(fixture),
        risk_statement=str(risk),
        **kwargs,  # type: ignore[arg-type]
    )


def evaluate_resonance_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_resonance_assessment(resonance_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_resonance_assessment",
    "evaluate_resonance_fixture",
    "evaluate_semantic_signal",
    "evaluate_signal_fixture",
    "refuse_signal_as_authority",
]
