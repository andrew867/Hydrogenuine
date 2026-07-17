"""
Graph mirror: build an in-memory graph from the DB-backed ledger stream.

Materialized JSONL artifacts may still be exported elsewhere, but this live
projection no longer reads them as its source of truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hg_core.ledger.ledger_writer import iterate_events


def build_graph(workspace_root: Path) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[str, str, str, List[str]]]]:
    """
    Ingest materialized tables into nodes and edges. Each edge has evidence_refs (event_ids).
    Returns (nodes_by_id, edges) where edges are (from_id, to_id, edge_type, evidence_refs).
    Idempotent: same id overwrites.
    """
    workspace_root = Path(workspace_root)
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Tuple[str, str, str, List[str]]] = []

    def node_id(typ: str, id_val: str) -> str:
        return f"{typ}:{id_val}"

    def add_node(nid: str, typ: str, attrs: Dict[str, Any], ev_refs: Optional[List[str]] = None) -> None:
        nodes[nid] = {"type": typ, "id": nid.split(":", 1)[-1], **attrs}
        if ev_refs:
            nodes[nid]["evidence_refs"] = ev_refs

    def add_edge(fr: str, to: str, etyp: str, ev_refs: Optional[List[str]] = None) -> None:
        edges.append((fr, to, etyp, ev_refs or []))

    for ev in iterate_events(workspace_root):
        action = ev.get("action")
        payload = ev.get("payload") or {}
        event_id = ev.get("event_id")
        scope = ev.get("scope") or {}
        actor = ev.get("actor") or {}
        if action not in {
            "DECISION_COMMITTED",
            "WORK_ITEM_CREATED",
            "WORK_ITEM_UPDATED",
            "WORK_ITEM_ASSIGNED",
            "WORK_ITEM_BLOCKED",
            "WORK_ITEM_UNBLOCKED",
            "WORK_ITEM_CLOSED",
            "WORK_ITEM_LINKED",
            "INCIDENT_CANDIDATE_CREATED",
            "INCIDENT_CONFIRMED",
            "INCIDENT_RESOLVED",
            "INCIDENT_MITIGATED",
            "INCIDENT_CLOSED",
            "HANDOFF_CREATED",
            "HANDOFF_ACCEPTED",
            "HANDOFF_REJECTED",
            "HANDOFF_COMPLETED",
        }:
            continue
        did = payload.get("decision_id") or (ev.get("object") or {}).get("id") or event_id
        if not did:
            continue
        nid = node_id("decision", did)
        if action == "DECISION_COMMITTED":
            add_node(
                nid,
                "decision",
                {
                    "title": payload.get("title", ""),
                    "scope_type": scope.get("type"),
                    "scope_id": scope.get("id"),
                    "agent_id": actor.get("agent_id", ""),
                },
                [event_id],
            )
            for cid in payload.get("based_on_claim_ids") or []:
                if isinstance(cid, str):
                    add_edge(nid, node_id("claim", cid), "based_on", [event_id])
        elif action.startswith("WORK_ITEM_"):
            wid = payload.get("work_item_id") or payload.get("id") or (ev.get("object") or {}).get("id") or event_id
            if not wid:
                continue
            nid = node_id("work_item", str(wid))
            current = nodes.get(nid, {"type": "work_item", "id": str(wid)})
            title = payload.get("title") or current.get("title", "")
            status = payload.get("status") or current.get("status", "")
            attrs = {**current, "title": title, "status": status, "scope_type": scope.get("type"), "scope_id": scope.get("id"), "agent_id": actor.get("agent_id", "")}
            add_node(nid, "work_item", attrs, [event_id])
            linked = payload.get("linked_ids") or []
            for ref in linked:
                lid = ref if isinstance(ref, str) else (ref.get("id") if isinstance(ref, dict) else None)
                if lid:
                    add_edge(nid, str(lid), "links_to", [event_id])
        elif action.startswith("INCIDENT_"):
            iid = payload.get("incident_id") or payload.get("candidate_id") or (ev.get("object") or {}).get("id") or event_id
            if not iid:
                continue
            nid = node_id("incident", str(iid))
            current = nodes.get(nid, {"type": "incident", "id": str(iid)})
            attrs = {
                **current,
                "status": payload.get("status") or current.get("status", ""),
                "severity": payload.get("severity") or current.get("severity", ""),
                "scope_type": scope.get("type"),
                "scope_id": scope.get("id"),
                "agent_id": actor.get("agent_id", ""),
            }
            add_node(nid, "incident", attrs, [event_id])
            for ref in payload.get("evidence_refs") or []:
                rid = ref.get("id") if isinstance(ref, dict) else (ref if isinstance(ref, str) else None)
                if rid:
                    add_edge(nid, str(rid), "evidence", [event_id])
        elif action.startswith("HANDOFF_"):
            hid = payload.get("handoff_id") or (ev.get("object") or {}).get("id") or event_id
            if not hid:
                continue
            nid = node_id("handoff", str(hid))
            current = nodes.get(nid, {"type": "handoff", "id": str(hid)})
            attrs = {
                **current,
                "from_agent": payload.get("from_agent_id") or current.get("from_agent"),
                "to_agent": payload.get("to_agent_id") or current.get("to_agent"),
                "status": payload.get("status") or current.get("status", ""),
                "scope_type": scope.get("type"),
                "scope_id": scope.get("id"),
                "agent_id": actor.get("agent_id", ""),
            }
            add_node(nid, "handoff", attrs, [event_id])
            wi = payload.get("work_item_id") or payload.get("work_item_ref")
            if wi:
                add_edge(nid, node_id("work_item", str(wi)) if ":" not in str(wi) else str(wi), "work_item", [event_id])

    return nodes, edges


def get_neighbors(
    workspace_root: Path,
    node_id: str,
    *,
    direction: str = "out",
    edge_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return neighbor nodes. node_id can be "type:id" or just id (then search nodes by id suffix).
    direction: "out" (from this node) or "in". edge_type: optional filter.
    """
    nodes, edges = build_graph(Path(workspace_root))
    nid = node_id if ":" in node_id else next((n for n in nodes if n.endswith(":" + node_id)), node_id)
    if nid not in nodes:
        return []
    neighbor_ids: Set[str] = set()
    for fr, to, etyp, _ in edges:
        if edge_type and etyp != edge_type:
            continue
        if direction == "out" and fr == nid:
            neighbor_ids.add(to)
        elif direction == "in" and to == nid:
            neighbor_ids.add(fr)
    return [nodes[n] for n in neighbor_ids if n in nodes]


