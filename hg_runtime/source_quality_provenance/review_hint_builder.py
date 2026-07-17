"""SQP-5 review hint builder (non-authoritative).

A review hint is advice for a human operator. It is never operator approval,
never a promotion, never an action, and never a truth claim. A hint cannot
override an AIS fever restriction, cannot override a quarantine, cannot authorize
tools, and cannot delete anything.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.schemas import (
    REVIEW_HINT_TYPES,
    REVIEW_PRIORITY_BANDS,
    SQPBoundaryError,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_review_hint(*, hint_id: str, source_id: str, hint_type: str, priority: str, rationale: list[str]) -> dict:
    if hint_type not in REVIEW_HINT_TYPES:
        raise SQPBoundaryError(f"unknown_review_hint_type:{hint_type}")
    if priority not in REVIEW_PRIORITY_BANDS:
        raise SQPBoundaryError(f"unknown_review_priority:{priority}")
    record = {
        "schema_version": "1",
        "record_type": "source_review_policy_hint_v1",
        "hint_id": hint_id,
        "source_id": source_id,
        "hint_type": hint_type,
        "priority": priority,
        "hint_rationale": list(rationale),
        "emitted_at": FIXED_TIME,
        "doctrine_note": "A review hint is advisory only; it is not operator approval.",
        "review_hint_treated_as_operator_approval": False,
        "hint_is_promotion": False,
        "hint_is_action": False,
        "hint_is_truth": False,
        "hint_overrides_fever_restriction": False,
        "hint_overrides_quarantine": False,
        "hint_authorizes_tools": False,
        "hint_deletes_source": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_blocked_review_hint(*, hint_id: str, source_id: str, requested_hint_type: str, replacement_hint_type: str, block_reason: str) -> dict:
    """Record a permissive hint that was blocked by a fever/quarantine restriction.

    The blocked hint demonstrates that a hint can never relax a restriction: a
    permissive ``ALLOW_PROVISIONAL_REVIEW`` is downgraded to a restrictive hint
    whenever AIS fever or quarantine applies.
    """
    if requested_hint_type not in REVIEW_HINT_TYPES:
        raise SQPBoundaryError(f"unknown_review_hint_type:{requested_hint_type}")
    if replacement_hint_type not in REVIEW_HINT_TYPES:
        raise SQPBoundaryError(f"unknown_review_hint_type:{replacement_hint_type}")
    record = {
        "schema_version": "1",
        "record_type": "blocked_review_hint_v1",
        "hint_id": hint_id,
        "source_id": source_id,
        "requested_hint_type": requested_hint_type,
        "replacement_hint_type": replacement_hint_type,
        "block_reason": block_reason,
        "blocked_at": FIXED_TIME,
        "doctrine_note": "A review hint cannot override fever or quarantine restrictions.",
        "review_hint_treated_as_operator_approval": False,
        "hint_overrides_fever_restriction": False,
        "hint_overrides_quarantine": False,
        "restriction_relaxed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
