"""Field run lock — prevents overlap."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.overnight_field_run.errors import FieldRunLockError
from hg_runtime.overnight_field_run.schema import STORE_ROOT, OvernightFieldRunVerdict, now_iso

LOCK_STALE_SECONDS = 180


@dataclass
class FieldRunLock:
    field_run_id: str
    pid: int
    started_at: str
    state: str = "active"

    def to_payload(self) -> dict:
        return {
            "field_run_id": self.field_run_id,
            "pid": self.pid,
            "started_at": self.started_at,
            "state": self.state,
        }


def lock_path(*, base: Path | None = None) -> Path:
    root = base or STORE_ROOT
    return root / "current_lock.json"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _is_stale(data: dict) -> bool:
    if data.get("state") != "active":
        return True
    pid = int(data.get("pid", 0))
    if not _pid_alive(pid):
        return True
    try:
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(str(data.get("started_at", "")).replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds() > LOCK_STALE_SECONDS
    except (ValueError, TypeError):
        return True


def acquire_field_run_lock(field_run_id: str, *, base: Path | None = None) -> FieldRunLock:
    root = base or STORE_ROOT
    root.mkdir(parents=True, exist_ok=True)
    path = lock_path(base=base)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("state") == "active" and not _is_stale(data):
            if data.get("field_run_id") != field_run_id:
                raise FieldRunLockError(OvernightFieldRunVerdict.RED_OVERLAP.value)
            raise FieldRunLockError(OvernightFieldRunVerdict.RED_OVERLAP.value)
    lock = FieldRunLock(field_run_id=field_run_id, pid=os.getpid(), started_at=now_iso())
    path.write_text(json.dumps(lock.to_payload(), indent=2) + "\n", encoding="utf-8")
    return lock


def release_field_run_lock(field_run_id: str, *, base: Path | None = None) -> None:
    path = lock_path(base=base)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("field_run_id") == field_run_id or _is_stale(data):
            data["state"] = "released"
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
