"""SRP-LIVE rollback — rollback records; no live landing."""

from __future__ import annotations

from typing import Any

from hg_core.srp_live.errors import SRP_ROLLBACK_RECORDED
from hg_core.srp_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_srp_apply.types import FIXTURE_CLOCK, RollbackRecord, SRPApplyReceipt


def _rollback_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "rollback"})
    return f"srp-rbk-{digest.rsplit(':', 1)[-1][:12]}"


def rollback_srp_apply(
    receipt: SRPApplyReceipt,
    *,
    target_ref: str,
    prior_digest: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record rollback state for a fake-sink apply; no live landing."""
    record = RollbackRecord(
        rollback_id=_rollback_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        repair_id=receipt.repair_id,
        target_ref=target_ref,
        prior_digest=prior_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SRP_ROLLBACK_RECORDED,
        "rollback_record": record.to_payload(),
        "rollback_acknowledged": True,
        "live_landing_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["rollback_srp_apply"]
