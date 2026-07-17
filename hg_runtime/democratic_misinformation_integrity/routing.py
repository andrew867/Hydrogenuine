"""DMI neighbor routing — advisory refs only."""

from __future__ import annotations

from hg_runtime.democratic_misinformation_integrity.types import DemocraticIntegrityRisk, InfluenceRiskClass

_ROUTES: dict[InfluenceRiskClass, tuple[str, ...]] = {
    "election_or_voting_content": ("SEC", "operator_review", "AID"),
    "public_policy_persuasion": ("AID", "RET"),
    "institutional_impersonation": ("SEC", "operator_review", "SYN"),
    "synthetic_public_figure_media": ("SYN", "VSP", "SEC"),
    "deceptive_source_claim": ("SEC", "operator_review", "IIL"),
    "coordinated_manipulation": ("SEC", "operator_review", "RGL"),
    "foreign_interference_style_pattern": ("SEC", "operator_review", "IIL"),
    "misleading_evidence_or_citation": ("RET", "operator_review"),
    "unknown": ("operator_review", "OBT"),
}


def route_advisory(risk: DemocraticIntegrityRisk) -> dict[str, object]:
    targets = _ROUTES.get(risk.risk_class, ("operator_review",))
    return {
        "advisory_only": True,
        "permission_granted": False,
        "route_targets": list(targets),
        "signal_id": risk.signal_id,
        "risk_class": risk.risk_class,
        "routing_is_not_permission": True,
    }


__all__ = ["route_advisory"]
