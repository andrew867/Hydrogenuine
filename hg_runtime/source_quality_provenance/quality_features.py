"""SQP-2 deterministic quality feature extraction."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.schemas import QUALITY_FEATURE_CATEGORIES, assert_neutral, neutral_flags
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_quality_feature_record(*, source_id: str, features: dict[str, bool]) -> dict:
    unknown = set(features) - QUALITY_FEATURE_CATEGORIES
    if unknown:
        raise ValueError(f"unknown_quality_features:{sorted(unknown)}")
    complete = {name: bool(features.get(name, False)) for name in sorted(QUALITY_FEATURE_CATEGORIES)}
    record = {
        "schema_version": "1",
        "record_type": "source_quality_feature_record_v1",
        "source_id": source_id,
        "features": complete,
        "feature_count": sum(1 for value in complete.values() if value),
        "evaluated_at": FIXED_TIME,
        "doctrine_note": "Quality features are metadata, not truth or authority.",
        **neutral_flags(),
    }
    record["feature_hash"] = record_hash(record)
    assert_neutral(record)
    return record
