"""
Rebuild and verify: rebuild all materializers, verify ledger chain, verify artifact checksums, materializer status.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_verify import verify_chain
from hg_core.ledger.ledger_writer import iter_events_by_scope
from hg_core.materializers import run_all
from hg_core.materializers._checkpoint import get_materialized_root, load_checkpoint


def rebuild_all_materializers(workspace_root: Path, scope: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Rebuild all materializers from scratch. scope optional for future per-scope rebuild. Returns summary."""
    workspace_root = Path(workspace_root)
    run_all(workspace_root, rebuild=True)
    return {"ok": True, "message": "rebuild completed", "scope": scope}


def verify_ledger_chain(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify ledger chain integrity (signatures, prev_hash, event_id). Returns report with ok, errors, checked."""
    return verify_chain(workspace_root, scope_type=scope_type, scope_id=scope_id)


def verify_artifact_checksums(workspace_root: Path, limit: int = 500) -> Dict[str, Any]:
    """Verify artifact checksums vs ledger references (payload_ref.checksum, ARTIFACT_PUBLISH.checksum). Returns report."""
    workspace_root = Path(workspace_root)
    report: Dict[str, Any] = {"ok": True, "checked": 0, "mismatches": [], "missing": []}
    seen = set()
    for _scope_type, _scope_id, ev in iter_events_by_scope(workspace_root):
        if report["checked"] >= limit:
            break
        payload = ev.get("payload") or {}
        checksum = payload.get("checksum")
        path = payload.get("path") or (payload.get("payload_ref") or {}).get("path")
        if not path or not checksum:
            continue
        if path in seen:
            continue
        seen.add(path)
        full_path = workspace_root / path if not Path(path).is_absolute() else Path(path)
        if not full_path.exists():
            report["missing"].append({"path": path, "event_id": ev.get("event_id")})
            report["ok"] = False
            report["checked"] += 1
            continue
        try:
            data = full_path.read_bytes()
            computed = hashlib.sha256(data).hexdigest()
            if computed != checksum:
                report["mismatches"].append({"path": path, "expected": checksum, "computed": computed})
                report["ok"] = False
        except Exception as e:
            report["mismatches"].append({"path": path, "error": str(e)})
            report["ok"] = False
        report["checked"] += 1
    return report


def get_materializer_status(workspace_root: Path) -> Dict[str, Any]:
    """Return last checkpoint per materializer and optional lag. Uses checkpoint files in memory/materialized/checkpoints."""
    root = get_materialized_root(Path(workspace_root))
    checkpoints_dir = root / "checkpoints"
    status: Dict[str, Any] = {"materializers": {}, "ok": True}
    if not checkpoints_dir.exists():
        return status
    for cp_file in sorted(checkpoints_dir.glob("*.json")):
        name = cp_file.stem
        try:
            with open(cp_file, encoding="utf-8") as f:
                data = json.load(f)
            status["materializers"][name] = {"last_checkpoint": data, "scopes": list(data.keys())}
        except Exception as e:
            status["materializers"][name] = {"error": str(e)}
            status["ok"] = False
    return status
