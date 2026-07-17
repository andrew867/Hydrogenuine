"""
Time-bound exceptions (Pack 4): grant_exception, check_exception_expired.
EXCEPTION_GRANTED, EXCEPTION_EXPIRED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def grant_exception(
    *,
    scope: Dict[str, str],
    expiry_ts: str,
    refs: List[Dict[str, Any]],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    reason: str = "",
) -> str:
    """
    Emit EXCEPTION_GRANTED with scope and expiry. refs can link to conflict_id, approval_id, etc.
    Returns exception_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    exception_id = "ex_" + hashlib.sha256(f"{scope.get('id','')}:{expiry_ts}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "exceptions"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{exception_id}.json"
    path.write_text(
        json.dumps({
            "exception_id": exception_id,
            "scope": scope,
            "expiry_ts": expiry_ts,
            "refs": refs,
            "reason": reason,
            "granted_ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    emit(
        "EXCEPTION_GRANTED",
        "exception",
        exception_id,
        {
            "exception_id": exception_id,
            "scope": scope,
            "expiry_ts": expiry_ts,
            "refs": refs,
            "artifact_id": str(path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return exception_id


def check_exception_expired(
    *,
    exception_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> bool:
    """
    If the exception artifact exists and expiry_ts is in the past, emit EXCEPTION_EXPIRED and return True.
    Otherwise return False.
    """
    workspace_root = Path(workspace_root or ".")
    root = workspace_root / "artifacts" / "exceptions"
    path = root / f"{exception_id}.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    expiry = data.get("expiry_ts") or ""
    if not expiry:
        return False
    try:
        exp_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    except ValueError:
        return False
    now = datetime.now(timezone.utc)
    if exp_dt.tzinfo is None:
        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
    if now < exp_dt:
        return False
    ts = _iso_ts()
    emit(
        "EXCEPTION_EXPIRED",
        "exception",
        exception_id,
        {"exception_id": exception_id, "expiry_ts": expiry, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True
