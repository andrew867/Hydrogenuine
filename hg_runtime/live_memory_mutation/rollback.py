"""MEM-LIVE rollback — rollback and restore records; no durable writes."""

from __future__ import annotations

from typing import Any

from hg_core.mem_live.errors import MEM_RESTORE_RECORDED, MEM_ROLLBACK_RECORDED
from hg_core.mem_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_memory_mutation.types import (
    FIXTURE_CLOCK,
    MemoryMutationReceipt,
    RestoreRecord,
    RollbackRecord,
)


def _rollback_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "rollback"})
    return f"mem-rbk-{digest.rsplit(':', 1)[-1][:12]}"


def _restore_id(rollback_id: str) -> str:
    digest = canonical_hash({"rollback_id": rollback_id, "kind": "restore"})
    return f"mem-rst-{digest.rsplit(':', 1)[-1][:12]}"


def rollback_memory_mutation(
    receipt: MemoryMutationReceipt,
    *,
    memory_key: str,
    prior_digest: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record rollback state for a committed fake-sink mutation; no durable write."""
    record = RollbackRecord(
        rollback_id=_rollback_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        memory_key=memory_key,
        prior_digest=prior_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": MEM_ROLLBACK_RECORDED,
        "rollback_record": record.to_payload(),
        "rollback_acknowledged": True,
        "durable_write_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def restore_from_rollback(
    rollback_record: dict[str, Any],
    *,
    restored_digest: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record restore from rollback; no durable write."""
    rollback_id = str(rollback_record.get("rollback_id", ""))
    memory_key = str(rollback_record.get("memory_key", ""))
    record = RestoreRecord(
        restore_id=_restore_id(rollback_id),
        rollback_id=rollback_id,
        memory_key=memory_key,
        restored_digest=restored_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": MEM_RESTORE_RECORDED,
        "restore_record": record.to_payload(),
        "restore_available": True,
        "durable_write_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["restore_from_rollback", "rollback_memory_mutation"]
