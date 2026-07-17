"""Provisional, evidence-bound belief state records.

A belief state is not truth. Promoted states (provisionally supported,
contradicted, retracted) require a provenance chain hash.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.schemas import (
    BELIEF_STATE_RECORD_SCHEMA,
    BELIEF_UNVERIFIED,
    BeliefRevisionError,
    PROMOTED_STATUSES,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_belief_state(
    *,
    claim_id: str,
    claim_hash: str,
    belief_status: str,
    supporting_ids: list[str],
    contradicting_ids: list[str],
    provenance_chain_hash: str | None,
    state_id: str | None = None,
) -> dict:
    if belief_status in PROMOTED_STATUSES and not provenance_chain_hash:
        raise BeliefRevisionError("provenance_chain_required_for_promoted_state")
    state = {
        "schema": BELIEF_STATE_RECORD_SCHEMA,
        "belief_state_id": state_id or f"belief-{claim_id}",
        "claim_id": claim_id,
        "claim_hash": claim_hash,
        "belief_status": belief_status,
        "supporting_evidence_receipt_ids": sorted(supporting_ids),
        "contradicting_evidence_receipt_ids": sorted(contradicting_ids),
        "provenance_chain_hash": provenance_chain_hash or "",
        "truth_claimed": False,
        "certainty_claimed": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    state["state_hash"] = canonical_hash(state)
    return state


def unverified_state(claim_id: str, claim_hash: str) -> dict:
    return build_belief_state(
        claim_id=claim_id,
        claim_hash=claim_hash,
        belief_status=BELIEF_UNVERIFIED,
        supporting_ids=[],
        contradicting_ids=[],
        provenance_chain_hash=None,
    )
