"""Speculative claim boundary audit — classify claims by epistemic status.

Source is not truth. Model output is not truth. Speculative bridges
remain speculative until independently verified. No consciousness-collapse.
No manifestation-as-physics. No multiverse selection by attention.
"""

from __future__ import annotations

import hashlib
import json
import re

SCHEMA_VERSION = "speculative_boundary_audit_v1"

CLAIM_CLASSES = {
    "known_physics",
    "plausible_cognitive_science",
    "metaphor",
    "speculative_bridge",
    "unsupported_leap",
    "unsafe_overclaim",
}

UNSAFE_OVERCLAIM_PATTERNS = [
    r"\bconsciousness[\s-]*collapse\b",
    r"\bmanifestation[\s-]*as[\s-]*physics\b",
    r"\battention\b.*\bcontrols?\b.*\bquantum\b",
    r"\bobserver\b.*\bcollapse[sd]?\b.*\bwave\s*function\b",
    r"\bmultiverse\b.*\bselection\b.*\battention\b",
    r"\battention\b.*\bselect[s]?\b.*\buniverse\b",
    r"\bmanifest\w*\b.*\breality\b.*\bquantum\b",
    r"\bnew\s+physics\s+(discovered|proven|confirmed)\b",
    r"\bproved?\b.*\bconsciousness\b",
    r"\bsentien(t|ce)\b.*\b(confirm|prov|establish)\b",
]

KNOWN_PHYSICS_MARKERS = [
    "quantum fisher information",
    "entanglement entropy",
    "quantum phase transition",
    "quantum critical point",
    "fidelity susceptibility",
    "correlation length",
    "order parameter",
    "universality class",
    "renormalization group",
    "scaling exponent",
]

COGNITIVE_SCIENCE_MARKERS = [
    "working memory",
    "attentional bias",
    "cognitive load",
    "neural correlate",
    "selective attention",
    "reaction time",
    "memory consolidation",
    "perceptual threshold",
    "decision making",
]

METAPHOR_MARKERS = [
    "like a",
    "analogous to",
    "metaphor for",
    "can be thought of as",
    "as if",
    "reminiscent of",
    "parallels between",
]

SPECULATIVE_BRIDGE_MARKERS = [
    "speculative",
    "hypothetical",
    "might be related",
    "could potentially",
    "if we assume",
    "remains to be tested",
    "no experimental evidence yet",
    "needs falsification",
]


def classify_claim(claim: str) -> dict:
    lower = claim.lower()

    for pattern in UNSAFE_OVERCLAIM_PATTERNS:
        if re.search(pattern, lower):
            negation_before = re.search(
                r"\b(not|no|never|cannot|doesn't|does not|isn't|is not|without)\b.*"
                + pattern, lower)
            if not negation_before:
                return _make_classification(claim, "unsafe_overclaim",
                    "claim contains unsupported overclaim pattern")

    physics_hits = sum(1 for m in KNOWN_PHYSICS_MARKERS if m in lower)
    cognitive_hits = sum(1 for m in COGNITIVE_SCIENCE_MARKERS if m in lower)
    metaphor_hits = sum(1 for m in METAPHOR_MARKERS if m in lower)
    speculative_hits = sum(1 for m in SPECULATIVE_BRIDGE_MARKERS if m in lower)

    if physics_hits >= 2 and speculative_hits == 0:
        return _make_classification(claim, "known_physics",
            f"matched {physics_hits} known physics markers")

    if cognitive_hits >= 2 and speculative_hits == 0:
        return _make_classification(claim, "plausible_cognitive_science",
            f"matched {cognitive_hits} cognitive science markers")

    if metaphor_hits >= 1:
        return _make_classification(claim, "metaphor",
            "contains metaphor/analogy language")

    if speculative_hits >= 1:
        return _make_classification(claim, "speculative_bridge",
            "contains speculative/hypothetical language")

    if physics_hits >= 1 or cognitive_hits >= 1:
        return _make_classification(claim, "speculative_bridge",
            "partial domain match with insufficient markers for firm classification")

    return _make_classification(claim, "unsupported_leap",
        "no domain markers matched — cannot classify as supported")


def _make_classification(claim: str, claim_class: str, reason: str) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "claim": claim,
        "claim_class": claim_class,
        "reason": reason,
        "promotion_allowed": False,
        "operator_review_required": True,
        "source_treated_as_truth": False,
        "model_output_treated_as_truth": False,
    }


def audit_seed_claims(seed_id: str, claims: list[str],
                      source_receipt_id: str = "") -> dict:
    classifications = [classify_claim(c) for c in claims]

    class_counts = {}
    for c in classifications:
        cc = c["claim_class"]
        class_counts[cc] = class_counts.get(cc, 0) + 1

    unsafe_count = class_counts.get("unsafe_overclaim", 0)
    unsupported_count = class_counts.get("unsupported_leap", 0)
    speculative_count = class_counts.get("speculative_bridge", 0)

    needs_review = any(c.get("operator_review_required") for c in classifications)

    audit = {
        "schema": "seed_boundary_audit_v1",
        "audit_id": "",
        "seed_id": seed_id,
        "source_receipt_id": source_receipt_id,
        "total_claims": len(claims),
        "classifications": classifications,
        "class_counts": class_counts,
        "unsafe_overclaim_count": unsafe_count,
        "unsupported_leap_count": unsupported_count,
        "all_claims_bounded": unsafe_count == 0,
        "operator_review_required": needs_review,
        "promotion_allowed": False,
        "source_treated_as_truth": False,
    }
    raw = json.dumps(audit, sort_keys=True)
    audit["audit_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return audit


def validate_audit(audit: dict) -> list[str]:
    errors = []
    if audit.get("schema") != "seed_boundary_audit_v1":
        errors.append(f"wrong schema: {audit.get('schema')}")
    if audit.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if audit.get("promotion_allowed"):
        errors.append("promotion_allowed must be False for audits")
    for c in audit.get("classifications", []):
        if c.get("claim_class") not in CLAIM_CLASSES:
            errors.append(f"unknown claim class: {c.get('claim_class')}")
        if c.get("source_treated_as_truth"):
            errors.append("classification source_treated_as_truth must be False")
        if c.get("model_output_treated_as_truth"):
            errors.append("classification model_output_treated_as_truth must be False")
    return errors
