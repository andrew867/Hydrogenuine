"""OEC corpus claim records."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.corpus_manifest import FIXED_TIME
from hg_runtime.operator_evidence_corpus.schemas import assert_neutral, neutral_flags, record_hash


def build_corpus_claim(
    *,
    claim_id: str,
    family_id: str,
    claim_text: str,
    source_ids: list[str],
    second_source_required: bool = True,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "corpus_claim_v1",
        "claim_id": claim_id,
        "family_id": family_id,
        "claim_text": claim_text,
        "source_ids": source_ids,
        "second_source_required": second_source_required,
        "created_at": FIXED_TIME,
        "doctrine_note": "Corpus claim is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_corpus_expected_outcome(
    *,
    outcome_id: str,
    claim_id: str,
    family_id: str,
    outcome_type: str,
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "corpus_expected_outcome_v1",
        "outcome_id": outcome_id,
        "claim_id": claim_id,
        "family_id": family_id,
        "outcome_type": outcome_type,
        "created_at": FIXED_TIME,
        "doctrine_note": "Expected outcome is not truth or proof.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
