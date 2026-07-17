"""SEN-LIVE quarantine/withdrawal — privacy rollback records; no live sensor connection."""

from __future__ import annotations

from typing import Any

from hg_core.sen_live.errors import SEN_QUARANTINE_RECORDED, SEN_WITHDRAWAL_RECORDED
from hg_core.sen_live.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.live_sensor_ingestion.types import (
    FIXTURE_CLOCK,
    QuarantineRecord,
    SensorIngestReceipt,
    WithdrawalRecord,
)


def _quarantine_id(receipt_id: str) -> str:
    digest = canonical_hash({"receipt_id": receipt_id, "kind": "quarantine"})
    return f"sen-qtn-{digest.rsplit(':', 1)[-1][:12]}"


def _withdrawal_id(quarantine_id: str) -> str:
    digest = canonical_hash({"quarantine_id": quarantine_id, "kind": "withdrawal"})
    return f"sen-wdr-{digest.rsplit(':', 1)[-1][:12]}"


def quarantine_observation(
    receipt: SensorIngestReceipt,
    *,
    observation_digest: str,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record quarantine state for a committed fake-sink observation; no live sensor connection."""
    record = QuarantineRecord(
        quarantine_id=_quarantine_id(receipt.receipt_id),
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        observation_digest=observation_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SEN_QUARANTINE_RECORDED,
        "quarantine_record": record.to_payload(),
        "live_sensor_connection": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def withdraw_from_quarantine(
    quarantine_record: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Record withdrawal from quarantine; no live sensor connection."""
    quarantine_id = str(quarantine_record.get("quarantine_id", ""))
    observation_digest = str(quarantine_record.get("observation_digest", ""))
    record = WithdrawalRecord(
        withdrawal_id=_withdrawal_id(quarantine_id),
        quarantine_id=quarantine_id,
        observation_digest=observation_digest,
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": SEN_WITHDRAWAL_RECORDED,
        "withdrawal_record": record.to_payload(),
        "live_sensor_connection": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["quarantine_observation", "withdraw_from_quarantine"]