def get_subgraph(
    workspace_root: Path,
    seed_ids: List[str],
    *,
    depth: int = 2,
) -> Dict[str, Any]:
    """
    Return subgraph (nodes + edges) reachable from seed_ids within depth hops.
    Each node/edge includes evidence_refs where available.
    """
    nodes, edges = build_graph(Path(workspace_root))
    normalized = []
    for sid in seed_ids:
        nid = sid if ":" in sid else next((n for n in nodes if n.endswith(":" + sid)), sid)
        if nid in nodes:
            normalized.append(nid)
    frontier: Set[str] = set(normalized)
    visited: Set[str] = set(frontier)
    for _ in range(depth):
        next_frontier: Set[str] = set()
        for fr, to, etyp, ev_refs in edges:
            if fr in frontier and to in nodes:
                next_frontier.add(to)
                visited.add(to)
            if to in frontier and fr in nodes:
                next_frontier.add(fr)
                visited.add(fr)
        frontier = next_frontier
    sub_edges = [(fr, to, etyp, ev_refs) for fr, to, etyp, ev_refs in edges if fr in visited and to in visited]
    return {"nodes": {n: nodes[n] for n in visited}, "edges": [{"from": fr, "to": to, "type": t, "evidence_refs": er} for fr, to, t, er in sub_edges]}
