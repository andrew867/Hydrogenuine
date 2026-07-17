"""OEA-TER-LIVE rollback — rollback and compensation records; no live actions."""

from __future__ import annotations

from typing import Any

from hg_core.oea_ter_live.errors import OEA_TER_COMPENSATION_RECORDED, OEA_TER_ROLLBACK_RECORDED
from hg_core.oea_ter_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_oea_ter_bridge.types import (
    FIXTURE_CLOCK,
    CompensationRecord,
    LiveActionReceipt,
    RollbackRecord,
)


def _rollback_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "rollback"})
    return f"oea-rbk-{digest.rsplit(':', 1)[-1][:12]}"


def _compensation_id(rollback_id: str) -> str:
    digest = canonical_hash({"rollback_id": rollback_id, "kind": "compensation"})
    return f"oea-cmp-{digest.rsplit(':', 1)[-1][:12]}"


def rollback_live_action(
    receipt: LiveActionReceipt,
    *,
    action_digest: str,
    prior_digest: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record rollback state for a committed fake-sink dispatch; no live action."""
    record = RollbackRecord(
        rollback_id=_rollback_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        action_digest=action_digest,
        prior_digest=prior_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": OEA_TER_ROLLBACK_RECORDED,
        "rollback_record": record.to_payload(),
        "rollback_acknowledged": True,
        "live_action_performed": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def compensate_from_rollback(
    rollback_record: dict[str, Any],
    *,
    compensation_digest: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record compensation from rollback; no live action."""
    rollback_id = str(rollback_record.get("rollback_id", ""))
    action_digest = str(rollback_record.get("action_digest", ""))
    record = CompensationRecord(
        compensation_id=_compensation_id(rollback_id),
        rollback_id=rollback_id,
        action_digest=action_digest,
        compensation_digest=compensation_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": OEA_TER_COMPENSATION_RECORDED,
        "compensation_record": record.to_payload(),
        "compensation_available": True,
        "live_action_performed": False,
        "oea_ter_called": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["compensate_from_rollback", "rollback_live_action"]
