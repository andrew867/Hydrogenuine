"""Review policy for contradictions.

Only operators and gates may resolve contradictions.
Models and systems cannot resolve contradictions.
"""

from __future__ import annotations


def can_resolve(resolver: str) -> bool:
    """True only if resolver is 'operator' or 'gate'."""
    return resolver in ("operator", "gate")


def requires_source(contradiction_type: str) -> bool:
    """True for contradiction types that require a source to resolve."""
    return contradiction_type in {
        "source_vs_source",
        "model_vs_source",
        "source_vs_memory",
        "evidence_gap_vs_claim",
    }


def auto_severity(contradiction_type: str) -> str:
    """Determine automatic severity for a contradiction type.

    claim_vs_boundary -> "critical"
    consensus_without_evidence -> "high"
    Others -> "medium"
    """
    if contradiction_type == "claim_vs_boundary":
        return "critical"
    if contradiction_type == "consensus_without_evidence":
        return "high"
    return "medium"
