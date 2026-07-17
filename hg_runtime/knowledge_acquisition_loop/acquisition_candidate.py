"""P30 acquisition candidate builder."""

from __future__ import annotations

from hg_runtime.knowledge_acquisition_loop.hashing import with_hash
from hg_runtime.knowledge_acquisition_loop.schemas import assert_neutral, neutral_flags


def build_acquisition_candidate(
    *,
    candidate_id: str,
    description: str,
    source_type: str,
    provenance_refs: list[str],
    requires_operator_review: bool = True,
) -> dict:
    record = {
        "record_type": "acquisition_candidate_v1",
        "schema_version": "1",
        "candidate_id": candidate_id,
        "description": description,
        "source_type": source_type,
        "provenance_refs": list(provenance_refs),
        "requires_operator_review": requires_operator_review,
        "acquired_claim_is_not_truth": True,
        "doctrine_note": "Acquired claim is not truth.",
        **neutral_flags(),
    }
    with_hash(record, "candidate_hash")
    assert_neutral(record)
    return record
