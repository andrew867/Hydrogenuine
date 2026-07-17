"""
Regulatory state snapshot: evidence-derived (from ledger); no self-report.
Reads from materialized agent_state_snapshots (reputation) or regulatory_state_snapshots (affective indexer).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
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


def get_regulatory_state_snapshot(
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    agent_id: Optional[str] = None,
    at_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return regulatory state snapshot from evidence (materialized).
    Prefer regulatory_state_snapshots.jsonl if present (has evidence_refs); else use agent_state_snapshots (reputation).
    If at_ts given, return latest snapshot with ts <= at_ts.
    """
    workspace_root = Path(workspace_root)
    root = _materialized_root(workspace_root)
    reg_path = root / "regulatory_state_snapshots.jsonl"
    if reg_path.exists():
        rows = _load_jsonl(reg_path)
        rows = [r for r in rows if r.get("scope_type") == scope_type and r.get("scope_id") == scope_id]
        if agent_id:
            rows = [r for r in rows if r.get("agent_id") == agent_id]
        if at_ts:
            rows = [r for r in rows if (r.get("ts") or "") <= at_ts]
        if not rows:
            return {"scope_type": scope_type, "scope_id": scope_id, "agent_id": agent_id, "state": {}, "evidence_refs": []}
        latest = max(rows, key=lambda r: r.get("ts", ""))
        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "agent_id": latest.get("agent_id"),
            "ts": latest.get("ts"),
            "state": {
                "trust_band": latest.get("trust_band", 0),
                "agency_budget": latest.get("agency_budget", 0.0),
                "escrow_locked": latest.get("escrow_locked", 0.0),
                "incident_points": latest.get("incident_points", 0.0),
            },
            "evidence_refs": latest.get("evidence_refs", []),
        }
    rep_path = root / "agent_state_snapshots.jsonl"
    if rep_path.exists():
        rows = _load_jsonl(rep_path)
        if agent_id:
            rows = [r for r in rows if r.get("agent_id") == agent_id]
        if at_ts:
            rows = [r for r in rows if (r.get("ts") or "") <= at_ts]
        if not rows:
            return {"scope_type": scope_type, "scope_id": scope_id, "agent_id": agent_id, "state": {"trust_band": 0, "agency_budget": 0.0, "escrow_locked": 0.0, "incident_points": 0.0}, "evidence_refs": []}
        latest = max(rows, key=lambda r: r.get("ts", ""))
        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "agent_id": latest.get("agent_id"),
            "ts": latest.get("ts"),
            "state": {
                "trust_band": latest.get("trust_band", 0),
                "agency_budget": latest.get("agency_budget", 0.0),
                "escrow_locked": latest.get("escrow_locked", 0.0),
                "incident_points": latest.get("incident_points", 0.0),
            },
            "evidence_refs": [],
        }
    return {"scope_type": scope_type, "scope_id": scope_id, "agent_id": agent_id, "state": {}, "evidence_refs": []}
