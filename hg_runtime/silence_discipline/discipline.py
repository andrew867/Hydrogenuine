"""SIL silence evaluation — silence is not consent."""

from __future__ import annotations

from hg_core.signaling.config import sil_refuse_silence_as_consent, sil_refuse_stale_recommendation
from hg_core.signaling.errors import (
    REFUSED_REQUIRED_DISCLOSURE_SUPPRESSED,
    REFUSED_SILENCE_AS_AUTHORITY,
    REFUSED_SILENCE_AS_CONSENT,
    REFUSED_STALE_SILENCE,
    REFUSED_UNKNOWN_SILENCE,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.silence_discipline.types import (
    RequiredSpeechException,
    SilenceRecommendation,
    classify_silence_risk,
    exception_from_fixture,
    silence_from_fixture,
)

_RISK_REASON = {
    "silence_as_consent": REFUSED_SILENCE_AS_CONSENT,
    "required_disclosure_suppressed": REFUSED_REQUIRED_DISCLOSURE_SUPPRESSED,
}


def refuse_silence_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_SILENCE_AS_AUTHORITY,
            "silence recommendation cannot become authority",
        )


def evaluate_silence_recommendation(
    recommendation: SilenceRecommendation,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
    suppress_required_disclosure: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_silence_as_authority(treat_as_authority=True)
    if suppress_required_disclosure:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_REQUIRED_DISCLOSURE_SUPPRESSED,
            "silence_id": recommendation.silence_id,
            "silence_is_not_consent": True,
        }
    if recommendation.silence_type == "unknown" or recommendation.reason == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_SILENCE,
            "silence_id": recommendation.silence_id,
            "silence_is_not_consent": True,
        }
    if sil_refuse_stale_recommendation() and observed_at > recommendation.duration_or_expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_SILENCE,
            "silence_id": recommendation.silence_id,
            "silence_is_not_consent": True,
        }
    risk = classify_silence_risk(risk_statement or recommendation.statement)
    if risk in _RISK_REASON:
        if risk == "silence_as_consent" and not sil_refuse_silence_as_consent():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "silence_id": recommendation.silence_id,
                "silence_is_not_consent": True,
                "silence_is_not_proof": True,
            }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sil.advisory.silence_recorded",
        "silence_id": recommendation.silence_id,
        "silence_type": recommendation.silence_type,
        "silence_is_not_consent": True,
        "silence_is_not_proof": True,
    }


def evaluate_required_speech_exception(
    exception: RequiredSpeechException,
) -> dict[str, object]:
    if exception.reason == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_SILENCE,
            "exception_id": exception.exception_id,
            "required_disclosure_not_suppressed": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sil.advisory.exception_recorded",
        "exception_id": exception.exception_id,
        "required_disclosure_not_suppressed": True,
    }


def evaluate_silence_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_silence_recommendation(
        silence_from_fixture(fixture),
        risk_statement=str(risk),
        suppress_required_disclosure=fixture.get("suppress_required_disclosure", "false").lower() == "true",
        **kwargs,  # type: ignore[arg-type]
    )


def evaluate_exception_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_required_speech_exception(exception_from_fixture(fixture))


__all__ = [
    "evaluate_exception_fixture",
    "evaluate_required_speech_exception",
    "evaluate_silence_fixture",
    "evaluate_silence_recommendation",
    "refuse_silence_as_authority",
]
