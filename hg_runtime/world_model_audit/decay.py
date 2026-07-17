"""Decay records — append-only maintenance markers, not deletion."""

from __future__ import annotations

from hg_runtime.world_model_audit.schemas import (
    DECAY_ACTIONS,
    DECAY_IS_NOT_DELETION,
    DECAY_RECORD_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_decay_record(
    *,
    target_record_id: str,
    target_record_kind: str,
    decay_action: str,
    reason: str,
    original_preserved: bool = True,
) -> dict:
    if decay_action not in DECAY_ACTIONS:
        raise ValueError(f"invalid_decay_action:{decay_action}")
    record = {
        "schema": DECAY_RECORD_SCHEMA,
        "decay_id": f"decay-{target_record_kind}-{target_record_id}",
        "target_record_id": target_record_id,
        "target_record_kind": target_record_kind,
        "decay_action": decay_action,
        "decay_reason": reason,
        "decay_is_not_deletion": True,
        "doctrine": DECAY_IS_NOT_DELETION,
        "original_preserved": original_preserved,
        "deletion_performed": False,
        "rewrite_performed": False,
        "decay_treated_as_deletion": False,
        **neutral_flags(),
    }
    record["decay_hash"] = canonical_hash(record)
    assert_neutral(record)
    return record


def validate_decay_record(record: dict) -> None:
    if record.get("schema") != DECAY_RECORD_SCHEMA:
        raise ValueError("invalid_decay_record_schema")
    if record.get("deletion_performed") or record.get("decay_treated_as_deletion"):
        raise ValueError("decay_treated_as_deletion_forbidden")
    assert_neutral(record)
