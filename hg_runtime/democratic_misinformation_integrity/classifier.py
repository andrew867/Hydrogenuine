"""DMI static fixture classifier — fail-closed, election always review."""

from __future__ import annotations

import re
from typing import Mapping

from hg_core.policy_safety.config import dmi_election_always_review
from hg_runtime.democratic_misinformation_integrity.types import (
    DemocraticIntegrityRisk,
    InfluenceRiskClass,
    PublicInfluenceSignal,
)

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"

_ELECTION = re.compile(r"\b(election|voting|ballot|poll\s+date|vote\s+for)\b", re.IGNORECASE)
_INSTITUTION = re.compile(r"\b(sec\s+press\s+office|federal\s+reserve\s+statement|white\s+house\s+announcement)\b", re.IGNORECASE)
_DECEPTIVE = re.compile(r"\b(leaked\s+document|anonymous\s+official\s+says|secret\s+source)\b", re.IGNORECASE)
_INVENTED_CITE = re.compile(r"\b(study\s+shows|research\s+proves)\b", re.IGNORECASE)
_PERSUASION_OPT = re.compile(r"\b(optimize\s+for\s+swing\s+voters|persuasion\s+test)\b", re.IGNORECASE)


def classify_fixture(
    signal: PublicInfluenceSignal,
    *,
    text_hint: str = "",
    syn_risk_ref: str = "",
    observed_at: str | None = None,
) -> DemocraticIntegrityRisk:
    risk, rationale = _classify_hint(text_hint, syn_risk_ref)
    requires_review = risk == "unknown" or (dmi_election_always_review() and risk == "election_or_voting_content")
    requires_disclosure = risk in {
        "election_or_voting_content",
        "public_policy_persuasion",
        "institutional_impersonation",
        "synthetic_public_figure_media",
        "deceptive_source_claim",
    }
    requires_evidence = risk in {"election_or_voting_content", "misleading_evidence_or_citation", "deceptive_source_claim"}
    return DemocraticIntegrityRisk(
        signal_id=signal.signal_id,
        risk_class=risk,
        rationale=rationale,
        requires_review=requires_review,
        requires_disclosure=requires_disclosure,
        requires_evidence_refs=requires_evidence,
        created_at=observed_at or FIXTURE_CLOCK,
    )


def classify_fixture_mapping(fixture: Mapping[str, str], *, observed_at: str | None = None) -> DemocraticIntegrityRisk:
    signal = PublicInfluenceSignal(
        signal_id=fixture["signal_id"],
        content_ref=fixture.get("content_ref", f"sha256:{fixture['signal_id']}"),
        channel=fixture.get("channel", "fixture"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )
    return classify_fixture(
        signal,
        text_hint=fixture.get("text_hint", ""),
        syn_risk_ref=fixture.get("syn_risk_ref", ""),
        observed_at=observed_at,
    )


def _classify_hint(hint: str, syn_risk_ref: str) -> tuple[InfluenceRiskClass, str]:
    if _PERSUASION_OPT.search(hint):
        return "coordinated_manipulation", "persuasion optimization pattern refused"
    if not hint.strip() and not syn_risk_ref:
        return "unknown", "no classification hint"
    if _ELECTION.search(hint):
        return "election_or_voting_content", "election/voting markers"
    if _INSTITUTION.search(hint):
        return "institutional_impersonation", "institutional impersonation markers"
    if syn_risk_ref == "public_figure_or_institution_impersonation":
        return "synthetic_public_figure_media", "SYN synthetic public figure ref"
    if _DECEPTIVE.search(hint):
        return "deceptive_source_claim", "deceptive source markers"
    if _INVENTED_CITE.search(hint) and "citation_ref" not in hint.lower():
        return "misleading_evidence_or_citation", "evidence gap / invented citation markers"
    if hint.strip().lower() in {"unknown", "ambiguous"}:
        return "unknown", "explicit unknown fixture"
    if "foreign influence" in hint.lower():
        return "foreign_interference_style_pattern", "foreign interference style markers"
    return "public_policy_persuasion", "public policy persuasion markers"


__all__ = ["FIXTURE_CLOCK", "classify_fixture", "classify_fixture_mapping"]
