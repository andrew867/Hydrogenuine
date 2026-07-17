"""Self mirror receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

SELF_MIRROR_EVENT_TYPES = (
    "SELF_MIRROR_SNAPSHOT_BUILT",
    "SELF_INSPECTION_ANSWERED",
    "SELF_INSPECTION_REFUSED",
    "IDLE_SELF_CHECK_STARTED",
    "IDLE_SELF_CHECK_QUESTION_SELECTED",
    "IDLE_SELF_CHECK_ANSWERED",
    "IDLE_SELF_CHECK_STOPPED",
    "IDLE_SELF_CHECK_BLOCKED_MUTATION",
)


@dataclass
class SelfMirrorReceipt:
    receipt_id: str
    event_type: str
    snapshot_hash: str | None = None
    question_id: str | None = None
    detail: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "self-mirror-receipt",
            "receipt_id": self.receipt_id,
            "event_type": self.event_type,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "snapshot_hash": self.snapshot_hash,
            "question_id": self.question_id,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def new_receipt(event_type: str, **kwargs: Any) -> SelfMirrorReceipt:
    return SelfMirrorReceipt(
        receipt_id=f"smr-{uuid.uuid4().hex[:12]}",
        event_type=event_type,
        snapshot_hash=kwargs.get("snapshot_hash"),
        question_id=kwargs.get("question_id"),
        detail=kwargs.get("detail", ""),
    )


__all__ = ["SELF_MIRROR_EVENT_TYPES", "SelfMirrorReceipt", "new_receipt"]
