"""Ch4 Audit log: append-only JSONL for privileged actions (who, when, what, why)."""

import json
import os
import time
from pathlib import Path
from typing import Any

from hg_gateway.shared_storage import append_audit_entry, use_shared_gateway_db


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def get_audit_path() -> Path | None:
    """Path to audit log file (memory/overseer/audit_log.jsonl or HG_AUDIT_LOG_PATH)."""
    p = os.getenv("HG_AUDIT_LOG_PATH")
    if p:
        return Path(p)
    root = _workspace_root()
    if not root:
        return None
    return root / "memory" / "overseer" / "audit_log.jsonl"


def append_audit(role: str, action: str, resource_id: str, details: dict[str, Any] | None = None) -> None:
    """Append one audit record (who, when, what, why)."""
    append_audit_entry(role, action, resource_id, details)
    path = get_audit_path()
    if not path:
        return
    if use_shared_gateway_db(path):
        return
    entry = {
        "role": role,
        "action": action,
        "resource_id": resource_id,
        "timestamp": time.time(),
        "details": details or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
