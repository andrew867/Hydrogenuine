"""WRR receipts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hg_runtime.wake_refresh.schema import WakeRefreshReceipt, WasteEliminationReceipt, WasteClass

WRR_EVENT_TYPES = (
    "WAKE_REFRESH_STARTED",
    "WAKE_REFRESH_COMPLETED",
    "WASTE_ELIMINATED",
    "WAKE_REFRESH_BLOCKED_PROTECTED_PATH",
    "WAKE_REFRESH_STOPPED_PANIC",
)


def new_wake_receipt(verdict: str, *, cleanup_applied: bool, waste_count: int, epoch_id: str | None = None) -> WakeRefreshReceipt:
    return WakeRefreshReceipt(
        receipt_id=f"wrr-{uuid.uuid4().hex[:12]}",
        verdict=verdict,
        cleanup_applied=cleanup_applied,
        waste_eliminated_count=waste_count,
        epoch_id=epoch_id,
    )


def new_waste_receipt(
    path: str,
    waste_class: WasteClass,
    reason: str,
    *,
    content_hash: str | None = None,
    method: str = "delete",
    epoch_id: str | None = None,
) -> WasteEliminationReceipt:
    return WasteEliminationReceipt(
        receipt_id=f"wer-{uuid.uuid4().hex[:12]}",
        path=path,
        waste_class=waste_class,
        reason=reason,
        content_hash=content_hash,
        method=method,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        epoch_id=epoch_id,
    )


__all__ = ["WRR_EVENT_TYPES", "new_wake_receipt", "new_waste_receipt"]
