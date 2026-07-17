"""
Distributed lock for (workflow_id, time_bucket) (Q1).

File-based lock: acquire before run, release on completion. TTL covers run + buffer.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

RUN_LOCK_DIR = "memory/automation/run_locks"
DEFAULT_LOCK_TTL_SEC = 3600  # 1 hour


def _lock_path(workspace_root: Path, workflow_id: str, time_bucket: str) -> Path:
    safe_w = workflow_id.replace("/", "_").replace("\\", "_")
    safe_b = time_bucket.replace("/", "_").replace(":", "-")
    return workspace_root / RUN_LOCK_DIR / f"{safe_w}_{safe_b}.lock"


def acquire_lock(
    workspace_root: Path,
    workflow_id: str,
    time_bucket: str,
    run_id: str,
    ttl_sec: int = DEFAULT_LOCK_TTL_SEC,
) -> bool:
    """
    Acquire lock for (workflow_id, time_bucket). Returns True if acquired, False if already held.
    Lock file contains run_id and expires_at; if file exists and not expired, return False.
    """
    path = _lock_path(workspace_root, workflow_id, time_bucket)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            expires_at = data.get("expires_at", 0)
            if time.time() < expires_at:
                return False
        except (json.JSONDecodeError, OSError):
            pass
    data = {
        "workflow_id": workflow_id,
        "time_bucket": time_bucket,
        "run_id": run_id,
        "acquired_at": time.time(),
        "expires_at": time.time() + ttl_sec,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True


def release_lock(workspace_root: Path, workflow_id: str, time_bucket: str) -> None:
    """Release lock for (workflow_id, time_bucket) by removing lock file."""
    path = _lock_path(workspace_root, workflow_id, time_bucket)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def apply_jitter_sec(scheduled_sec: float, jitter_sec: float) -> float:
    """
    Q3: Apply jitter to scheduled time. Returns scheduled_sec + random in [-jitter_sec, +jitter_sec].
    """
    import random
    delta = random.uniform(-jitter_sec, jitter_sec)
    return max(0.0, scheduled_sec + delta)
