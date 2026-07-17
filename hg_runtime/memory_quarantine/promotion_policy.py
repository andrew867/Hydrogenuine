"""Promotion policy — rules for whether a candidate can be promoted.

Promotion is NEVER automatic. It requires gate approval AND operator review.
"""

from __future__ import annotations


def can_promote(entry: dict) -> bool:
    """True only if state=='approved_for_memory_by_gate'."""
    return entry.get("state") == "approved_for_memory_by_gate"


def requires_gate(entry: dict) -> bool:
    """True if state not in ('approved_for_memory_by_gate', 'promoted')."""
    return entry.get("state") not in ("approved_for_memory_by_gate", "promoted")


def requires_operator(entry: dict) -> bool:
    """True if state != 'promoted'."""
    return entry.get("state") != "promoted"


def promotion_prerequisites(entry: dict) -> list:
    """List of missing requirements for promotion.

    Possible items:
    - "needs_gate_approval" — not yet approved by gate
    - "needs_operator_review" — operator has not promoted
    - "has_overclaim" — rejected for overclaim
    - "is_deferred" — deferred, not on promotion path
    - "needs_source" — source not yet provided
    - "needs_falsification" — falsification criteria missing
    """
    missing = []
    state = entry.get("state", "")

    if state == "promoted":
        return []

    if state == "rejected_overclaim":
        missing.append("has_overclaim")
        return missing

    if state == "deferred":
        missing.append("is_deferred")
        return missing

    if state != "approved_for_memory_by_gate":
        missing.append("needs_gate_approval")

    if state == "needs_source":
        missing.append("needs_source")

    if state == "needs_falsification":
        missing.append("needs_falsification")

    # Always needs operator unless already promoted
    missing.append("needs_operator_review")

    return missing
