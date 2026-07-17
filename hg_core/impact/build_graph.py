"""
Impact graph: build from materialized views and ledger refs; dependency closure; blast radius.
IMPACT_EDGE_RECORDED (optional), BLAST_RADIUS_COMPUTED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hg_core.ledger import emit
from hg_core.ledger.ledger_writer import iterate_events


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _node_id(typ: str, id_val: str) -> str:
    return f"{typ}:{id_val}"


def build_impact_graph(workspace_root: Path) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[str, str, str, List[str]]]]:
    """
    Build impact graph: nodes (artifacts, decisions, work_items, incidents, policies), edges with evidence_refs.
    Edges: PRODUCES, CONSUMES, DERIVES_FROM, VERIFIED_BY, GOVERNED_BY, DEPENDS_ON.
    Returns (nodes_by_id, edges) where edges are (from_id, to_id, edge_type, evidence_refs).
    """
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Tuple[str, str, str, List[str]]] = []

    def add_node(nid: str, typ: str, attrs: Dict[str, Any], ev_refs: Optional[List[str]] = None) -> None:
        nodes[nid] = {"type": typ, "id": nid.split(":", 1)[-1], **attrs}
        if ev_refs:
            nodes[nid]["evidence_refs"] = ev_refs

    def add_edge(fr: str, to: str, etyp: str, ev_refs: Optional[List[str]] = None) -> None:
        edges.append((fr, to, etyp, ev_refs or []))

    for ev in iterate_events(Path(workspace_root)):
        action = ev.get("action") or ""
        payload = ev.get("payload") or {}
        scope = ev.get("scope") or {}
        actor = ev.get("actor") or {}
        if action == "DECISION_COMMITTED":
            did = payload.get("decision_id") or (ev.get("object") or {}).get("id") or ev.get("event_id")
            if did:
                nid = _node_id("decision", did)
                add_node(nid, "decision", {"title": payload.get("title", ""), "scope_type": scope.get("type"), "scope_id": scope.get("id"), "agent_id": actor.get("agent_id", "")}, [ev.get("event_id")])
                for cid in payload.get("based_on_claim_ids") or []:
                    if isinstance(cid, str):
                        add_edge(nid, _node_id("claim", cid), "DERIVES_FROM", [ev.get("event_id")])
        elif action.startswith("WORK_ITEM_"):
            wid = payload.get("work_item_id") or payload.get("id") or (ev.get("object") or {}).get("id") or ev.get("event_id")
            if wid:
                nid = _node_id("work_item", str(wid))
                add_node(nid, "work_item", {"title": payload.get("title", ""), "status": payload.get("status", ""), "scope_type": scope.get("type"), "scope_id": scope.get("id"), "agent_id": actor.get("agent_id", "")}, [ev.get("event_id")])
                for linked in payload.get("linked_ids") or []:
                    lid = linked if isinstance(linked, str) else (linked.get("id") if isinstance(linked, dict) else None)
                    if lid and ":" not in str(lid):
                        add_edge(nid, str(lid), "DEPENDS_ON", [ev.get("event_id")])
        elif action.startswith("INCIDENT_"):
            iid = payload.get("incident_id") or payload.get("candidate_id") or (ev.get("object") or {}).get("id") or ev.get("event_id")
            if iid:
                nid = _node_id("incident", str(iid))
                add_node(nid, "incident", {"status": payload.get("status", ""), "severity": payload.get("severity", ""), "scope_type": scope.get("type"), "scope_id": scope.get("id"), "agent_id": actor.get("agent_id", "")}, [ev.get("event_id")])
        elif action in ("POLICY_PUBLISHED", "POLICY_APPLIED", "POLICY_OVERRIDE_APPLIED", "POLICY_CHANGE_LINKED", "APPROVAL_POLICY_APPLIED", "FEDERATION_POLICY_APPLIED", "POLICY_ROLLOUT_STARTED", "POLICY_ROLLOUT_COMPLETED", "POLICY_ROLLOUT_ROLLED_BACK", "POLICY_DIFF_RISK_REPORT"):
            pref = payload.get("policy_ref") or payload.get("artifact_path") or payload.get("policy_id") or (ev.get("object") or {}).get("id") or ev.get("event_id")
            if pref:
                nid = _node_id("policy", str(pref))
                add_node(nid, "policy", {"policy_type": payload.get("policy_type", ""), "action": action, "scope_type": scope.get("type"), "scope_id": scope.get("id"), "agent_id": actor.get("agent_id", "")}, [ev.get("event_id")])
        elif action == "TOOL_OUTCOME_RECORDED":
            tid = payload.get("tool_call_id") or payload.get("tool_name") or (ev.get("object") or {}).get("id") or ev.get("event_id")
            if tid:
                nid = _node_id("tool", str(tid))
                if nid not in nodes:
                    add_node(nid, "tool", {"tool_name": payload.get("tool_name", ""), "outcome": payload.get("outcome", ""), "scope_type": scope.get("type"), "scope_id": scope.get("id"), "agent_id": actor.get("agent_id", "")}, [ev.get("event_id")])

    # Verifiers (Differentiators Pack 1: from verification source artifacts or ledger)
    _add_verifier_nodes(workspace_root, add_node)

    return nodes, edges


def _add_verifier_nodes(workspace_root: Path, add_node) -> None:
    """Add verifier nodes from VERIFICATION_SOURCE_REGISTERED events."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    seen: Set[str] = set()
    for _st, _sid, ev in iter_events_by_scope(Path(workspace_root)):
        if ev.get("action") != "VERIFICATION_SOURCE_REGISTERED":
            continue
        p = ev.get("payload") or {}
        sid = p.get("source_id") or ""
        if not sid or sid in seen:
            continue
        seen.add(sid)
        nid = f"verifier:{sid}"
        add_node(nid, "verifier", {"name": p.get("name", "")}, [ev.get("event_id")])


