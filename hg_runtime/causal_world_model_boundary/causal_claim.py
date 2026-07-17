"""Causal claim extraction from provenance-bound belief states.

A causal claim merely *describes* causal-looking language in a supported belief
state. It claims no truth and no causality-as-fact.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    CAUSAL_CLAIM_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_causal_claim(
    *,
    belief_state: dict,
    evidence_ids: list[str],
    causal_language: bool,
    correlation_language: bool,
    mechanism_language: bool,
) -> dict:
    claim_id = belief_state.get("claim_id", "claim-unknown")
    text = f"[causal-claim derived from belief {belief_state.get('belief_state_id')} ({belief_state.get('belief_status')})]"
    record = {
        "schema": CAUSAL_CLAIM_RECORD_SCHEMA,
        "causal_claim_id": f"causal-claim-{claim_id}",
        "source_claim_id": claim_id,
        "source_belief_state_id": belief_state.get("belief_state_id", ""),
        "source_evidence_receipt_ids": sorted(evidence_ids),
        "claim_hash": belief_state.get("claim_hash", ""),
        "claim_text_redacted": text,
        "causal_language_detected": bool(causal_language),
        "correlation_language_detected": bool(correlation_language),
        "mechanism_language_detected": bool(mechanism_language),
        "truth_claimed": False,
        "causality_claimed_as_fact": False,
        "authority_granted": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
