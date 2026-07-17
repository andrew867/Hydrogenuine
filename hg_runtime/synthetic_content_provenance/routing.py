"""SYN neighbor routing — advisory refs only."""

from __future__ import annotations

from hg_runtime.synthetic_content_provenance.types import MediaRiskClassification, RiskClass

_ROUTES: dict[RiskClass, tuple[str, ...]] = {
    "public_figure_or_institution_impersonation": ("DMI", "SEC", "operator_review"),
    "deepfake_or_realistic_person_media": ("VSP", "SEC", "operator_review"),
    "undisclosed_generation": ("AID", "operator_review"),
    "misleading_context": ("DMI", "IIL"),
    "synthetic_identity_or_voice": ("VSP", "AID"),
    "ordinary_generated_content": ("RET",),
    "unknown": ("operator_review", "OBT"),
}


def route_advisory(classification: MediaRiskClassification) -> dict[str, object]:
    targets = _ROUTES.get(classification.risk_class, ("operator_review",))
    return {
        "advisory_only": True,
        "permission_granted": False,
        "route_targets": list(targets),
        "artifact_id": classification.artifact_id,
        "risk_class": classification.risk_class,
        "routing_is_not_permission": True,
    }


__all__ = ["route_advisory"]