def get_dependency_closure(
    workspace_root: Path,
    node_id: str,
    direction: str = "downstream",
    max_depth: int = 100,
) -> List[str]:
    """
    Return list of node ids reachable from node_id. direction: downstream (follow from->to) or upstream (to->from).
    """
    nodes, edges = build_impact_graph(Path(workspace_root))
    if node_id not in nodes:
        for nid in nodes:
            if nid.endswith(":" + node_id) or nid == node_id:
                node_id = nid
                break
        else:
            return []
    from_to: Dict[str, List[str]] = {}
    to_from: Dict[str, List[str]] = {}
    for fr, to, _et, _ in edges:
        from_to.setdefault(fr, []).append(to)
        to_from.setdefault(to, []).append(fr)
    follow = from_to if direction == "downstream" else to_from
    seen: Set[str] = {node_id}
    stack = [node_id]
    for _ in range(max_depth):
        if not stack:
            break
        next_stack = []
        for n in stack:
            for neighbor in follow.get(n, []):
                if neighbor not in seen:
                    seen.add(neighbor)
                    next_stack.append(neighbor)
        stack = next_stack
    return list(seen - {node_id})


def compute_blast_radius(
    *,
    incident_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> tuple[float, str]:
    """
    Compute blast radius for incident: dependency closure of incident node, score = len(affected). Write rationale, emit BLAST_RADIUS_COMPUTED. Returns (score, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    nodes, edges = build_impact_graph(workspace_root)
    inid = _node_id("incident", incident_id) if ":" not in incident_id else incident_id
    affected = get_dependency_closure(workspace_root, inid, direction="downstream")
    score = float(len(affected))
    ts = _iso_ts()
    blast_id = "blast_" + hashlib.sha256(f"{incident_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "impact"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{blast_id}.json"
    rationale_path.write_text(
        json.dumps({
            "blast_id": blast_id,
            "incident_id": incident_id,
            "score": score,
            "affected_refs": [{"node_id": a} for a in affected],
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    event_id = emit(
        "BLAST_RADIUS_COMPUTED",
        "impact",
        blast_id,
        {
            "blast_id": blast_id,
            "incident_id": incident_id,
            "score": score,
            "affected_refs": [{"node_id": a} for a in affected],
            "rationale_artifact_id": str(rationale_path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return score, event_id


def record_impact_edge(
    *,
    from_node_id: str,
    to_node_id: str,
    edge_type: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    evidence_refs: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit IMPACT_EDGE_RECORDED (optional explicit edge). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "IMPACT_EDGE_RECORDED",
        "impact_edge",
        f"{from_node_id}_{to_node_id}_{edge_type}",
        {
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "edge_type": edge_type,
            "evidence_refs": evidence_refs or [],
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
