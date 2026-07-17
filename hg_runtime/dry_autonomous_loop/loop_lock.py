"""Dry autonomous loop lock — one active loop at a time."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopLockError
from hg_runtime.dry_autonomous_loop.schema import now_iso
from hg_runtime.dry_autonomous_loop.storage import current_lock_path, loop_root

LOCK_STALE_SECONDS = 120


class LoopLockState(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    STALE = "stale"
    MISSING = "missing"


@dataclass
class LoopLock:
    run_id: str
    pid: int
    started_at: str
    heartbeat_at: str
    state: LoopLockState = LoopLockState.ACTIVE

    def to_payload(self) -> dict:
        return {
            "run_id": self.run_id,
            "pid": self.pid,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
            "state": self.state.value,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> LoopLock:
        return cls(
            run_id=payload["run_id"],
            pid=int(payload["pid"]),
            started_at=payload["started_at"],
            heartbeat_at=payload["heartbeat_at"],
            state=LoopLockState(payload.get("state", LoopLockState.ACTIVE.value)),
        )


def read_lock(*, base: Path | None = None) -> LoopLock | None:
    path = current_lock_path(base=base)
    if not path.is_file():
        return None
    lock = LoopLock.from_payload(json.loads(path.read_text(encoding="utf-8")))
    if lock.state == LoopLockState.ACTIVE and _is_stale(lock):
        lock.state = LoopLockState.STALE
    return lock


def _is_stale(lock: LoopLock) -> bool:
    try:
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(lock.heartbeat_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds() > LOCK_STALE_SECONDS
    except Exception:
        return True


def acquire_lock(run_id: str, *, base: Path | None = None) -> LoopLock:
    loop_root(base=base).mkdir(parents=True, exist_ok=True)
    existing = read_lock(base=base)
    if existing and existing.state == LoopLockState.ACTIVE and existing.run_id != run_id:
        raise DryAutonomousLoopLockError(f"RED_DRY_AUTONOMOUS_LOOP_OVERLAP:{existing.run_id}")
    if existing and existing.state == LoopLockState.ACTIVE and existing.run_id == run_id:
        raise DryAutonomousLoopLockError("lock already held for this run_id")

    now = now_iso()
    lock = LoopLock(run_id=run_id, pid=os.getpid(), started_at=now, heartbeat_at=now)
    path = current_lock_path(base=base)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return lock


def heartbeat_lock(run_id: str, *, base: Path | None = None) -> LoopLock:
    lock = read_lock(base=base)
    if not lock or lock.run_id != run_id:
        raise DryAutonomousLoopLockError("RED_DRY_AUTONOMOUS_LOOP_LOCK_FAILURE")
    if lock.state == LoopLockState.STALE:
        raise DryAutonomousLoopLockError("lock is stale")
    lock.heartbeat_at = now_iso()
    current_lock_path(base=base).write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    return lock


def release_lock(run_id: str, *, status: str = "released", base: Path | None = None) -> None:
    lock = read_lock(base=base)
    path = current_lock_path(base=base)
    if not lock:
        return
    if lock.run_id != run_id:
        raise DryAutonomousLoopLockError("lock run_id mismatch on release")
    released = LoopLock(
        run_id=run_id,
        pid=lock.pid,
        started_at=lock.started_at,
        heartbeat_at=now_iso(),
        state=LoopLockState.RELEASED,
    )
    payload = released.to_payload()
    payload["release_status"] = status
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if status in ("released", "completed", "stopped", "panic", "failed"):
        path.unlink(missing_ok=True)


def lock_state(*, base: Path | None = None) -> LoopLockState:
    lock = read_lock(base=base)
    if not lock:
        return LoopLockState.MISSING
    return lock.state


def recover_stale_lock(*, base: Path | None = None) -> bool:
    lock = read_lock(base=base)
    if lock and lock.state == LoopLockState.STALE:
        current_lock_path(base=base).unlink(missing_ok=True)
        return True
    return False


__all__ = [
    "LOCK_STALE_SECONDS",
    "LoopLock",
    "LoopLockState",
    "acquire_lock",
    "heartbeat_lock",
    "lock_state",
    "read_lock",
    "recover_stale_lock",
    "release_lock",
]
