"""Foreground session lock — prevents overlap."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from hg_runtime.hands_off_session.errors import HandsOffLockError
from hg_runtime.hands_off_session.schema import STORE_ROOT, now_iso


LOCK_STALE_SECONDS = 180


class SessionLockState(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    STALE = "stale"


@dataclass
class ForegroundSessionLock:
    session_id: str
    pid: int
    started_at: str
    heartbeat_at: str
    state: SessionLockState = SessionLockState.ACTIVE

    def to_payload(self) -> dict:
        return {
            "session_id": self.session_id,
            "pid": self.pid,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
            "state": self.state.value,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> ForegroundSessionLock:
        return cls(
            session_id=payload["session_id"],
            pid=int(payload["pid"]),
            started_at=payload["started_at"],
            heartbeat_at=payload["heartbeat_at"],
            state=SessionLockState(payload.get("state", SessionLockState.ACTIVE.value)),
        )


def lock_path(*, base: Path | None = None) -> Path:
    root = base or STORE_ROOT
    return root / "current_lock.json"


def read_lock(*, base: Path | None = None) -> ForegroundSessionLock | None:
    path = lock_path(base=base)
    if not path.is_file():
        return None
    lock = ForegroundSessionLock.from_payload(json.loads(path.read_text(encoding="utf-8")))
    if lock.state == SessionLockState.ACTIVE and _is_stale(lock):
        lock.state = SessionLockState.STALE
    return lock


def _is_stale(lock: ForegroundSessionLock) -> bool:
    try:
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(lock.heartbeat_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds() > LOCK_STALE_SECONDS
    except Exception:
        return True


def acquire_lock(session_id: str, *, base: Path | None = None) -> ForegroundSessionLock:
    root = base or STORE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    existing = read_lock(base=base)
    if existing and existing.state == SessionLockState.ACTIVE and existing.session_id != session_id:
        raise HandsOffLockError(f"RED_PHASE22_OVERLAP_ALLOWED:{existing.session_id}")
    if existing and existing.state == SessionLockState.ACTIVE and existing.session_id == session_id:
        raise HandsOffLockError("RED_PHASE22_OVERLAP_ALLOWED:same_session")

    now = now_iso()
    lock = ForegroundSessionLock(session_id=session_id, pid=os.getpid(), started_at=now, heartbeat_at=now)
    path = lock_path(base=base)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return lock


def heartbeat_lock(session_id: str, *, base: Path | None = None) -> ForegroundSessionLock:
    lock = read_lock(base=base)
    if not lock or lock.session_id != session_id:
        raise HandsOffLockError("RED_PHASE22_RUN_LOCK_MISSING")
    lock.heartbeat_at = now_iso()
    lock_path(base=base).write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    return lock


def release_lock(session_id: str, *, status: str = "released", base: Path | None = None) -> None:
    lock = read_lock(base=base)
    if lock and lock.session_id == session_id:
        lock.state = SessionLockState.RELEASED
        lock.heartbeat_at = now_iso()
        payload = lock.to_payload()
        payload["release_status"] = status
        lock_path(base=base).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
