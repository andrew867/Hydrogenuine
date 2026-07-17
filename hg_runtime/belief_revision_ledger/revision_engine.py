"""Belief revision engine.

Drives evidence-bound, provisional belief-state transitions. Supporting
evidence can only promote a claim to PROVISIONALLY_SUPPORTED — never to truth or
certainty. Contradicting evidence opens a contradiction (and, after prior
support, a retraction path). Every transition is recorded as an append-only
revision record.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.belief_state import build_belief_state
from hg_runtime.belief_revision_ledger.contradiction_detector import build_contradiction_record
from hg_runtime.belief_revision_ledger.evidence_receipt import (
    build_synthetic_evidence_receipt,
    validate_evidence_receipt,
)
from hg_runtime.belief_revision_ledger.provenance import build_provenance_chain
from hg_runtime.belief_revision_ledger.retraction import build_retraction_record
from hg_runtime.belief_revision_ledger.schemas import (
    BELIEF_CONTRADICTED,
    BELIEF_INSUFFICIENT,
    BELIEF_PROVISIONALLY_SUPPORTED,
    BELIEF_RETRACTED,
    BELIEF_REVISION_RECORD_SCHEMA,
    BELIEF_UNVERIFIED,
    BeliefRevisionError,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def transition(current_status: str, stance: str) -> tuple[str, str]:
    """Pure belief-status transition. Returns (new_status, revision_reason)."""
    if stance == "SUPPORTS":
        if current_status in (BELIEF_UNVERIFIED, BELIEF_INSUFFICIENT):
            return BELIEF_PROVISIONALLY_SUPPORTED, "SUPPORTING_EVIDENCE_RECEIVED"
        if current_status == BELIEF_CONTRADICTED:
            return BELIEF_PROVISIONALLY_SUPPORTED, "CONFLICT_REOPENED"
        return BELIEF_PROVISIONALLY_SUPPORTED, "SUPPORTING_EVIDENCE_RECEIVED"
    if stance == "CONTRADICTS":
        return BELIEF_CONTRADICTED, "CONTRADICTING_EVIDENCE_RECEIVED"
    if stance == "INSUFFICIENT":
        if current_status == BELIEF_UNVERIFIED:
            return BELIEF_INSUFFICIENT, "INSUFFICIENT_EVIDENCE"
        return current_status, "INSUFFICIENT_EVIDENCE"
    raise BeliefRevisionError("invalid_stance")


def build_revision_record(claim_id: str, previous: str, new: str, evidence_ids: list[str], reason: str) -> dict:
    record = {
        "schema": BELIEF_REVISION_RECORD_SCHEMA,
        "revision_id": f"rev-{claim_id}-{previous}->{new}-{canonical_hash({'e': sorted(evidence_ids), 'r': reason})[:12]}",
        "claim_id": claim_id,
        "previous_belief_status": previous,
        "new_belief_status": new,
        "evidence_receipt_ids": sorted(evidence_ids),
        "revision_reason": reason,
        "truth_claimed": False,
        "certainty_claimed": False,
        **neutral_flags(),
    }
    record["revision_hash"] = canonical_hash(record)
    return record


def process_claim_evidence(claim: dict, task: dict, stances: list[str], source_matrix_ids: list[str]) -> dict:
    """Apply an ordered sequence of synthetic evidence stances to a single claim."""
    claim_id = claim["claim_id"]
    claim_hash = claim.get("claim_hash", "")
    status = BELIEF_UNVERIFIED
    supporting: list[str] = []
    contradicting: list[str] = []
    evidence_receipts: list[dict] = []
    revisions: list[dict] = []
    contradictions: list[dict] = []
    retractions: list[dict] = []
    retraction_triggered = False

    for ordinal, stance in enumerate(stances):
        receipt = build_synthetic_evidence_receipt(
            task=task, target_claim_id=claim_id, stance=stance, ordinal=ordinal
        )
        validate_evidence_receipt(receipt)
        evidence_receipts.append(receipt)
        if stance == "SUPPORTS":
            supporting.append(receipt["evidence_receipt_id"])
        elif stance == "CONTRADICTS":
            contradicting.append(receipt["evidence_receipt_id"])

        prev = status
        status, reason = transition(prev, stance)
        revisions.append(build_revision_record(claim_id, prev, status, [receipt["evidence_receipt_id"]], reason))

        if prev == BELIEF_PROVISIONALLY_SUPPORTED and status == BELIEF_CONTRADICTED:
            retraction_triggered = True
        if prev != BELIEF_CONTRADICTED and status == BELIEF_CONTRADICTED:
            contradictions.append(build_contradiction_record(
                claim_id=claim_id,
                supporting_ids=supporting,
                contradicting_ids=contradicting,
                status="RETRACTION_RECOMMENDED" if retraction_triggered else "OPEN",
            ))

    # Build provenance chain (revision ids known) before final state.
    provenance_chain = build_provenance_chain(
        claim=claim,
        verification_task_ids=[task.get("task_id", "")],
        evidence_receipt_ids=[r["evidence_receipt_id"] for r in evidence_receipts],
        revision_ids=[r["revision_id"] for r in revisions],
        source_matrix_ids=source_matrix_ids,
    )

    retraction_record = None
    if retraction_triggered:
        prev = status  # CONTRADICTED
        status = BELIEF_RETRACTED
        revisions.append(build_revision_record(
            claim_id, prev, status, contradicting, "RETRACTION_REQUIRED"
        ))
        retraction_record = build_retraction_record(
            claim_id=claim_id,
            previous_belief_state_id=f"belief-{claim_id}",
            new_belief_state_id=f"belief-{claim_id}-retracted",
            triggering_evidence_receipt_ids=contradicting,
            reason="Contradicting evidence superseded prior provisional support.",
        )
        retractions.append(retraction_record)
        # Provenance chain re-derived to include the retraction revision.
        provenance_chain = build_provenance_chain(
            claim=claim,
            verification_task_ids=[task.get("task_id", "")],
            evidence_receipt_ids=[r["evidence_receipt_id"] for r in evidence_receipts],
            revision_ids=[r["revision_id"] for r in revisions],
            source_matrix_ids=source_matrix_ids,
        )

    state_id = f"belief-{claim_id}-retracted" if retraction_triggered else f"belief-{claim_id}"
    belief_state = build_belief_state(
        claim_id=claim_id,
        claim_hash=claim_hash,
        belief_status=status,
        supporting_ids=supporting,
        contradicting_ids=contradicting,
        provenance_chain_hash=provenance_chain["chain_hash"],
        state_id=state_id,
    )

    return {
        "belief_state": belief_state,
        "revisions": revisions,
        "contradictions": contradictions,
        "retractions": retractions,
        "evidence_receipts": evidence_receipts,
        "provenance_chain": provenance_chain,
        "final_status": status,
    }
