"""OEC corpus source records."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.corpus_manifest import FIXED_TIME
from hg_runtime.operator_evidence_corpus.schemas import assert_neutral, neutral_flags, record_hash


def build_corpus_source(
    *,
    source_id: str,
    path_ref: str,
    logical_key: str,
    family_id: str,
    quality_band: str = "STRUCTURALLY_USABLE",
) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "corpus_source_v1",
        "source_id": source_id,
        "path_ref": path_ref,
        "logical_source_key": logical_key,
        "family_id": family_id,
        "quality_band": quality_band,
        "created_at": FIXED_TIME,
        "doctrine_note": "Local source is not authority.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
