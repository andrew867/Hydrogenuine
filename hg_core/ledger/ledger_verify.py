"""
Verify ledger chain: signatures, prev_hash continuity, event_id recompute.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .event_envelope import compute_event_id, body_for_hash, verify_envelope
from .ledger_writer import get_scope_ledger_path, get_ledger_root, iterate_events, _iter_scope_paths


def verify_chain(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify events in scope (or all). Returns report with ok, errors, checked count.
    Checks: signature (if present), prev_hash continuity per scope file, event_id recompute.
    """
    report: Dict[str, Any] = {"ok": True, "errors": [], "checked": 0, "last_event_id": None}
    if scope_type is not None and scope_id is not None:
        paths = [(scope_type, scope_id, get_scope_ledger_path(workspace_root, scope_type, scope_id))]
        if not paths[0][2].exists():
            return report
    else:
        paths = [(st, sid, p) for st, sid, p in _iter_scope_paths(workspace_root)]
    for st, sid, path in paths:
        prev_hash: Optional[str] = None
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                report["checked"] += 1
                if ev.get("prev_hash") != prev_hash:
                    report["ok"] = False
                    report["errors"].append({
                        "event_id": ev.get("event_id"),
                        "scope": (st, sid),
                        "issue": "prev_hash_mismatch",
                        "expected": prev_hash,
                        "got": ev.get("prev_hash"),
                    })
                body = body_for_hash(ev)
                if compute_event_id(body) != ev.get("event_id"):
                    report["ok"] = False
                    report["errors"].append({
                        "event_id": ev.get("event_id"),
                        "issue": "event_id_mismatch",
                    })
                if not verify_envelope(ev):
                    report["ok"] = False
                    report["errors"].append({
                        "event_id": ev.get("event_id"),
                        "issue": "signature_invalid",
                    })
                prev_hash = ev.get("event_id")
                report["last_event_id"] = ev.get("event_id")
    return report


def get_event(workspace_root: Path, event_id: str) -> Optional[Dict[str, Any]]:
    """Return first event with given event_id from any scope file, or None."""
    for ev in iterate_events(workspace_root):
        if ev.get("event_id") == event_id:
            return ev
    return None
