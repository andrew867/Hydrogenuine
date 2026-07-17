"""SQP-5 review priority classification (non-authoritative).

Priority only orders operator attention. A high priority is not urgency-as-truth
and never authorizes automatic action.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.schemas import (
    REVIEW_PRIORITY_BANDS,
    SQPBoundaryError,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME

_CRITICAL = {"BLOCK_PROMOTION_REQUEST", "RETRACTION_RECOMMENDED", "QUARANTINE_RECOMMENDED"}
_HIGH = {"PRIORITIZE_REVIEW", "REQUIRE_OPERATOR_CONFIRMATION"}
_NORMAL = {"REQUEST_MORE_EVIDENCE", "REQUIRE_SECOND_SOURCE"}


def priority_for_hint(hint_type: str) -> str:
    if hint_type in _CRITICAL:
        return "CRITICAL_REVIEW_REQUIRED"
    if hint_type in _HIGH:
        return "HIGH"
    if hint_type in _NORMAL:
        return "NORMAL"
    return "LOW"


def build_review_priority_record(*, source_id: str, hint_type: str, priority: str) -> dict:
    if priority not in REVIEW_PRIORITY_BANDS:
        raise SQPBoundaryError(f"unknown_review_priority:{priority}")
    record = {
        "schema_version": "1",
        "record_type": "review_priority_record_v1",
        "source_id": source_id,
        "hint_type": hint_type,
        "priority": priority,
        "assigned_at": FIXED_TIME,
        "doctrine_note": "Priority orders attention; it does not authorize action.",
        "priority_authorizes_action": False,
        "priority_is_truth": False,
        "review_hint_treated_as_operator_approval": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
