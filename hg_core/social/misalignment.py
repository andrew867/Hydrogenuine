"""
Misalignment detection: compare decisions' based_on_claim_ids to exposure graph; emit MISALIGNMENT_DETECTED when agent acted on unexposed claim.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iterate_events


def _exposure_set(exposures: List[Dict[str, Any]], scope_type: str, scope_id: str) -> Dict[str, Set[str]]:
    """Return dict: agent_id -> set of ref_ids (claim/entity) that agent was exposed to in scope."""
    by_agent: Dict[str, Set[str]] = {}
    for e in exposures:
        if e.get("scope_type") != scope_type or e.get("scope_id") != scope_id:
            continue
        agent_id = e.get("agent_id", "")
        ref_id = e.get("ref_id", "") or e.get("entity_id", "") or e.get("claim_id", "")
        if not agent_id or not ref_id:
            continue
        if agent_id not in by_agent:
            by_agent[agent_id] = set()
        by_agent[agent_id].add(ref_id)
    return by_agent


def detect_misalignments(
    workspace_root: Path,
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    severity: str = "medium",
) -> List[str]:
    """
    Load exposures and decisions from the ledger stream; for each decision where agent cited based_on_claim_ids,
    check that every claim_id was in that agent's exposure set. If not, emit MISALIGNMENT_DETECTED.
    Returns list of emitted misalignment event ids.
    """
    workspace_root = Path(workspace_root)
    scope_type = scope.get("type", "global")
    scope_id = scope.get("id", "default")
    exposures: List[Dict[str, Any]] = []
    for ev in iterate_events(workspace_root):
        action = ev.get("action") or ""
        payload = ev.get("payload") or {}
        if ev.get("scope", {}).get("type") != scope_type or ev.get("scope", {}).get("id") != scope_id:
            continue
        agent_id = (ev.get("actor") or {}).get("agent_id", "")
        if action == "RETRIEVAL_SET":
            for ref_id in payload.get("top_k_ids", []) or payload.get("selected_ids", []):
                if ref_id:
                    exposures.append({
                        "scope_type": scope_type,
                        "scope_id": scope_id,
                        "agent_id": agent_id,
                        "ref_id": ref_id,
                        "ref_type": "entity",
                    })
        elif action == "READ":
            obj = ev.get("object") or {}
            ref_id = obj.get("id", "")
            if ref_id:
                exposures.append({
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "agent_id": agent_id,
                    "ref_id": ref_id,
                    "ref_type": "entity",
                })
    by_agent = _exposure_set(exposures, scope_type, scope_id)
    emitted: List[str] = []
    for ev in iterate_events(workspace_root, action="DECISION_COMMITTED"):
        dec = ev.get("payload") or {}
        if ev.get("scope", {}).get("type") != scope_type or ev.get("scope", {}).get("id") != scope_id:
            continue
        agent_id = (ev.get("actor") or {}).get("agent_id", "") or dec.get("agent_id", "")
        claim_ids = dec.get("based_on_claim_ids") or []
        if not claim_ids:
            continue
        exposed = by_agent.get(agent_id, set())
        unexposed = [c for c in claim_ids if c and c not in exposed]
        if not unexposed:
            continue
        decision_id = dec.get("decision_id") or (ev.get("object") or {}).get("id") or ev.get("event_id", "")
        misalign_id = f"misalign_{decision_id}_{agent_id}"[:64]
        emit(
            "MISALIGNMENT_DETECTED",
            "misalignment",
            misalign_id,
            {
                "misalignment_id": misalign_id,
                "decision_id": decision_id,
                "agent_id": agent_id,
                "unexposed_claim_ids": unexposed,
                "severity": severity,
            },
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        emitted.append(misalign_id)
    return emitted
