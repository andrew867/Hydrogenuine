"""CHRONO receipts — hashable proof-of-record of a time reading.

A receipt is evidence, never a secret, never PII, never authority.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from hg_runtime.chrono.hash import chrono_hash
from hg_runtime.chrono.schema import TimeConfidence, TimeSourceKind, TimeSyncResult

CHRONO_EVENT_TYPES = (
    "CHRONO_SYNC_ATTEMPTED",
    "CHRONO_TIME_RECEIVED",
    "CHRONO_FALLBACK_USED",
    "CHRONO_TIME_UNAVAILABLE",
    "CHRONO_CLOCK_DRIFT_DETECTED",
    "CHRONO_BACKWARD_ORDERING_DETECTED",
    "CHRONO_AUTHORITY_CONVERSION_REJECTED",
)


@dataclass
class ChronoReceipt:
    receipt_id: str
    utc_now: str
    monotonic_seconds: float
    source: TimeSourceKind
    time_confidence: TimeConfidence
    time_uncertain: bool
    ntp_host: str | None = None
    drift_seconds: float | None = None
    drift_finding_ref: str | None = None
    epoch_id: str | None = None
    epoch_lock_id: str | None = None
    monotonic_ns: int | None = None
    receipt_sequence: int = 0

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "chrono-receipt",
            "receipt_id": self.receipt_id,
            "utc_now": self.utc_now,
            "monotonic_seconds": self.monotonic_seconds,
            "source": self.source.value,
            "ntp_host": self.ntp_host,
            "time_confidence": self.time_confidence.value,
            "time_uncertain": self.time_uncertain,
            "drift_seconds": self.drift_seconds,
            "drift_finding_ref": self.drift_finding_ref,
            "epoch_id": self.epoch_id,
            "epoch_lock_id": self.epoch_lock_id,
            "monotonic_ns": self.monotonic_ns,
            "receipt_sequence": self.receipt_sequence,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["content_hash"] = chrono_hash(payload)
        return payload


def create_receipt(result: TimeSyncResult, *, drift_finding_ref: str | None = None) -> ChronoReceipt:
    return ChronoReceipt(
        receipt_id=f"chronorcpt-{uuid.uuid4().hex[:12]}",
        utc_now=result.utc,
        monotonic_seconds=result.monotonic_seconds,
        source=result.source,
        time_confidence=result.confidence,
        time_uncertain=result.time_uncertain,
        ntp_host=result.ntp_host,
        drift_seconds=result.drift_seconds,
        drift_finding_ref=drift_finding_ref,
    )


def create_epoch_receipt(
    result: TimeSyncResult,
    *,
    epoch_id: str,
    epoch_lock_id: str,
    receipt_sequence: int,
    drift_finding_ref: str | None = None,
) -> ChronoReceipt:
    import time

    receipt = create_receipt(result, drift_finding_ref=drift_finding_ref)
    receipt.epoch_id = epoch_id
    receipt.epoch_lock_id = epoch_lock_id
    receipt.monotonic_ns = time.monotonic_ns()
    receipt.receipt_sequence = receipt_sequence
    return receipt


def stamp_mission_receipt(
    receipt: ChronoReceipt,
    *,
    epoch_id: str,
    epoch_lock_id: str,
    receipt_sequence: int,
) -> ChronoReceipt:
    """Attach epoch binding to a mission receipt; monotonic sequence is tie-breaker."""
    import time

    receipt.epoch_id = epoch_id
    receipt.epoch_lock_id = epoch_lock_id
    receipt.monotonic_ns = time.monotonic_ns()
    receipt.receipt_sequence = receipt_sequence
    return receipt


__all__ = ["CHRONO_EVENT_TYPES", "ChronoReceipt", "create_epoch_receipt", "create_receipt", "stamp_mission_receipt"]
