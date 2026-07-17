"""Source staleness schema records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_staleness_record(*, source_id: str, level: str = "UNKNOWN_AGE") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_staleness_record_v1",
        "source_id": source_id,
        "staleness_level": level,
        "last_reviewed_at": None,
        "age_policy_ref": "docs/planning/source_quality_provenance/01_SQP_SPEC.md",
        "evaluated_at": FIXED_TIME,
        "doctrine_note": "Stale source is not false.",
        "stale_source_treated_as_false": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
