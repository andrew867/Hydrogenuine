"""Provenance chains linking claim, task, evidence, and revisions.

A provenance chain binds a belief state to its full evidentiary lineage so that
no belief is promoted without provenance.
"""

from __future__ import annotations

from hg_runtime.belief_revision_ledger.schemas import (
    PROVENANCE_CHAIN_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_provenance_chain(
    *,
    claim: dict,
    verification_task_ids: list[str],
    evidence_receipt_ids: list[str],
    revision_ids: list[str],
    source_matrix_ids: list[str],
) -> dict:
    claim_id = claim["claim_id"]
    chain = {
        "schema": PROVENANCE_CHAIN_SCHEMA,
        "provenance_chain_id": f"prov-{claim_id}",
        "claim_id": claim_id,
        "source_receipt_ids": sorted(filter(None, [claim.get("source_receipt_id")])),
        "source_matrix_ids": sorted(set(source_matrix_ids)),
        "source_verification_task_ids": sorted(set(verification_task_ids)),
        "evidence_receipt_ids": sorted(set(evidence_receipt_ids)),
        "revision_ids": list(revision_ids),
        **neutral_flags(),
    }
    chain["chain_hash"] = canonical_hash(chain)
    return chain
