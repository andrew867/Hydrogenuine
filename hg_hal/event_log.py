"""HAL event log adapter — append-only in-memory or file-backed log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from hg_hal.models import HalEvent


class HalEventLogAdapter:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path
        self._events: list[HalEvent] = []
        self._seq = 0

    @property
    def events(self) -> list[HalEvent]:
        return list(self._events)

    def append(self, event: HalEvent) -> HalEvent:
        if event.seq != self._seq + 1:
            raise ValueError(f"event seq {event.seq} != expected {self._seq + 1}")
        self._events.append(event)
        self._seq = event.seq
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_payload(), sort_keys=True) + "\n")
        return event

    def next_seq(self) -> int:
        return self._seq + 1

    def read_all(self) -> list[HalEvent]:
        if self._path is not None and self._path.exists():
            loaded: list[HalEvent] = []
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                loaded.append(
                    HalEvent(
                        seq=int(payload["seq"]),
                        event_type=str(payload["event_type"]),
                        timestamp=str(payload["timestamp"]),
                        request_id=str(payload["request_id"]),
                        payload=dict(payload["payload"]),
                    )
                )
            return loaded
        return list(self._events)


__all__ = ["HalEventLogAdapter"]
