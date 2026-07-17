"""
Cancel request helper for DAG runs.

The executor checks for a cancel request file in run_dir and exits cleanly.
Operator APIs can create the file to interrupt in-progress runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

CANCEL_REQUEST_FILENAME = "cancel.requested.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def cancel_request_path(run_dir: Optional[Path]) -> Optional[Path]:
    """Return run_dir/cancel.requested.json when run_dir is provided."""
    if not run_dir:
        return None
    return Path(run_dir) / CANCEL_REQUEST_FILENAME


def write_cancel_request(
    run_dir: Path,
    run_id: str,
    reason: str = "",
    source: str = "",
) -> dict:
    """Write cancel.requested.json in run_dir and return payload."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "requested_at": _iso_now(),
        "reason": reason or "",
        "source": source or "",
    }
    path = cancel_request_path(run_dir)
    if path is not None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def read_cancel_request(run_dir: Optional[Path]) -> Optional[dict[str, Any]]:
    """Read cancel.requested.json if present; return None when missing or invalid."""
    path = cancel_request_path(run_dir)
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"requested_at": _iso_now()}


def is_cancel_requested(run_dir: Optional[Path]) -> Tuple[bool, Optional[dict[str, Any]]]:
    """Return (True, payload) if cancel request file exists; else (False, None)."""
    payload = read_cancel_request(run_dir)
    if payload is None:
        return False, None
    return True, payload
