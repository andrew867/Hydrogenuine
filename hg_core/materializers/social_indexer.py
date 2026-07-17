"""
Social indexer: exposures (from RETRIEVAL_SET, READ), handoffs, availability, beliefs, escalations, conflicts, misalignments.
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
    exposures: List[Dict[str, Any]] = []
    handoffs: List[Dict[str, Any]] = []
    handoff_status: Dict[str, str] = {}
    availability: List[Dict[str, Any]] = []
    beliefs: List[Dict[str, Any]] = []
    escalations: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    misalignments: List[Dict[str, Any]] = []
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        agent_id = actor.get("agent_id", "")
        base = {"event_id": ev.get("event_id"), "ts": ts, "scope_type": scope_type, "scope_id": scope_id, "agent_id": agent_id}

        if action == "RETRIEVAL_SET":
            for ref_id in payload.get("top_k_ids", []) or payload.get("selected_ids", []):
                if ref_id:
                    exposures.append({
                        **base,
                        "ref_id": ref_id,
                        "ref_type": "entity",
                        "source": "RETRIEVAL_SET",
                    })
        elif action == "READ":
            obj = ev.get("object") or {}
            ref_id = obj.get("id", "")
            if ref_id:
                exposures.append({
                    **base,
                    "ref_id": ref_id,
                    "ref_type": "entity",
                    "source": "READ",
                })
        elif action == "HANDOFF_CREATED":
            handoffs.append({
                **base,
                "handoff_id": payload.get("handoff_id", ""),
                "from_agent_id": payload.get("from_agent_id", ""),
                "to_agent_id": payload.get("to_agent_id", ""),
                "work_item_ref": payload.get("work_item_ref", {}),
                "ownership_mode": payload.get("ownership_mode", ""),
                "expected_response_by": payload.get("expected_response_by", ""),
                "priority": payload.get("priority", ""),
                "status": "created",
            })
            handoff_status[payload.get("handoff_id", "")] = "created"
        elif action == "HANDOFF_ACCEPTED":
            for h in handoffs:
                if h.get("handoff_id") == payload.get("handoff_id"):
                    h["status"] = "accepted"
                    break
            handoff_status[payload.get("handoff_id", "")] = "accepted"
        elif action == "HANDOFF_REJECTED":
            for h in handoffs:
                if h.get("handoff_id") == payload.get("handoff_id"):
                    h["status"] = "rejected"
                    break
            handoff_status[payload.get("handoff_id", "")] = "rejected"
        elif action == "HANDOFF_COMPLETED":
            for h in handoffs:
                if h.get("handoff_id") == payload.get("handoff_id"):
                    h["status"] = "completed"
                    break
            handoff_status[payload.get("handoff_id", "")] = "completed"
        elif action == "AVAILABILITY_DECLARED":
            availability.append({
                **base,
                "agent_id": payload.get("agent_id", ""),
                "windows": payload.get("windows", []),
                "timezone": payload.get("timezone", ""),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
            })
        elif action == "BELIEF_MODEL_UPDATED":
            beliefs.append({
                **base,
                "belief_id": payload.get("belief_id", ""),
                "subject_agent_id": payload.get("subject_agent_id", ""),
                "claim_id": payload.get("claim_id"),
                "entity_id": payload.get("entity_id"),
                "confidence": payload.get("confidence"),
                "basis_refs": payload.get("basis_refs", []),
                "scope": payload.get("scope", {}),
            })
        elif action == "BELIEF_MODEL_OVERRIDDEN":
            beliefs.append({
                **base,
                "override_id": payload.get("override_id", ""),
                "subject_agent_id": payload.get("subject_agent_id", ""),
                "claim_id": payload.get("claim_id"),
                "entity_id": payload.get("entity_id"),
                "rationale_artifact_id": payload.get("rationale_artifact_id", ""),
                "is_override": True,
            })
        elif action == "ESCALATION_RAISED":
            escalations.append({
                **base,
                "handoff_id": payload.get("handoff_id"),
                "work_item_ref": payload.get("work_item_ref", {}),
                "reason": payload.get("reason", ""),
                "to_agent_id": payload.get("to_agent_id"),
            })
        elif action == "CONFLICT_DETECTED":
            conflicts.append({
                **base,
                "work_item_ref": payload.get("work_item_ref", {}),
                "agent_ids": payload.get("agent_ids", []),
                "trace": payload.get("trace", []),
            })
        elif action == "MISALIGNMENT_DETECTED":
            misalignments.append({
                **base,
                "misalignment_id": payload.get("misalignment_id", ""),
                "decision_id": payload.get("decision_id", ""),
                "agent_id": payload.get("agent_id", ""),
                "unexposed_claim_ids": payload.get("unexposed_claim_ids", []),
                "severity": payload.get("severity", "medium"),
            })

    with open(root / "exposures.jsonl", "w", encoding="utf-8") as f:
        for r in exposures:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "handoffs.jsonl", "w", encoding="utf-8") as f:
        for r in handoffs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "availability.jsonl", "w", encoding="utf-8") as f:
        for r in availability:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "beliefs.jsonl", "w", encoding="utf-8") as f:
        for r in beliefs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "escalations.jsonl", "w", encoding="utf-8") as f:
        for r in escalations:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "conflicts.jsonl", "w", encoding="utf-8") as f:
        for r in conflicts:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "misalignments.jsonl", "w", encoding="utf-8") as f:
        for r in misalignments:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "social", checkpoint)
