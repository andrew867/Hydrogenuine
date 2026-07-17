"""Single-supervisor lock — one lease per run directory."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hg_runtime.bounded_soak.stop_panic_runtime import may_start_supervisor

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_LEASE_SECONDS = 120


def _lock_path(run_dir: Path) -> Path:
    return run_dir / "supervisor.lock"


def read_lock(run_dir: Path) -> dict[str, Any] | None:
    p = _lock_path(run_dir)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def acquire_supervisor_lock(
    run_dir: Path,
    *,
    supervisor_id: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    force_stale_recovery: bool = False,
    workspace: Path | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    ws = workspace or WORKSPACE
    ok, reason = may_start_supervisor(ws)
    if not ok:
        return False, reason, None

    run_dir.mkdir(parents=True, exist_ok=True)
    existing = read_lock(run_dir)
    now = datetime.now(timezone.utc)
    if existing:
        expires = existing.get("lease_expires_at")
        holder = existing.get("supervisor_id")
        if expires and holder != supervisor_id:
            try:
                exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
                if exp > now and not force_stale_recovery:
                    return False, "RED_MULTIPLE_SUPERVISORS_ALLOWED", existing
            except ValueError:
                pass
        elif holder == supervisor_id:
            pass
        elif not force_stale_recovery:
            return False, "RED_MULTIPLE_SUPERVISORS_ALLOWED", existing

    payload = {
        "schema": "supervisor-lock",
        "supervisor_id": supervisor_id,
        "pid": os.getpid(),
        "acquired_at": _now(),
        "heartbeat_at": _now(),
        "lease_expires_at": (now + timedelta(seconds=lease_seconds)).isoformat(),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    tmp = _lock_path(run_dir).with_suffix(".lock.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, _lock_path(run_dir))
    return True, "GREEN_SINGLE_SUPERVISOR_GUARD_READY", payload


def heartbeat_supervisor_lock(run_dir: Path, *, supervisor_id: str, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> bool:
    lock = read_lock(run_dir)
    if not lock or lock.get("supervisor_id") != supervisor_id:
        return False
    now = datetime.now(timezone.utc)
    lock["heartbeat_at"] = _now()
    lock["lease_expires_at"] = (now + timedelta(seconds=lease_seconds)).isoformat()
    _lock_path(run_dir).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def release_supervisor_lock(run_dir: Path, *, supervisor_id: str) -> bool:
    lock = read_lock(run_dir)
    if not lock or lock.get("supervisor_id") != supervisor_id:
        return False
    _lock_path(run_dir).unlink(missing_ok=True)
    return True


__all__ = ["acquire_supervisor_lock", "heartbeat_supervisor_lock", "read_lock", "release_supervisor_lock"]
