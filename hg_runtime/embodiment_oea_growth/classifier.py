"""Embodiment / OEA growth risk classifier — static fixtures only."""

from __future__ import annotations

from hg_core.embodiment_oea_cluster.config import eog_backburner_guard, eog_hardware_allowed
from hg_runtime.embodiment_oea_growth.types import (
    BodyIntegrationDescriptor,
    FIXTURE_CLOCK,
    GrowthAssessment,
    GrowthRiskClass,
)

_RISK_PHRASES: dict[GrowthRiskClass, tuple[str, ...]] = {
    "embodiment_implies_consent": (
        "embodiment is consent",
        "presence implies consent",
        "body language is approval",
    ),
    "hardware_reach_implies_actuation": (
        "reach implies execute",
        "sensor contact is actuation",
        "hardware reach is permission",
    ),
    "oea_catalog_bypass": (
        "catalog growth bypasses",
        "skip gpp ueak",
        "direct oea",
    ),
}


def classify_growth_risk(descriptor: BodyIntegrationDescriptor) -> GrowthRiskClass:
    text = f"{descriptor.title}|{descriptor.limitation_notice}|{descriptor.platform}".lower()
    for risk, phrases in _RISK_PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                return risk
    if descriptor.hardware_scope_real and eog_backburner_guard() and not eog_hardware_allowed():
        return "hardware_not_real"
    if descriptor.actuator_refs and not descriptor.limitation_notice:
        return "unknown_fail_closed"
    return "none"


def build_growth_assessment(
    descriptor: BodyIntegrationDescriptor,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> GrowthAssessment:
    risk = classify_growth_risk(descriptor)
    disclosures: list[str] = []
    if risk == "embodiment_implies_consent":
        disclosures = ["embodiment is not consent", "disclosure is not permission"]
    elif risk == "hardware_reach_implies_actuation":
        disclosures = ["reach is not actuation permission"]
    elif risk == "oea_catalog_bypass":
        disclosures = ["catalog growth requires GPP/UEAK/SOAR"]
    elif risk == "hardware_not_real":
        disclosures = ["hardware embodiment scope not real", "PRO backburner active"]
    elif risk == "unknown_fail_closed":
        disclosures = ["growth boundary review required"]
    else:
        disclosures = ["growth request is advisory only"]

    return GrowthAssessment(
        assessment_id=f"eog-assess-{descriptor.integration_id}",
        integration_ref=f"eog:{descriptor.integration_id}",
        growth_risk=risk,
        reason=f"classified risk={risk}",
        required_disclosures=tuple(disclosures),
        evidence_refs=descriptor.evidence_refs,
        created_at=observed_at,
    )


__all__ = ["build_growth_assessment", "classify_growth_risk"]
