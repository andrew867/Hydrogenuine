"""
Affective/regulatory indexer: regulatory state snapshots (with evidence_refs), applied modulations, overrides.
From TRUST_BAND_CHANGED, BUDGET_ADJUSTED, ESCROW_*, EVALUATION_RECORDED (incident), MODULATION_APPLIED, REGULATORY_OVERRIDE_*.
Deterministic and rebuildable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, save_checkpoint


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    regulatory_snapshots: List[Dict[str, Any]] = []
    modulations: List[Dict[str, Any]] = []
    overrides: List[Dict[str, Any]] = []
    agent_state: Dict[str, Dict[str, Any]] = {}
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        agent_id = actor.get("agent_id", "")
        eid = ev.get("event_id", "")
        base = {"event_id": eid, "ts": ts, "scope_type": scope_type, "scope_id": scope_id, "agent_id": agent_id}

        if action == "MODULATION_APPLIED":
            modulations.append({
                **base,
                "modulation_id": payload.get("modulation_id", eid),
                "before_state": payload.get("before_state", {}),
                "after_state": payload.get("after_state", {}),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
            })
        elif action == "REGULATORY_OVERRIDE_APPLIED":
            overrides.append({
                **base,
                "override_id": payload.get("override_id", eid),
                "override_spec": payload.get("override_spec", {}),
                "expiry_ts": payload.get("expiry_ts", ""),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
                "revoked": False,
            })
        elif action == "REGULATORY_OVERRIDE_REVOKED":
            for o in overrides:
                if o.get("override_id") == payload.get("override_id"):
                    o["revoked"] = True
                    break
        elif agent_id and action in (
            "TRUST_BAND_CHANGED", "BUDGET_ADJUSTED",
            "ESCROW_LOCKED", "ESCROW_RELEASED", "ESCROW_SLASHED",
            "EVALUATION_RECORDED",
        ):
            key = (scope_type, scope_id, agent_id)
            if key not in agent_state:
                agent_state[key] = {"agency_budget": 0.0, "trust_band": 0, "escrow_locked": 0.0, "incident_points": 0.0}
            s = agent_state[key]
            if action == "TRUST_BAND_CHANGED":
                s["trust_band"] = int(payload.get("band", 0) or 0)
            elif action == "BUDGET_ADJUSTED":
                s["agency_budget"] = s.get("agency_budget", 0) + float(payload.get("delta", 0) or 0)
            elif action == "ESCROW_LOCKED":
                s["escrow_locked"] = s.get("escrow_locked", 0) + float(payload.get("amount", 0) or 0)
            elif action in ("ESCROW_RELEASED", "ESCROW_SLASHED"):
                s["escrow_locked"] = max(0, s.get("escrow_locked", 0) - float(payload.get("amount", 0) or 0))
                if action == "ESCROW_SLASHED":
                    s["incident_points"] = s.get("incident_points", 0) + 1
            elif action == "EVALUATION_RECORDED" and (payload.get("incident") or {}).get("raised"):
                s["incident_points"] = s.get("incident_points", 0) + 1
            regulatory_snapshots.append({
                "ts": ts,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "agent_id": agent_id,
                "trust_band": s["trust_band"],
                "agency_budget": s["agency_budget"],
                "escrow_locked": s["escrow_locked"],
                "incident_points": s["incident_points"],
                "evidence_refs": [eid],
            })

    with open(root / "regulatory_state_snapshots.jsonl", "w", encoding="utf-8") as f:
        for r in regulatory_snapshots:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "applied_modulations.jsonl", "w", encoding="utf-8") as f:
        for r in modulations:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "regulatory_overrides.jsonl", "w", encoding="utf-8") as f:
        for r in overrides:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "affective", checkpoint)
