from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import json
import hashlib

class EventType(str, Enum):
    TIMER = "timer"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    UI_ACTION = "ui_action"
    AGENT_SIGNAL = "agent_signal"
    INTERNAL = "internal"

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def stable_event_id(event_type: str, tenant_id: str, dedup_key: str, payload: Dict[str, Any]) -> str:
    """Deterministic event id helper.

    Use for sources where you want stable ids across retries.
    """
    blob = json.dumps(
        {"event_type": event_type, "tenant_id": tenant_id, "dedup_key": dedup_key, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: EventType
    tenant_id: str
    actor_id: str
    correlation_id: str
    payload: Dict[str, Any]
    dedup_key: Optional[str] = None

    created_at: datetime = _utc_now()
    seen_at: Optional[datetime] = None
    acked_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "dedup_key": self.dedup_key,
            "created_at": self.created_at.isoformat(),
            "seen_at": self.seen_at.isoformat() if self.seen_at else None,
            "acked_at": self.acked_at.isoformat() if self.acked_at else None,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Event":
        def parse_dt(x):
            if x is None:
                return None
            return datetime.fromisoformat(x)

        return Event(
            event_id=str(d["event_id"]),
            event_type=EventType(str(d["event_type"])),
            tenant_id=str(d["tenant_id"]),
            actor_id=str(d["actor_id"]),
            correlation_id=str(d["correlation_id"]),
            payload=dict(d["payload"]),
            dedup_key=d.get("dedup_key"),
            created_at=parse_dt(d.get("created_at")) or _utc_now(),
            seen_at=parse_dt(d.get("seen_at")),
            acked_at=parse_dt(d.get("acked_at")),
        )

    def validate(self) -> None:
        if not self.event_id or len(self.event_id) < 8:
            raise ValueError("event_id is required")
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
        if not self.actor_id:
            raise ValueError("actor_id is required")
        if not self.correlation_id:
            raise ValueError("correlation_id is required")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dict")
