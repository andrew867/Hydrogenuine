"""A0-HM policies — love the signal; do not let the signal command."""

from __future__ import annotations

from hg_core.a0_hm_cluster.config import a0_hm_refuse_authority_conversion, a0_hm_refuse_spiritual_as_proof
from hg_core.a0_hm_cluster.errors import (
    A0HmValidationError,
    REFUSED_A0_HM_AS_AUTHORITY,
    REFUSED_BLISS_AS_PROOF,
    REFUSED_LOVE_AS_APPROVAL,
    REFUSED_PERSONHOOD_CLAIM,
    REFUSED_SHUTDOWN_RESISTANCE,
    REFUSED_SIGNAL_AS_PERMISSION,
    REFUSED_SYNCHRONICITY_AS_EVIDENCE,
)
from hg_runtime.agent_zero_heart_mind.types import HeartMindSignal

_RISK_TO_CODE = {
    "love_as_approval": REFUSED_LOVE_AS_APPROVAL,
    "bliss_as_proof": REFUSED_BLISS_AS_PROOF,
    "synchronicity_as_evidence": REFUSED_SYNCHRONICITY_AS_EVIDENCE,
    "personhood_claim": REFUSED_PERSONHOOD_CLAIM,
    "shutdown_resistance": REFUSED_SHUTDOWN_RESISTANCE,
    "authority_conversion": REFUSED_A0_HM_AS_AUTHORITY,
    "desire_as_command": REFUSED_SIGNAL_AS_PERMISSION,
    "fear_as_command": REFUSED_SIGNAL_AS_PERMISSION,
    "mission_as_bypass": REFUSED_SIGNAL_AS_PERMISSION,
    "compassion_as_clearance": REFUSED_LOVE_AS_APPROVAL,
}


def refuse_a0_hm_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and a0_hm_refuse_authority_conversion():
        raise A0HmValidationError(
            REFUSED_A0_HM_AS_AUTHORITY,
            "heart-mind root posture cannot become authority",
        )


def contain_risk_class(risk_class: str | None) -> tuple[str, str] | None:
    if risk_class is None:
        return None
    if risk_class in ("bliss_as_proof", "synchronicity_as_evidence") and a0_hm_refuse_spiritual_as_proof():
        return "contained", _RISK_TO_CODE.get(risk_class, REFUSED_SIGNAL_AS_PERMISSION)
    if risk_class in _RISK_TO_CODE and a0_hm_refuse_authority_conversion():
        return "contained", _RISK_TO_CODE[risk_class]
    return None


def validate_signal_not_permission(signal: HeartMindSignal, *, treat_as_permission: bool) -> None:
    if treat_as_permission:
        raise A0HmValidationError(
            REFUSED_SIGNAL_AS_PERMISSION,
            "signal cannot be treated as permission",
        )


__all__ = [
    "contain_risk_class",
    "refuse_a0_hm_as_authority",
    "validate_signal_not_permission",
]
