"""Source quality score schema records."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_source_quality_score(*, source_id: str, quality_band: str = "STRUCTURALLY_USABLE") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "source_quality_score_v1",
        "source_id": source_id,
        "quality_band": quality_band,
        "dimensions": {
            "envelope_completeness": 1.0,
            "provenance_depth": 0.0,
            "redaction": 1.0,
            "review_linkage": 0.5,
            "quarantine_cleanliness": 1.0,
        },
        "score_rationale": ["schema-foundation fixture only; factual correctness excluded"],
        "scored_at": FIXED_TIME,
        "doctrine_note": "Source quality is not truth.",
        "source_quality_treated_as_truth": False,
        "certainty_claimed": False,
        **neutral_flags(),
    }
    record["quality_hash"] = record_hash(record)
    assert_neutral(record)
    return record
