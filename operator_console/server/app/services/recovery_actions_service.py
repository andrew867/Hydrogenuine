"""Recovery hub: aggregate stuck/failed work and record operator recovery actions to ledger + proof evidence."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root
        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _runtime_tenant_id() -> str:
    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _list_stuck_runs(stale_minutes: int = 30) -> List[Dict[str, Any]]:
    try:
        from ..services.run_index_db import list_runs
        from datetime import datetime, timezone, timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
        stuck: List[Dict[str, Any]] = []
        for row in list_runs(limit=500):
            status = str(row.get("status") or "").lower()
            if status not in ("running", "pending", "pending_approval"):
                continue
            started = row.get("started_at") or row.get("created_at")
            if not started:
                continue
            try:
                ts = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if ts < cutoff:
                stuck.append(dict(row))
        return stuck
    except Exception:
        return []


def _list_failed_runs(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        from ..services.run_index_db import list_runs

        failed: List[Dict[str, Any]] = []
        for row in list_runs(limit=limit):
            status = str(row.get("status") or "").lower()
            if status in ("failed", "error", "blocked", "cancelled"):
                failed.append(dict(row))
        return failed[:limit]
    except Exception:
        return []


def _list_tripped_breakers() -> List[Dict[str, Any]]:
    try:
        from hg_core.task_graph.circuit_breaker import CIRCUIT_BREAKER_DIR, _load_state

        root = _workspace_root()
        base = root / CIRCUIT_BREAKER_DIR
        if not base.exists():
            return []
        out: List[Dict[str, Any]] = []
        for p in base.iterdir():
            if p.is_file() and p.suffix == ".json":
                state = _load_state(p)
                if state.get("tripped_at"):
                    out.append({"workflow_id": p.stem, "destination": None, **state})
            elif p.is_dir():
                for f in p.glob("*.json"):
                    state = _load_state(f)
                    if state.get("tripped_at"):
                        out.append({"workflow_id": p.name, "destination": f.stem, **state})
        return out
    except Exception:
        return []


def build_recovery_summary(*, stale_minutes: int = 30) -> Dict[str, Any]:
    """Unified recovery surface payload."""
    stuck = _list_stuck_runs(stale_minutes=stale_minutes)
    failed = _list_failed_runs()
    breakers = _list_tripped_breakers()
    try:
        from hg_core.task_graph import operator_ux

        deadletter = operator_ux.get_dead_letter_queue(_workspace_root())
    except Exception:
        deadletter = []

    purge_audit: List[Dict[str, Any]] = []
    audit_path = _workspace_root() / "memory" / "automation" / "audit" / "purge_audit.jsonl"
    if audit_path.exists():
        try:
            lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-20:]):
                if line.strip():
                    purge_audit.append(json.loads(line))
        except Exception:
            purge_audit = []

    return {
        "ok": True,
        "generated_at": _iso_now(),
        "stuck_runs": stuck,
        "failed_runs": failed,
        "tripped_breakers": breakers,
        "incident_queue": deadletter,
        "recent_purge_audit": purge_audit,
        "counts": {
            "stuck": len(stuck),
            "failed": len(failed),
            "breakers": len(breakers),
            "incidents": len(deadletter),
        },
        "evidence_links": {
            "timeline": "#/timeline",
            "proofs": "#/proofs",
            "retention": "#/retention",
            "reliability": "#/reliability",
        },
    }


def _append_recovery_evidence(action: str, payload: Dict[str, Any]) -> Optional[str]:
    """Write recovery action to proof evidence dir for operator audit."""
    root = _workspace_root()
    evidence_dir = root / "docs" / "audits" / "recovery_actions"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = evidence_dir / f"{stamp}_{action}.json"
    record = {"recorded_at": _iso_now(), "action": action, **payload}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return str(path.relative_to(root)).replace("\\", "/")


def record_recovery_action(
    *,
    action: str,
    target_type: str,
    target_id: str,
    actor_id: str = "operator",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record operator recovery action to ledger and proof evidence."""
    payload = {
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "actor_id": actor_id,
        "tenant_id": _runtime_tenant_id(),
        "details": details or {},
        "recorded_at": _iso_now(),
    }
    event_id: Optional[str] = None
    try:
        from hg_core.ledger import emit

        event_id = emit(
            "OPERATOR_RECOVERY_ACTION",
            target_type,
            target_id,
            payload,
            scope={"type": "tenant", "id": _runtime_tenant_id()},
            actor={"agent_id": actor_id, "pubkey": "0", "key_id": "operator"},
            workspace_root=_workspace_root(),
        )
    except Exception:
        event_id = None

    evidence_path = _append_recovery_evidence(action, {**payload, "ledger_event_id": event_id})
    return {
        "ok": True,
        "event_id": event_id,
        "evidence_path": evidence_path,
        "payload": payload,
        "post_action_landing": "#/timeline",
    }
