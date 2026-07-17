"""Run lock — prevent overlapping rehearsal runs."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.supervised_rehearsal.errors import RehearsalLockError
from hg_runtime.supervised_rehearsal.rehearsal_store import current_lock_path, rehearsal_root
from hg_runtime.supervised_rehearsal.schema import RunLockState, now_iso

LOCK_STALE_SECONDS = 120


@dataclass
class RunLock:
    run_id: str
    pid: int
    started_at: str
    heartbeat_at: str
    state: RunLockState = RunLockState.ACTIVE

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "pid": self.pid,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
            "state": self.state.value,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> RunLock:
        return cls(
            run_id=payload["run_id"],
            pid=int(payload["pid"]),
            started_at=payload["started_at"],
            heartbeat_at=payload["heartbeat_at"],
            state=RunLockState(payload.get("state", RunLockState.ACTIVE.value)),
        )


def _lock_path(*, base: Path | None = None) -> Path:
    return current_lock_path(base=base)


def read_lock(*, base: Path | None = None) -> RunLock | None:
    path = _lock_path(base=base)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    lock = RunLock.from_payload(payload)
    if lock.state == RunLockState.ACTIVE and _is_stale(lock):
        lock.state = RunLockState.STALE
    return lock


def _is_stale(lock: RunLock) -> bool:
    try:
        hb = lock.heartbeat_at
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(hb.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age > LOCK_STALE_SECONDS
    except Exception:
        return True


def acquire_lock(run_id: str, *, base: Path | None = None) -> RunLock:
    rehearsal_root(base=base).mkdir(parents=True, exist_ok=True)
    existing = read_lock(base=base)
    if existing and existing.state == RunLockState.ACTIVE and existing.run_id != run_id:
        raise RehearsalLockError(f"RED_REHEARSAL_LOCK_CONFLICT:{existing.run_id}")
    if existing and existing.state == RunLockState.ACTIVE and existing.run_id == run_id:
        raise RehearsalLockError("lock already held for this run_id")

    now = now_iso()
    lock = RunLock(run_id=run_id, pid=os.getpid(), started_at=now, heartbeat_at=now)
    path = _lock_path(base=base)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return lock


def heartbeat_lock(run_id: str, *, base: Path | None = None) -> RunLock:
    lock = read_lock(base=base)
    if not lock or lock.run_id != run_id:
        raise RehearsalLockError("RED_REHEARSAL_LOCK_MISSING")
    if lock.state == RunLockState.STALE:
        raise RehearsalLockError("lock is stale")
    lock.heartbeat_at = now_iso()
    _lock_path(base=base).write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    return lock


def release_lock(run_id: str, *, status: str = "released", base: Path | None = None) -> None:
    lock = read_lock(base=base)
    path = _lock_path(base=base)
    if not lock:
        return
    if lock.run_id != run_id:
        raise RehearsalLockError("lock run_id mismatch on release")
    released = RunLock(
        run_id=run_id,
        pid=lock.pid,
        started_at=lock.started_at,
        heartbeat_at=now_iso(),
        state=RunLockState.RELEASED,
    )
    payload = released.to_payload()
    payload["release_status"] = status
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if status in ("released", "completed", "stopped", "panic"):
        path.unlink(missing_ok=True)


def lock_state(*, base: Path | None = None) -> RunLockState:
    lock = read_lock(base=base)
    if not lock:
        return RunLockState.MISSING
    return lock.state


def recover_stale_lock(*, base: Path | None = None) -> bool:
    lock = read_lock(base=base)
    if lock and lock.state == RunLockState.STALE:
        _lock_path(base=base).unlink(missing_ok=True)
        return True
    return False


__all__ = [
    "LOCK_STALE_SECONDS",
    "RunLock",
    "acquire_lock",
    "heartbeat_lock",
    "lock_state",
    "read_lock",
    "recover_stale_lock",
    "release_lock",
]
