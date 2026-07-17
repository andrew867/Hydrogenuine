"""
Ch7 API: list audit events, export audit bundle (emit AUDIT_BUNDLE_EXPORTED).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def list_audit_events(
    workspace_root: Path,
    action_filter: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List audit events from materialized audit_events.jsonl (after extras indexer run)."""
    root = _materialized_root(Path(workspace_root))
    path = root / "audit_events.jsonl"
    rows = _load_jsonl(path)
    if action_filter:
        rows = [r for r in rows if r.get("action") == action_filter]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]


def export_audit_bundle(
    *,
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    bundle_path: Optional[str] = None,
) -> str:
    """Write audit bundle artifact (summary of audit events + optional exports), emit AUDIT_BUNDLE_EXPORTED. Returns event_id."""
    workspace_root = Path(workspace_root)
    root = _materialized_root(workspace_root)
    events = _load_jsonl(root / "audit_events.jsonl")[-500:]
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    bundle = {"exported_at": ts, "scope": scope, "event_count": len(events), "events": events}
    if not bundle_path:
        art_root = workspace_root / "artifacts" / "audit"
        art_root.mkdir(parents=True, exist_ok=True)
        date_prefix = ts[:10]
        bundle_path = f"artifacts/audit/{date_prefix}/bundle_{hashlib.sha256(ts.encode()).hexdigest()[:12]}.json"
    full = workspace_root / bundle_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    obj_id = "bundle_" + hashlib.sha256(bundle_path.encode()).hexdigest()[:16]
    payload = {"bundle_path": bundle_path, "event_count": len(events)}
    return emit(
        "AUDIT_BUNDLE_EXPORTED",
        "audit_bundle",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
