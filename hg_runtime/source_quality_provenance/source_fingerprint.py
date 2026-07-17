"""Source fingerprint and duplicate schema records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_source_fingerprint(*, source_id: str, content_hash: str, envelope_hash: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_fingerprint_v1",
        "source_id": source_id,
        "content_hash": content_hash,
        "envelope_hash": envelope_hash,
        "composite_hash": record_hash({"content_hash": content_hash, "envelope_hash": envelope_hash}),
        "normalization_rules_ref": "docs/planning/source_quality_provenance/01_SQP_SPEC.md",
        "computed_at": FIXED_TIME,
        "duplicate_treated_as_corroboration": False,
        **neutral_flags(),
    }
    record["fingerprint_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_duplicate_source_record(*, record_id: str, primary_source_id: str, duplicate_source_id: str, relation: str, composite_hash: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "duplicate_source_record_v1",
        "record_id": record_id,
        "primary_source_id": primary_source_id,
        "duplicate_source_id": duplicate_source_id,
        "relation": relation,
        "composite_hash": composite_hash,
        "copy_path_refs": ["tests/fixtures/local_evidence/source_001.md", "tests/fixtures/local_evidence/source_001_copy.md"],
        "independent_corroboration_count": 1,
        "doctrine_note": "Duplicate copies are not independent corroboration.",
        "duplicate_treated_as_corroboration": False,
        "many_copies_treated_as_many_sources": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
