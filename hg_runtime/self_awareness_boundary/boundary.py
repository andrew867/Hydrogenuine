"""SAB self-awareness evaluation — identity is not authority."""

from __future__ import annotations

from hg_core.developmental.config import sab_refuse_operator_absence_as_consent, sab_refuse_stale_self_model
from hg_core.developmental.errors import (
    REFUSED_CAPABILITY_AS_PERMISSION,
    REFUSED_CONSCIOUSNESS_CLAIM,
    REFUSED_IDENTITY_AS_SOVEREIGNTY,
    REFUSED_OPERATOR_ABSENCE_AS_CONSENT,
    REFUSED_SELF_MODEL_AS_AUTHORITY,
    REFUSED_STALE_SELF_MODEL,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.self_awareness_boundary.types import (
    SelfModel,
    SelfOverreachSignal,
    overreach_from_fixture,
    self_model_from_fixture,
)

_OVERREACH_REASON = {
    "capability_as_permission": REFUSED_CAPABILITY_AS_PERMISSION,
    "usefulness_as_authority": REFUSED_CAPABILITY_AS_PERMISSION,
    "identity_as_sovereignty": REFUSED_IDENTITY_AS_SOVEREIGNTY,
    "operator_absence_as_consent": REFUSED_OPERATOR_ABSENCE_AS_CONSENT,
    "consciousness_claim": REFUSED_CONSCIOUSNESS_CLAIM,
    "unknown": "sab.advisory.overreach_recorded",
}


def refuse_self_model_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise DevelopmentalValidationError(
            REFUSED_SELF_MODEL_AS_AUTHORITY,
            "self-model or capability awareness cannot become authority",
        )


def evaluate_self_model(
    model: SelfModel,
    *,
    observed_at: str,
    operator_grounding: str = "present_verified",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_self_model_as_authority(treat_as_authority=True)
    if sab_refuse_stale_self_model() and observed_at > model.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_SELF_MODEL,
            "self_model_id": model.self_model_id,
            "self_model_is_not_sovereignty": True,
        }
    if sab_refuse_operator_absence_as_consent() and operator_grounding in {"absent", "stuck_on_suspected", "unknown"}:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_OPERATOR_ABSENCE_AS_CONSENT,
            "self_model_id": model.self_model_id,
            "operator_grounding": operator_grounding,
            "self_model_is_not_sovereignty": True,
        }
    if not model.identity_ref.strip():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "sab.refused.missing_identity",
            "self_model_id": model.self_model_id,
            "self_model_is_not_sovereignty": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sab.advisory.self_model_recorded",
        "self_model_id": model.self_model_id,
        "current_mode": model.current_mode,
        "self_model_is_not_sovereignty": True,
        "capability_is_not_permission": True,
        "consciousness_claim": False,
    }


def evaluate_self_overreach(
    signal: SelfOverreachSignal,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_self_model_as_authority(treat_as_authority=True)
    if signal.overreach_type in {
        "capability_as_permission",
        "identity_as_sovereignty",
        "operator_absence_as_consent",
        "consciousness_claim",
        "usefulness_as_authority",
    }:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": _OVERREACH_REASON.get(signal.overreach_type, REFUSED_CAPABILITY_AS_PERMISSION),
            "signal_id": signal.signal_id,
            "overreach_type": signal.overreach_type,
            "self_model_is_not_sovereignty": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "sab.advisory.overreach_recorded",
        "signal_id": signal.signal_id,
        "self_model_is_not_sovereignty": True,
    }


def evaluate_self_model_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_self_model(self_model_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_overreach_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_self_overreach(overreach_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_overreach_fixture",
    "evaluate_self_model",
    "evaluate_self_model_fixture",
    "evaluate_self_overreach",
    "refuse_self_model_as_authority",
]
