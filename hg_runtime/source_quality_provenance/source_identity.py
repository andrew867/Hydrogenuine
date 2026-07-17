"""Source identity records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash

FIXED_TIME = "2026-06-20T00:00:00Z"


def build_source_identity(*, source_id: str, logical_source_key: str, path_ref: str, envelope_ref: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_identity_v1",
        "source_id": source_id,
        "logical_source_key": logical_source_key,
        "canonical_path_ref": path_ref,
        "envelope_ref": envelope_ref,
        "first_seen_at": FIXED_TIME,
        "last_updated_at": FIXED_TIME,
        "admission_layer": "LEB",
        "doctrine_note": "Source identity is not truth.",
        **neutral_flags(),
    }
    record["identity_hash"] = record_hash(record)
    assert_neutral(record)
    return record
