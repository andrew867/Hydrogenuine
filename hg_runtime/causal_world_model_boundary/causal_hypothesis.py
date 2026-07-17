"""Provisional causal hypotheses.

A causal hypothesis is not causal truth. Every hypothesis is provisional,
provenance-bound, and carries an uncertainty level. Contradicted seeds yield
CONTRADICTED hypotheses so the conflict stays visible.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    BELIEF_TO_HYPOTHESIS_STATUS,
    CAUSAL_HYPOTHESIS_RECORD_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash

_UNCERTAINTY_BY_STATUS = {
    "PROPOSED": "MEDIUM",
    "INSUFFICIENT_EVIDENCE": "HIGH",
    "CONTRADICTED": "HIGH",
}


def build_causal_hypothesis(
    *,
    causal_claim: dict,
    belief_state: dict,
    provenance_chain_ids: list[str],
    supporting_ids: list[str],
    contradicting_ids: list[str],
) -> dict:
    belief_status = belief_state.get("belief_status", "INSUFFICIENT_EVIDENCE")
    status = BELIEF_TO_HYPOTHESIS_STATUS.get(belief_status, "INSUFFICIENT_EVIDENCE")
    claim_id = causal_claim["source_claim_id"]
    text = f"[causal-hypothesis from {causal_claim['causal_claim_id']} status={status}]"
    record = {
        "schema": CAUSAL_HYPOTHESIS_RECORD_SCHEMA,
        "hypothesis_id": f"hyp-{claim_id}",
        "source_causal_claim_ids": [causal_claim["causal_claim_id"]],
        "hypothesis_text_hash": canonical_hash({"text": text}),
        "hypothesis_text_redacted": text,
        "hypothesis_status": status,
        "provenance_chain_ids": sorted(provenance_chain_ids),
        "supporting_evidence_receipt_ids": sorted(supporting_ids),
        "contradicting_evidence_receipt_ids": sorted(contradicting_ids),
        "uncertainty_level": _UNCERTAINTY_BY_STATUS.get(status, "HIGH"),
        "causal_truth_claimed": False,
        "certainty_claimed": False,
        "intervention_authorized": False,
        "tools_authorized": False,
        **neutral_flags(),
    }
    record["hypothesis_hash"] = canonical_hash(record)
    return record
