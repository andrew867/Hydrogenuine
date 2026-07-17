"""Extended dry autonomy run lock."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyLockError
from hg_runtime.extended_dry_autonomy.schema import now_iso
from hg_runtime.extended_dry_autonomy.storage import current_lock_path, extended_root

LOCK_STALE_SECONDS = 120


class ExtendedLockState(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    STALE = "stale"
    MISSING = "missing"


@dataclass
class ExtendedLock:
    run_id: str
    pid: int
    started_at: str
    heartbeat_at: str
    state: ExtendedLockState = ExtendedLockState.ACTIVE

    def to_payload(self) -> dict:
        return {
            "run_id": self.run_id,
            "pid": self.pid,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
            "state": self.state.value,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> ExtendedLock:
        return cls(
            run_id=payload["run_id"],
            pid=int(payload["pid"]),
            started_at=payload["started_at"],
            heartbeat_at=payload["heartbeat_at"],
            state=ExtendedLockState(payload.get("state", ExtendedLockState.ACTIVE.value)),
        )


def read_lock(*, base: Path | None = None) -> ExtendedLock | None:
    path = current_lock_path(base=base)
    if not path.is_file():
        return None
    lock = ExtendedLock.from_payload(json.loads(path.read_text(encoding="utf-8")))
    if lock.state == ExtendedLockState.ACTIVE and _is_stale(lock):
        lock.state = ExtendedLockState.STALE
    return lock


def _is_stale(lock: ExtendedLock) -> bool:
    try:
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(lock.heartbeat_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds() > LOCK_STALE_SECONDS
    except Exception:
        return True


def acquire_lock(run_id: str, *, base: Path | None = None) -> ExtendedLock:
    extended_root(base=base).mkdir(parents=True, exist_ok=True)
    existing = read_lock(base=base)
    if existing and existing.state == ExtendedLockState.ACTIVE and existing.run_id != run_id:
        raise ExtendedDryAutonomyLockError(f"RED_EXTENDED_DRY_AUTONOMY_OVERLAP:{existing.run_id}")
    if existing and existing.state == ExtendedLockState.ACTIVE and existing.run_id == run_id:
        raise ExtendedDryAutonomyLockError("lock already held for this run_id")
    now = now_iso()
    lock = ExtendedLock(run_id=run_id, pid=os.getpid(), started_at=now, heartbeat_at=now)
    path = current_lock_path(base=base)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return lock


def heartbeat_lock(run_id: str, *, base: Path | None = None) -> ExtendedLock:
    lock = read_lock(base=base)
    if not lock or lock.run_id != run_id:
        raise ExtendedDryAutonomyLockError("RED_EXTENDED_DRY_AUTONOMY_LOCK_FAILURE")
    if lock.state == ExtendedLockState.STALE:
        raise ExtendedDryAutonomyLockError("lock is stale")
    lock.heartbeat_at = now_iso()
    current_lock_path(base=base).write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    return lock


def release_lock(run_id: str, *, status: str = "released", base: Path | None = None) -> None:
    lock = read_lock(base=base)
    path = current_lock_path(base=base)
    if not lock:
        return
    if lock.run_id != run_id:
        raise ExtendedDryAutonomyLockError("lock run_id mismatch on release")
    if status in ("released", "completed", "stopped", "panic", "failed"):
        path.unlink(missing_ok=True)


def lock_state(*, base: Path | None = None) -> ExtendedLockState:
    lock = read_lock(base=base)
    if not lock:
        return ExtendedLockState.MISSING
    return lock.state


__all__ = [
    "ExtendedLock",
    "ExtendedLockState",
    "acquire_lock",
    "heartbeat_lock",
    "lock_state",
    "read_lock",
    "release_lock",
]
