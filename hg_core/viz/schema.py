"""
Visualization Phase 1: Unified schema for viz nodes, edges, and evidence_refs.
Read-only; used by viz API and adapters.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Node types in the unified viz schema
VIZ_NODE_TYPES = ("work_item", "decision", "incident", "handoff", "claim", "agent", "run", "artifact", "event")

# Edge types
VIZ_EDGE_TYPES = ("based_on", "links_to", "evidence", "work_item", "owns", "references")


def evidence_ref(ref_id: str, ref_type: str = "event_id", artifact_id: str = "") -> Dict[str, Any]:
    """Build a single evidence_ref entry for the unified schema."""
    out: Dict[str, Any] = {"id": ref_id}
    if ref_type:
        out["type"] = ref_type
    if artifact_id:
        out["artifact_id"] = artifact_id
    return out


def normalize_evidence_refs(raw: List[Any]) -> List[Dict[str, Any]]:
    """Normalize raw evidence_refs (string or dict) to list of {id, type?, artifact_id?}."""
    out: List[Dict[str, Any]] = []
    for r in raw or []:
        if isinstance(r, str):
            out.append(evidence_ref(r, "event_id"))
        elif isinstance(r, dict) and r.get("id"):
            out.append(evidence_ref(r["id"], r.get("type", "event_id"), r.get("artifact_id", "")))
        elif isinstance(r, dict):
            out.append(evidence_ref(r.get("event_id", ""), "event_id", r.get("artifact_id", "")))
    return out


def viz_node(node_id: str, node_type: str, attrs: Dict[str, Any], evidence_refs: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Build a unified viz node."""
    out: Dict[str, Any] = {"id": node_id, "type": node_type, **attrs}
    if evidence_refs:
        out["evidence_refs"] = evidence_refs
    return out


def viz_edge(from_id: str, to_id: str, edge_type: str, evidence_refs: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Build a unified viz edge."""
    out: Dict[str, Any] = {"from": from_id, "to": to_id, "type": edge_type}
    if evidence_refs:
        out["evidence_refs"] = evidence_refs
    return out
