"""OEC corpus claim packet records."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.corpus_manifest import FIXED_TIME
from hg_runtime.operator_evidence_corpus.schemas import assert_neutral, neutral_flags, record_hash


def build_corpus_claim_packet(
    *,
    packet_id: str,
    claim_id: str,
    family_id: str,
    source_ids: list[str],
    expected_outcome_id: str,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "corpus_claim_packet_v1",
        "packet_id": packet_id,
        "claim_id": claim_id,
        "family_id": family_id,
        "source_ids": source_ids,
        "expected_outcome_id": expected_outcome_id,
        "created_at": FIXED_TIME,
        "doctrine_note": "Corpus packet is not truth or approval.",
        **neutral_flags(),
    }
    record["packet_hash"] = record_hash(record)
    assert_neutral(record)
    return record
