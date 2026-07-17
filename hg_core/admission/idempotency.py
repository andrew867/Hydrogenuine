"""Idempotency key store with retention window (CT-06 ADM)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    request_id: str
    result_ref: str
    recorded_at: float


class IdempotencyStore:
    def __init__(self, *, retention_s: float = 3600.0) -> None:
        self._retention_s = retention_s
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def lookup(self, key: str, *, now: float | None = None) -> IdempotencyRecord | None:
        ts = now if now is not None else time.monotonic()
        with self._lock:
            self._purge(ts)
            return self._records.get(key)

    def record(self, key: str, request_id: str, result_ref: str, *, now: float | None = None) -> IdempotencyRecord:
        ts = now if now is not None else time.monotonic()
        rec = IdempotencyRecord(key=key, request_id=request_id, result_ref=result_ref, recorded_at=ts)
        with self._lock:
            self._purge(ts)
            self._records[key] = rec
        return rec

    def _purge(self, now: float) -> None:
        expired = [k for k, v in self._records.items() if now - v.recorded_at > self._retention_s]
        for key in expired:
            del self._records[key]

    def export_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"key": r.key, "request_id": r.request_id, "result_ref": r.result_ref}
                for r in self._records.values()
            ]


__all__ = ["IdempotencyRecord", "IdempotencyStore"]
