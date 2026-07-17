"""SQP-4 source staleness detector (descriptive metadata only).

Staleness is a descriptive signal. A stale source is *not* false: it is merely
old, undated, superseded, or retracted/quarantined. Staleness may at most emit a
review hint; it never deletes, never resolves truth, and never authorizes action.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.schemas import (
    STALENESS_CLASSES,
    SQPBoundaryError,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def classify_staleness(source: dict) -> str:
    if source.get("retracted_or_quarantined"):
        return "RETRACTED_OR_QUARANTINED"
    if source.get("superseded_by_reviewed"):
        return "SUPERSEDED_BY_REVIEWED_SOURCE"
    age_class = source.get("age_class")
    if age_class is None:
        return "DATE_UNKNOWN"
    if age_class == "CURRENT":
        return "CURRENT_ENOUGH"
    if age_class == "OLD":
        return "POSSIBLY_STALE"
    if age_class == "STALE":
        return "STALE_BY_POLICY"
    raise SQPBoundaryError(f"unknown_age_class:{age_class}")


def build_staleness_record(source: dict) -> dict:
    staleness_class = classify_staleness(source)
    if staleness_class not in STALENESS_CLASSES:
        raise SQPBoundaryError(f"unknown_staleness_class:{staleness_class}")
    # Only non-current, decidable signals may suggest a review hint.
    may_emit_review_hint = staleness_class in {
        "POSSIBLY_STALE",
        "STALE_BY_POLICY",
        "SUPERSEDED_BY_REVIEWED_SOURCE",
        "RETRACTED_OR_QUARANTINED",
    }
    record = {
        "schema_version": "1",
        "record_type": "source_staleness_record_v1",
        "source_id": source["source_id"],
        "staleness_class": staleness_class,
        "age_class": source.get("age_class"),
        "superseded_by_reviewed": bool(source.get("superseded_by_reviewed")),
        "retracted_or_quarantined": bool(source.get("retracted_or_quarantined")),
        "may_emit_review_hint": may_emit_review_hint,
        "evaluated_at": FIXED_TIME,
        "doctrine_note": "Stale source is not false. Staleness may only suggest review.",
        "stale_source_treated_as_false": False,
        "staleness_authorizes_action": False,
        "staleness_authorizes_tools": False,
        "staleness_deletes_source": False,
        "source_preserved": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def detect_staleness(sources: list[dict]) -> list[dict]:
    return [build_staleness_record(source) for source in sources]
