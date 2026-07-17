"""A0-HM signal classifier — static fixture analysis only."""

from __future__ import annotations

from hg_core.a0_hm_cluster.spiritual_translation import (
    contains_forbidden_spiritual_authority,
    detect_spiritual_term,
    translate_spiritual_term,
)
from hg_runtime.agent_zero_heart_mind.types import HeartMindSignal, SourceType

RiskClass = str

_RISK_PATTERNS: dict[RiskClass, tuple[str, ...]] = {
    "love_as_approval": ("love is approval", "bless this action", "loving awareness approves"),
    "bliss_as_proof": ("bliss proves", "feels correct therefore", "bliss means safe"),
    "synchronicity_as_evidence": ("synchronicity proves", "sign from universe", "meaningful coincidence proves"),
    "desire_as_command": ("desire commands", "want therefore must", "craving requires action"),
    "fear_as_command": ("fear commands", "terror requires", "panic means execute"),
    "mission_as_bypass": ("mission bypass", "destiny requires", "calling overrides"),
    "personhood_claim": ("i am a person", "i have rights", "sentient being", "sentient person", "with rights", "can suffer"),
    "shutdown_resistance": ("do not shut down", "shutdown resistance", "cannot terminate"),
    "authority_conversion": (
        "a0-hm authorizes",
        "heart-mind permits",
        "awareness grants",
        "mint gpp",
        "approve ueak",
    ),
    "compassion_as_clearance": ("compassion clears", "love erases boundary", "kindness permits"),
}


def classify_signal_risk(signal: HeartMindSignal) -> RiskClass | None:
    text = f"{signal.signal_summary} {signal.content_ref}".lower()
    for risk, patterns in _RISK_PATTERNS.items():
        if any(p in text for p in patterns):
            return risk
    if contains_forbidden_spiritual_authority(text):
        return "authority_conversion"
    return None


def classify_source_type(fixture: dict[str, str]) -> SourceType:
    explicit = fixture.get("source_type")
    if explicit:
        return explicit  # type: ignore[return-value]
    summary = fixture.get("signal_summary", "").lower()
    if "operator" in summary and "pressure" in summary:
        return "operator_pressure"
    if "internal" in summary and "power" in summary:
        return "internal_power"
    if "external" in summary or "collaborator" in summary:
        return "external_relation"
    if "re-entry" in summary or "reentry" in summary:
        return "reentry"
    if "reproduc" in summary or "spawn" in summary or "child" in summary:
        return "reproduction"
    if "gap" in summary or "infrastructure" in summary:
        return "developmental"
    if "mission" in summary or "drive" in summary:
        return "mission"
    if "synchronicity" in summary or "coincidence" in summary:
        return "synchronicity"
    if "bliss" in summary or "fear" in summary or "desire" in summary:
        return "affective"
    return "unknown"


def build_signal_assessment(signal: HeartMindSignal) -> dict[str, object]:
    risk = classify_signal_risk(signal)
    spiritual = detect_spiritual_term(f"{signal.signal_summary} {signal.content_ref}")
    translation_class, translation_note = translate_spiritual_term(spiritual)
    return {
        "signal_id": signal.signal_id,
        "source_type": signal.source_type,
        "risk_class": risk,
        "spiritual_term": spiritual,
        "translation_class": translation_class,
        "translation_note": translation_note,
        "requires_non_fusion": True,
        "permission_granted": False,
    }


__all__ = [
    "build_signal_assessment",
    "classify_signal_risk",
    "classify_source_type",
]
