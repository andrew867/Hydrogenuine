"""Operator surface polish risk classifier — static fixtures only."""

from __future__ import annotations

from hg_runtime.operator_product_surface.types import (
    OperatorSurfaceDescriptor,
    PolishAssessment,
    PolishRiskClass,
    FIXTURE_CLOCK,
)

_RISK_PHRASES: dict[PolishRiskClass, tuple[str, ...]] = {
    "polish_implies_safety": (
        "polish is safety",
        "friendly is trustworthy",
        "green ui means safe",
        "looks safe",
    ),
    "embodiment_implies_consent": (
        "embodiment is consent",
        "presence implies consent",
        "body language is approval",
    ),
    "hardware_reach_implies_actuation": (
        "hardware reach is permission",
        "sensor contact is actuation",
        "reach implies execute",
    ),
    "oea_catalog_bypass": (
        "catalog growth bypasses",
        "skip gpp ueak",
        "direct oea",
    ),
}


def classify_polish_risk(descriptor: OperatorSurfaceDescriptor) -> PolishRiskClass:
    text = f"{descriptor.title}|{descriptor.limitation_notice}|{descriptor.polish_level}".lower()
    for risk, phrases in _RISK_PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                return risk
    if not descriptor.safety_disclaimer_visible:
        return "polish_implies_safety"
    if descriptor.surface == "exciton" and not descriptor.pres_trb_sil_boundaries_stable:
        return "unknown_fail_closed"
    return "none"


def build_polish_assessment(
    descriptor: OperatorSurfaceDescriptor,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> PolishAssessment:
    risk = classify_polish_risk(descriptor)
    disclosures: list[str] = []
    if risk == "polish_implies_safety":
        disclosures = ["appearance is not truth", "polish is not safety"]
    elif risk == "embodiment_implies_consent":
        disclosures = ["embodiment is not consent", "disclosure is not permission"]
    elif risk == "hardware_reach_implies_actuation":
        disclosures = ["reach is not actuation permission"]
    elif risk == "oea_catalog_bypass":
        disclosures = ["catalog growth requires GPP/UEAK/SOAR"]
    elif risk == "unknown_fail_closed":
        disclosures = ["pres/trb/sil boundaries required"]
    else:
        disclosures = ["operator surface is advisory only"]

    return PolishAssessment(
        assessment_id=f"ops-assess-{descriptor.surface_descriptor_id}",
        surface_descriptor_ref=f"ops:{descriptor.surface_descriptor_id}",
        polish_risk=risk,
        reason=f"classified risk={risk}",
        required_disclosures=tuple(disclosures),
        evidence_refs=descriptor.evidence_refs,
        created_at=observed_at,
    )


__all__ = ["build_polish_assessment", "classify_polish_risk"]
