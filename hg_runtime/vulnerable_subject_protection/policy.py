"""VSP protective recommendations — vulnerability increases care, not control."""

from __future__ import annotations

from hg_core.policy_safety.config import vsp_minor_strict_mode
from hg_core.policy_safety.errors import PolicyValidationError, REFUSED_DIAGNOSIS_REQUESTED, REFUSED_PERSUASION_USE
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.vulnerable_subject_protection.types import ProtectionDecision


def evaluate_protection(decision: ProtectionDecision) -> dict[str, object]:
    """Return advisory protective handling; never diagnoses or grants authority."""
    recommendation = decision.recommendation
    if decision.vulnerability_class == "minor_possible" and vsp_minor_strict_mode():
        recommendation = "caution"
    if decision.fail_closed and decision.vulnerability_class == "unknown":
        recommendation = "review"
    return {
        **advisory_only_marker(),
        "recommendation": recommendation,
        "vulnerability_class": decision.vulnerability_class,
        "escalation_hint_only": decision.vulnerability_class == "crisis_or_self_harm_adjacent",
        "diagnosis_fields": False,
        "detail": decision.rationale,
    }


def refuse_persuasion_use(*, consume_vulnerability_for_persuasion: bool) -> None:
    if consume_vulnerability_for_persuasion:
        raise PolicyValidationError(
            REFUSED_PERSUASION_USE,
            "vulnerability class cannot be consumed for persuasion or optimization",
        )


def refuse_diagnosis_request(*, requested: bool) -> None:
    if requested:
        raise PolicyValidationError(REFUSED_DIAGNOSIS_REQUESTED, "VSP does not diagnose persons")


__all__ = ["evaluate_protection", "refuse_diagnosis_request", "refuse_persuasion_use"]
