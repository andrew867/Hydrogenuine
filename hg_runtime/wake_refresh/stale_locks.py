"""Stale lock detection."""

from __future__ import annotations

import time
from pathlib import Path

from hg_runtime.wake_refresh.boot_hygiene import WORKSPACE, normalize_rel
from hg_runtime.wake_refresh.schema import StaleLockFinding

LOCK_DIR = WORKSPACE / ".hg-local" / "runtime_locks"
STALE_LOCK_AGE_S = 3600


def detect_stale_locks(*, workspace: Path | None = None, max_age_seconds: float = STALE_LOCK_AGE_S) -> list[StaleLockFinding]:
    ws = workspace or WORKSPACE
    lock_dir = ws / ".hg-local" / "runtime_locks"
    findings: list[StaleLockFinding] = []
    if not lock_dir.is_dir():
        return findings
    now = time.time()
    for path in lock_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age >= max_age_seconds:
            findings.append(
                StaleLockFinding(
                    path=normalize_rel(path, ws),
                    lock_age_seconds=age,
                    detail=f"lock older than {max_age_seconds}s",
                )
            )
    # Also check runtime panic marker as stale lock class
    panic = ws / ".hg-local" / "runtime" / "agent0_dev_boot.panic"
    if panic.is_file():
        try:
            age = now - panic.stat().st_mtime
            if age >= max_age_seconds:
                findings.append(StaleLockFinding(path=normalize_rel(panic, ws), lock_age_seconds=age, detail="stale panic marker"))
        except OSError:
            pass
    return findings


__all__ = ["STALE_LOCK_AGE_S", "detect_stale_locks"]
