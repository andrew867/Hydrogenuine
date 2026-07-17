"""Mechanism proposals.

A mechanism proposal is not proof. It records a hypothesized mechanism that
still requires verification.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    MECHANISM_PROPOSAL_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_mechanism_proposal(*, hypothesis: dict, evidence_ids: list[str]) -> dict:
    text = f"[mechanism proposal for {hypothesis['hypothesis_id']}]"
    record = {
        "schema": MECHANISM_PROPOSAL_SCHEMA,
        "mechanism_id": f"mech-{hypothesis['hypothesis_id']}",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "mechanism_text_hash": canonical_hash({"text": text}),
        "mechanism_text_redacted": text,
        "source_evidence_receipt_ids": sorted(evidence_ids),
        "mechanism_is_proof": False,
        "requires_verification": True,
        "authority_granted": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record
