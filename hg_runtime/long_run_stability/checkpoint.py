"""Phase 39 checkpoints.

A checkpoint is a content-addressed snapshot of loop state sufficient to resume
deterministically: task cursor, iteration, receipt-chain root, boundary state,
and preserved statuses. The checkpoint hash changes whenever the captured state
changes and is stable for identical state. A checkpoint is not approval and
never carries authority.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.long_run_stability.boundary_monitor import boundary_state_hash
from hg_runtime.long_run_stability.schemas import (
    BOUNDARY_FLAG_FIELDS,
    CHECKPOINT_MANIFEST_SCHEMA,
    CHECKPOINT_RECORD_SCHEMA,
    PHASE19_STATUS,
    PHASE24_STATUS,
    StabilityError,
)

# Fields captured by a checkpoint (everything needed to resume + verify).
_CAPTURED = (
    "run_id",
    "task_queue_hash",
    "iteration",
    "task_cursor",
    "receipt_chain_root",
    "stop_requested",
    "panic_requested",
    "phase19_status",
    "phase24_status",
)


def _checkpoint_payload(state: Mapping[str, Any]) -> dict[str, Any]:
    payload = {field: state.get(field) for field in _CAPTURED}
    for field in BOUNDARY_FLAG_FIELDS:
        payload[field] = bool(state.get(field, False))
    payload["boundary_state_hash"] = boundary_state_hash(state)
    payload.setdefault("phase19_status", PHASE19_STATUS)
    payload.setdefault("phase24_status", PHASE24_STATUS)
    return payload


def checkpoint_hash(state: Mapping[str, Any]) -> str:
    return canonical_hash(_checkpoint_payload(state))


def make_checkpoint(state: Mapping[str, Any], *, sequence: int) -> dict[str, Any]:
    payload = _checkpoint_payload(state)
    chash = canonical_hash(payload)
    record = {
        "schema": CHECKPOINT_RECORD_SCHEMA,
        "checkpoint_id": f"ckpt-{sequence:04d}-{chash.removeprefix('sha256:')[:16]}",
        "sequence": sequence,
        "checkpoint_hash": chash,
        **payload,
    }
    return record


def verify_checkpoint(record: Mapping[str, Any]) -> bool:
    """True iff the record's stored hash matches a recompute of its payload."""
    payload = {k: v for k, v in record.items() if k not in ("schema", "checkpoint_id", "sequence", "checkpoint_hash")}
    return canonical_hash(payload) == record.get("checkpoint_hash")


def build_manifest(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    valid = [bool(verify_checkpoint(r)) for r in records]
    manifest = {
        "schema": CHECKPOINT_MANIFEST_SCHEMA,
        "count": len(records),
        "checkpoint_ids": [r["checkpoint_id"] for r in records],
        "checkpoint_hashes": [r["checkpoint_hash"] for r in records],
        "all_valid": all(valid),
        "manifest_hash": canonical_hash(
            {"ids": [r["checkpoint_id"] for r in records], "hashes": [r["checkpoint_hash"] for r in records]}
        ),
    }
    return manifest


def verify_manifest(records: list[Mapping[str, Any]], manifest: Mapping[str, Any]) -> bool:
    """True iff every checkpoint verifies and matches the manifest's recorded hashes."""
    if not all(verify_checkpoint(r) for r in records):
        return False
    return build_manifest(records)["manifest_hash"] == manifest.get("manifest_hash")


def last_valid_checkpoint(records: list[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for record in reversed(records):
        if verify_checkpoint(record):
            return record
    return None


def resume_state_from_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_checkpoint(record):
        raise StabilityError("corrupted_checkpoint")
    return {field: record.get(field) for field in _CAPTURED if field in record} | {
        field: bool(record.get(field, False)) for field in BOUNDARY_FLAG_FIELDS
    }


__all__ = [
    "checkpoint_hash",
    "make_checkpoint",
    "verify_checkpoint",
    "build_manifest",
    "verify_manifest",
    "last_valid_checkpoint",
    "resume_state_from_checkpoint",
]
