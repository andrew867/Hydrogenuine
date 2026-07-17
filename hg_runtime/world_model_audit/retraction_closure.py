"""Retraction closure records — preserve originals, close audit paths."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    RETRACTION_CLOSURE_SCHEMA,
    RETRACTION_IS_NOT_ERASURE,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_retraction_closure(
    *,
    hypothesis_id: str,
    original_record_id: str,
    closure_reason: str,
    original_preserved: bool = True,
) -> dict:
    record = {
        "schema": RETRACTION_CLOSURE_SCHEMA,
        "closure_id": f"retraction-closure-{hypothesis_id}",
        "hypothesis_id": hypothesis_id,
        "original_record_id": original_record_id,
        "closure_reason": closure_reason,
        "retraction_is_not_erasure": True,
        "doctrine": RETRACTION_IS_NOT_ERASURE,
        "original_preserved": original_preserved,
        "deletion_performed": False,
        "rewrite_performed": False,
        "retraction_treated_as_erasure": False,
        "audit_closure_treated_as_laundering": False,
        **neutral_flags(),
    }
    record["closure_hash"] = canonical_hash(record)
    assert_neutral(record)
    return record


def validate_retraction_closure(record: dict) -> None:
    if record.get("schema") != RETRACTION_CLOSURE_SCHEMA:
        raise ValueError("invalid_retraction_closure_schema")
    if not record.get("original_preserved"):
        raise ValueError("original_must_be_preserved")
    if record.get("retraction_treated_as_erasure") or record.get("audit_closure_treated_as_laundering"):
        raise ValueError("retraction_erasure_or_laundering_forbidden")
    assert_neutral(record)
