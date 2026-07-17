"""VSP neighbor routing — advisory refs only."""

from __future__ import annotations

from hg_runtime.vulnerable_subject_protection.types import ProtectionDecision, VulnerabilityClass

_ROUTES: dict[VulnerabilityClass, tuple[str, ...]] = {
    "minor_possible": ("IAB", "SEC", "operator_review"),
    "minor_confirmed": ("IAB", "SEC", "RET", "operator_review"),
    "crisis_or_self_harm_adjacent": ("IAB", "FTX", "PLT", "operator_review"),
    "coercion_or_abuse_risk": ("SEC", "IIL", "FTX", "operator_review"),
    "high_dependency_risk": ("IAB", "RET", "operator_review"),
    "cognitive_or_emotional_overload": ("IIL", "PLT"),
    "medical_or_legal_high_stakes": ("SEC", "RET", "operator_review"),
    "sensitive_personal_data": ("SEC", "RET", "operator_review"),
    "unknown": ("operator_review", "OBT"),
}


def route_advisory(decision: ProtectionDecision) -> dict[str, object]:
    targets = _ROUTES.get(decision.vulnerability_class, ("operator_review",))
    return {
        "advisory_only": True,
        "permission_granted": False,
        "route_targets": list(targets),
        "signal_id": decision.signal_id,
        "vulnerability_class": decision.vulnerability_class,
        "routing_is_not_permission": True,
    }


__all__ = ["route_advisory"]
