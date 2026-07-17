"""
Facts↔meaning bridge: explain_decision, compare_decisions from ledger + materialized views.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .ledger_writer import iterate_events


def explain_decision(
    decision_id: str,
    workspace_root: Path,
) -> Dict[str, Any]:
    """
    Return claims + value weights + context refs + produced artifacts for a decision.
    Reads from ledger (DECISION_COMMITTED/DECISION_PROPOSED) only.
    """
    out: Dict[str, Any] = {
        "decision_id": decision_id,
        "based_on_claim_ids": [],
        "value_weights": [],
        "context_ref": {},
        "produced_artifact_ids": [],
        "title": "",
        "event_id": None,
    }
    for ev in iterate_events(workspace_root):
        if ev.get("action") not in ("DECISION_COMMITTED", "DECISION_PROPOSED"):
            continue
        payload = ev.get("payload") or {}
        if payload.get("decision_id") != decision_id and ev.get("object", {}).get("id") != decision_id:
            continue
        out["based_on_claim_ids"] = payload.get("based_on_claim_ids", [])
        out["value_weights"] = payload.get("value_weights", [])
        out["context_ref"] = payload.get("context_ref", {})
        out["produced_artifact_ids"] = payload.get("produced_artifact_ids", [])
        out["title"] = payload.get("title", "")
        out["event_id"] = ev.get("event_id")
        break
    return out


def compare_decisions(
    decision_id_a: str,
    decision_id_b: str,
    workspace_root: Path,
) -> Dict[str, Any]:
    """
    Compare two decisions: overlapping claims and value weight diffs.
    """
    a = explain_decision(decision_id_a, workspace_root)
    b = explain_decision(decision_id_b, workspace_root)
    claims_a = set(a.get("based_on_claim_ids", []))
    claims_b = set(b.get("based_on_claim_ids", []))
    overlapping = list(claims_a & claims_b)
    weights_a = {w["dimension"]: w["weight"] for w in (a.get("value_weights") or []) if isinstance(w, dict) and "dimension" in w}
    weights_b = {w["dimension"]: w["weight"] for w in (b.get("value_weights") or []) if isinstance(w, dict) and "dimension" in w}
    dims = sorted(set(weights_a) | set(weights_b))
    value_diffs = []
    for d in dims:
        va = weights_a.get(d, 0)
        vb = weights_b.get(d, 0)
        if va != vb:
            value_diffs.append({"dimension": d, "weight_a": va, "weight_b": vb, "diff": vb - va})
    return {
        "decision_id_a": decision_id_a,
        "decision_id_b": decision_id_b,
        "overlapping_claim_ids": overlapping,
        "value_weight_diffs": value_diffs,
        "same_facts_different_action": len(overlapping) > 0 and value_diffs != [],
    }


def explain_message_provenance(
    *,
    message_id: str,
    chat_id: str,
    role: str,
    content: str = "",
    turn_provenance: Optional[Dict[str, Any]] = None,
    retrieval_sources: Optional[List[Dict[str, Any]]] = None,
    evidence_rows: Optional[List[Dict[str, Any]]] = None,
    reflection_ids: Optional[List[str]] = None,
    mirrored_from: Optional[str] = None,
    policy_notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a structured provenance explanation for a message/reply.

    This is intentionally DTO-shaped so callers can combine prompt/model provenance,
    retrieval cards, evidence rows, and policy notes without each UI rebuilding the
    same grouping rules.
    """
    retrieval_sources = [item for item in (retrieval_sources or []) if isinstance(item, dict)]
    evidence_rows = [item for item in (evidence_rows or []) if isinstance(item, dict)]
    reflection_ids = [str(item).strip() for item in (reflection_ids or []) if str(item).strip()]
    policy_notes = [str(item).strip() for item in (policy_notes or []) if str(item).strip()]

    policy_group: List[Dict[str, Any]] = []
    if isinstance(turn_provenance, dict):
        prompt_id = str(turn_provenance.get("prompt_id") or "").strip()
        model_config_id = str(turn_provenance.get("model_config_id") or "").strip()
        sampling_params = turn_provenance.get("sampling_params") if isinstance(turn_provenance.get("sampling_params"), dict) else {}
        if prompt_id:
            policy_group.append({"kind": "prompt", "label": "Prompt", "value": prompt_id})
        if model_config_id:
            policy_group.append({"kind": "model_config", "label": "Model config", "value": model_config_id})
        if sampling_params:
            policy_group.append({"kind": "sampling", "label": "Sampling", "value": sampling_params})

    evidence_group: List[Dict[str, Any]] = []
    for row in evidence_rows[:12]:
        evidence_group.append(
            {
                "ledger_id": row.get("ledger_id"),
                "timestamp": row.get("ts"),
                "evidence_type": row.get("evidence_type"),
                "approval_id": row.get("approval_id"),
                "content_ref": row.get("content_ref"),
            }
        )

    inference_group: List[Dict[str, Any]] = []
    if content.strip():
        inference_group.append({"kind": "reply", "label": "Reply content", "value": content[:240]})

    user_mirroring_group: List[Dict[str, Any]] = []
    if mirrored_from:
        user_mirroring_group.append({"kind": "mirror", "label": "Mirrors", "value": mirrored_from})

    if policy_notes:
        inference_group.extend({"kind": "policy_note", "label": "Policy note", "value": note} for note in policy_notes[:4])
    if reflection_ids:
        inference_group.extend({"kind": "reflection", "label": "Reflection artifact", "value": artifact_id} for artifact_id in reflection_ids[:4])

    why_parts: List[str] = []
    if retrieval_sources:
        why_parts.append(f"{len(retrieval_sources)} retrieval source(s)")
    if policy_group:
        why_parts.append("prompt/model binding")
    if evidence_group:
        why_parts.append(f"{len(evidence_group)} evidence row(s)")
    if reflection_ids:
        why_parts.append(f"{len(reflection_ids)} reflection artifact(s)")
    if mirrored_from:
        why_parts.append(f"mirrors {mirrored_from}")
    if policy_notes:
        why_parts.append(policy_notes[0])

    why = " · ".join(why_parts) if why_parts else "No explicit provenance edges were recorded."

    return {
        "message_id": message_id,
        "chat_id": chat_id,
        "role": role,
        "why": why,
        "turn_provenance": turn_provenance if isinstance(turn_provenance, dict) else None,
        "source_groups": {
            "retrieval": retrieval_sources,
            "policy": policy_group,
            "evidence": evidence_group,
            "reflection": [{"kind": "reflection", "label": "Reflection artifact", "value": artifact_id} for artifact_id in reflection_ids],
            "user_mirroring": user_mirroring_group,
            "inference": inference_group,
        },
    }
