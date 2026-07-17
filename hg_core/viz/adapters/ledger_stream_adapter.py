"""
Viz Phase 2: Ledger stream view (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_writer import iterate_events


def adapt_ledger_stream(
    workspace_root: Path,
    limit: int = 100,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return ledger events as a chronological stream: { items, has_more }.
    Each item: event_id, action, ts, scope, payload_summary (optional).
    """
    root = Path(workspace_root)
    items: List[Dict[str, Any]] = []
    for ev in iterate_events(root, scope_type=scope_type, scope_id=scope_id):
        if len(items) >= limit:
            break
        payload = ev.get("payload") or {}
        payload_summary = payload.get("payload_summary") if isinstance(payload.get("payload_summary"), dict) else None
        items.append({
            "event_id": ev.get("event_id"),
            "action": ev.get("action", ""),
            "ts": ev.get("ts", ""),
            "scope": ev.get("scope") or {},
            "payload_summary": payload_summary,
        })
    return {"items": items, "has_more": len(items) >= limit}
