"""ALOOP-LIVE rollback — loop stop compensation; no live loop start."""

from __future__ import annotations

from typing import Any

from hg_core.aloop_live.errors import ALOOP_PAUSE_RECORDED, ALOOP_ROLLBACK_RECORDED
from hg_core.aloop_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_autonomous_loop.types import FIXTURE_CLOCK, LoopSupervisorReceipt


def _rollback_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "loop_rollback"})
    return f"aloop-rbk-{digest.rsplit(':', 1)[-1][:12]}"


def rollback_loop_supervisor(
    receipt: LoopSupervisorReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record rollback for a fake-sink loop supervisor; no live loop."""
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ALOOP_ROLLBACK_RECORDED,
        "rollback_id": _rollback_id(receipt.receipt_id),
        "receipt_id": receipt.receipt_id,
        "rollback_acknowledged": True,
        "live_loop_started": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def record_loop_pause(
    receipt: LoopSupervisorReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record operator pause without live loop start."""
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ALOOP_PAUSE_RECORDED,
        "receipt_id": receipt.receipt_id,
        "supervisor_state": "paused",
        "live_loop_started": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["record_loop_pause", "rollback_loop_supervisor"]
