"""RIB-SPAWN-LIVE rollback — failed spawn compensation; no live spawn."""

from __future__ import annotations

from typing import Any

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.rib_spawn_live.errors import RIB_SPAWN_ROLLBACK_RECORDED
from hg_core.rib_spawn_live.no_authority import advisory_only_marker
from hg_runtime.live_reproduction_spawn.types import FIXTURE_CLOCK, ChildSpawnReceipt, FailedSpawnRecord


def _rollback_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "spawn_rollback"})
    return f"rib-rbk-{digest.rsplit(':', 1)[-1][:12]}"


def rollback_spawn_plan(
    receipt: ChildSpawnReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record rollback for a fake-sink spawn plan; no live spawn."""
    record = FailedSpawnRecord(
        failed_spawn_id=_rollback_id(receipt.receipt_id),
        request_id=receipt.request_id,
        reason_code=RIB_SPAWN_ROLLBACK_RECORDED,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": RIB_SPAWN_ROLLBACK_RECORDED,
        "failed_spawn_record": record.to_payload(),
        "rollback_acknowledged": True,
        "live_spawn_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["rollback_spawn_plan"]
