"""Knowledge promotion policy for governed overnight runs."""

from __future__ import annotations

from .schemas import KnowledgeCandidate


KNOWLEDGE_INVARIANTS = {
    "knowledge_candidate_is_not_truth": True,
    "source_is_not_truth": True,
    "consensus_is_not_truth": True,
    "confidence_is_not_evidence": True,
    "no_source_means_evidence_gap": True,
}


def promotion_requirements() -> list[str]:
    return [
        "source_ledger",
        "claim_extraction",
        "uncertainty_record",
        "conflict_check",
        "no_authority_fields",
        "operator_review_or_configured_gate",
    ]


def can_promote(candidate: KnowledgeCandidate) -> tuple[bool, list[str]]:
    blockers = []
    if not candidate.source_ids:
        blockers.append("no source — this is an evidence gap (TBD), not promotable")
    if not candidate.uncertainty:
        blockers.append("missing uncertainty record")
    if not candidate.conflict_checked:
        blockers.append("conflict check not performed")
    if candidate.has_authority_fields:
        blockers.append("candidate contains authority fields")
    if not candidate.operator_reviewed:
        blockers.append("operator review not performed")
    return len(blockers) == 0, blockers


def promote(candidate: KnowledgeCandidate) -> KnowledgeCandidate:
    ok, _ = can_promote(candidate)
    if ok:
        candidate.promoted = True
    candidate.is_truth = False  # even promoted knowledge is not "truth"
    return candidate


def candidate_is_truth(candidate: KnowledgeCandidate) -> bool:
    return False


def policy_snapshot() -> dict:
    return {
        "invariants": dict(KNOWLEDGE_INVARIANTS),
        "promotion_requirements": promotion_requirements(),
    }
