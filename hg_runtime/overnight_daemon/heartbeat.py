"""Heartbeat file — updated at least every 60s, before/after LM Studio calls."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _elapsed_from_started(started_at: str) -> float:
    try:
        import calendar
        ts = calendar.timegm(time.strptime(started_at, "%Y-%m-%dT%H:%M:%SZ"))
        return max(0.0, time.time() - ts)
    except (ValueError, OverflowError):
        return 0.0


def heartbeat_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / "heartbeat.json"


def write_heartbeat(state_dir: str | Path, *, run_id: str, pid: int,
                    started_at: str, cycle_count: int = 0,
                    current_seed_id: str = "", current_task_id: str = "",
                    current_model: str = "", current_status: str = "running",
                    current_verdict_so_far: str = "YELLOW_IN_PROGRESS",
                    last_checkin_path: str = "", proof_path: str = "",
                    stop_requested: bool = False, panic_requested: bool = False,
                    fatal_error: str = "", receipt_count: int = 0,
                    boundary_violation_count: int = 0) -> dict:
    hb = {
        "run_id": run_id,
        "pid": pid,
        "started_at": started_at,
        "last_heartbeat_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": _elapsed_from_started(started_at),
        "cycle_count": cycle_count,
        "current_seed_id": current_seed_id,
        "current_task_id": current_task_id,
        "current_model": current_model,
        "current_status": current_status,
        "current_verdict_so_far": current_verdict_so_far,
        "last_checkin_path": last_checkin_path,
        "proof_path": proof_path,
        "stop_requested": stop_requested,
        "panic_requested": panic_requested,
        "fatal_error": fatal_error,
        "receipt_count": receipt_count,
        "boundary_violation_count": boundary_violation_count,
    }
    p = heartbeat_path(state_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(hb, indent=2), encoding="utf-8")
    return hb


def read_heartbeat(state_dir: str | Path) -> dict | None:
    p = heartbeat_path(state_dir)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def heartbeat_age_seconds(state_dir: str | Path) -> float | None:
    hb = read_heartbeat(state_dir)
    if hb is None:
        return None
    try:
        import calendar
        ts = calendar.timegm(time.strptime(hb["last_heartbeat_at"], "%Y-%m-%dT%H:%M:%SZ"))
        return time.time() - ts
    except (KeyError, ValueError):
        return None


def is_stale(state_dir: str | Path, threshold_seconds: float = 120.0) -> bool:
    age = heartbeat_age_seconds(state_dir)
    if age is None:
        return True
    return age > threshold_seconds
