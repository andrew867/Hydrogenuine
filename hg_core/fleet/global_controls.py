"""Global emergency controls: preflight, apply with quorum and expiry."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit

KINDS = frozenset({"freeze_writes", "read_only", "isolate_connectors", "pause_subset"})


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _mat(ws: Path) -> Path:
    return Path(ws) / "memory" / "materialized"


def _ctl_root(ws: Path) -> Path:
    return Path(ws) / "artifacts" / "fleet" / "global_controls"


def _jl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def preflight_global_control(workspace_root: Path, kind: str, scope: Dict[str, str], params: Optional[Dict[str, Any]] = None, quorum_threshold: float = 0.5) -> Dict[str, Any]:
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        return {"allowed": False, "reason": "invalid_kind", "quorum_required": True}
    return {"allowed": True, "reason": "", "quorum_required": True, "proof_ref": "preflight_ok"}


def apply_global_control(
    kind: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    expiry_hours: int = 1,
    rationale_artifact_id: str = "",
    params: Optional[Dict[str, Any]] = None,
    quorum_approved: bool = True,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    ws = Path(workspace_root or ".")
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        return {"control_id": "", "event_id": "", "applied": False, "reason": "invalid_kind"}
    ts = _ts()
    expiry_ts = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat().replace("+00:00", "Z")
    control_id = "gc_" + hashlib.sha256(f"{kind}:{ts}".encode()).hexdigest()[:16]
    if not quorum_approved:
        eid = emit("GLOBAL_CONTROL_DENIED", "global_control", control_id, {"control_id": control_id, "kind": kind, "scope": scope, "ts": ts, "reason": "quorum_not_met"}, scope=scope, actor=actor, workspace_root=ws)
        return {"control_id": control_id, "event_id": eid, "applied": False, "reason": "quorum_not_met"}
    root = _ctl_root(ws)
    root.mkdir(parents=True, exist_ok=True)
    doc = {"control_id": control_id, "scope": scope, "kind": kind, "ts": ts, "expiry_ts": expiry_ts, "rationale_artifact_id": rationale_artifact_id or "", "params": params or {}}
    path = root / f"{control_id}.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    eid = emit("GLOBAL_CONTROL_APPLIED", "global_control", control_id, {"control_id": control_id, "kind": kind, "scope": scope, "ts": ts, "expiry_ts": expiry_ts, "rationale_artifact_id": rationale_artifact_id or "", "artifact_path": str(path), "params": params or {}}, scope=scope, actor=actor, workspace_root=ws)
    mat = _mat(ws)
    mat.mkdir(parents=True, exist_ok=True)
    with open(mat / "global_controls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"control_id": control_id, "kind": kind, "expiry_ts": expiry_ts, "ts": ts}, ensure_ascii=False) + "\n")
    return {"control_id": control_id, "event_id": eid, "applied": True}


def list_active_global_controls(workspace_root: Path) -> List[Dict[str, Any]]:
    rows = _jl(_mat(Path(workspace_root)) / "global_controls.jsonl")
    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        ex = r.get("expiry_ts")
        if ex:
            try:
                if datetime.fromisoformat(ex.replace("Z", "+00:00")) <= now:
                    continue
            except Exception:
                pass
        out.append(r)
    return out
