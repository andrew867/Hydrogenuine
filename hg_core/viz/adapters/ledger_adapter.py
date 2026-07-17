"""
Viz Phase 1: Adapter from ledger events to unified viz nodes (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import iterate_events
from hg_core.viz.schema import viz_node, evidence_ref


def adapt_ledger_events_to_nodes(workspace_root: Path, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Map ledger events to viz nodes (one node per event). Read-only.
    Returns list of unified viz nodes with evidence_refs (event_id).
    """
    root = Path(workspace_root)
    nodes: List[Dict[str, Any]] = []
    for ev in iterate_events(root):
        if len(nodes) >= limit:
            break
        eid = ev.get("event_id")
        action = ev.get("action", "")
        if not eid:
            continue
        node_id = f"event:{eid}"
        nodes.append(viz_node(
            node_id,
            "event",
            {"action": action, "ts": ev.get("ts", "")},
            [evidence_ref(eid, "event_id")],
        ))
    return nodes
