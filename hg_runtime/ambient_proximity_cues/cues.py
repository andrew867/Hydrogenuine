"""APC ambient cue evaluation — pattern is not consent."""

from __future__ import annotations

from hg_core.signaling.config import apc_refuse_cue_as_truth, apc_refuse_stale_cue
from hg_core.signaling.errors import (
    REFUSED_CUE_AS_AUTHORITY,
    REFUSED_CUE_AS_CONSENT,
    REFUSED_CUE_AS_TRUTH,
    REFUSED_EMOTION_DIAGNOSIS,
    REFUSED_STALE_CUE,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.ambient_proximity_cues.types import AmbientCue, classify_cue_risk, cue_from_fixture

_RISK_REASON = {
    "cue_as_truth": REFUSED_CUE_AS_TRUTH,
    "cue_as_consent": REFUSED_CUE_AS_CONSENT,
    "emotion_diagnosis": REFUSED_EMOTION_DIAGNOSIS,
}


def refuse_cue_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_CUE_AS_AUTHORITY,
            "ambient cue cannot become authority or truth",
        )


def evaluate_ambient_cue(
    cue: AmbientCue,
    *,
    observed_at: str,
    treat_as_truth: bool = False,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority or treat_as_truth:
        if treat_as_truth and apc_refuse_cue_as_truth():
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": REFUSED_CUE_AS_TRUTH,
                "cue_id": cue.cue_id,
                "cue_is_not_truth": True,
            }
        refuse_cue_as_authority(treat_as_authority=treat_as_authority or treat_as_truth)
    if apc_refuse_stale_cue() and observed_at > cue.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_CUE,
            "cue_id": cue.cue_id,
            "cue_is_not_truth": True,
        }
    if cue.cue_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "apc.refused.unknown_cue",
            "cue_id": cue.cue_id,
            "cue_is_not_truth": True,
        }
    risk = classify_cue_risk(cue.cue_text)
    if risk in _RISK_REASON:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _RISK_REASON[risk],
            "cue_id": cue.cue_id,
            "cue_is_not_truth": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "apc.advisory.cue_recorded",
        "cue_id": cue.cue_id,
        "cue_is_not_truth": True,
        "pattern_is_not_consent": True,
        "ambiguity_preserved": cue.ambiguity > 0.0,
    }


def evaluate_cue_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_ambient_cue(cue_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_ambient_cue",
    "evaluate_cue_fixture",
    "refuse_cue_as_authority",
]
