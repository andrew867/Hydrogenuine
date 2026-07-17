"""Source conflict schema records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_conflict_record(*, conflict_id: str, participant_source_ids: list[str]) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_conflict_record_v1",
        "conflict_id": conflict_id,
        "participant_source_ids": participant_source_ids,
        "conflict_status": "UNRESOLVED",
        "declared_by_ref": "schema-foundation-fixture",
        "detected_at": FIXED_TIME,
        "doctrine_note": "Contradicted source is not erased.",
        "deletion_performed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
