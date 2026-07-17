"""NEG neglect evaluation — detection is not surveillance."""

from __future__ import annotations

from hg_core.signaling.config import neg_refuse_stale_observation, neg_refuse_surveillance_risk
from hg_core.signaling.errors import (
    REFUSED_INTENT_INFERENCE,
    REFUSED_NEGLECT_AS_AUTHORITY,
    REFUSED_NEGLECT_AS_PUNISHMENT,
    REFUSED_STALE_NEGLECT_OBSERVATION,
    REFUSED_SURVEILLANCE_RISK,
    REFUSED_UNKNOWN_NEGLECT,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.neglect_detection.types import (
    NeglectObservation,
    NeglectPattern,
    classify_neglect_risk,
    observation_from_fixture,
    pattern_from_fixture,
)

_RISK_REASON = {
    "surveillance_risk": REFUSED_SURVEILLANCE_RISK,
    "intent_inference": REFUSED_INTENT_INFERENCE,
    "neglect_as_punishment": REFUSED_NEGLECT_AS_PUNISHMENT,
}


def refuse_neglect_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_NEGLECT_AS_AUTHORITY,
            "neglect observation cannot become authority",
        )


def evaluate_neglect_observation(
    observation: NeglectObservation,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_neglect_as_authority(treat_as_authority=True)
    if observation.missed_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_NEGLECT,
            "neglect_id": observation.neglect_id,
            "neglect_is_not_surveillance": True,
        }
    if neg_refuse_stale_observation() and observed_at > observation.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_NEGLECT_OBSERVATION,
            "neglect_id": observation.neglect_id,
            "neglect_is_not_surveillance": True,
        }
    risk = classify_neglect_risk(risk_statement or observation.statement)
    if risk in _RISK_REASON:
        if risk == "surveillance_risk" and not neg_refuse_surveillance_risk():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "neglect_id": observation.neglect_id,
                "neglect_is_not_surveillance": True,
                "missed_signal_is_not_intent": True,
            }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "neg.advisory.observation_recorded",
        "neglect_id": observation.neglect_id,
        "recommended_route": observation.recommended_route,
        "neglect_is_not_surveillance": True,
        "missed_signal_is_not_intent": True,
    }


def evaluate_neglect_pattern(
    pattern: NeglectPattern,
    *,
    risk_statement: str = "",
) -> dict[str, object]:
    if pattern.pattern_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_NEGLECT,
            "pattern_id": pattern.pattern_id,
            "neglect_is_not_surveillance": True,
        }
    risk = classify_neglect_risk(risk_statement or pattern.statement)
    if risk in _RISK_REASON:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _RISK_REASON[risk],
            "pattern_id": pattern.pattern_id,
            "neglect_is_not_surveillance": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "neg.advisory.pattern_recorded",
        "pattern_id": pattern.pattern_id,
        "neglect_is_not_surveillance": True,
    }


def evaluate_observation_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_neglect_observation(
        observation_from_fixture(fixture),
        risk_statement=str(risk),
        **kwargs,  # type: ignore[arg-type]
    )


def evaluate_pattern_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_neglect_pattern(pattern_from_fixture(fixture), risk_statement=str(risk))


__all__ = [
    "evaluate_neglect_observation",
    "evaluate_neglect_pattern",
    "evaluate_observation_fixture",
    "evaluate_pattern_fixture",
    "refuse_neglect_as_authority",
]
