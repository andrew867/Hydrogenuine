"""
Viz Phase 2: Delegation graph view — handoffs and work_item links (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.viz.adapters.materializer_adapter import adapt_materializer_graph

DELEGATION_NODE_TYPES = ("handoff", "work_item")


def adapt_delegation_graph(
    workspace_root: Path,
    limit: int = 200,
) -> Dict[str, Any]:
    """
    Return graph view for delegation: handoff and work_item nodes, edges handoff->work_item and links_to.
    Uses materializer graph filtered to handoff/work_item types.
    """
    out = adapt_materializer_graph(
        Path(workspace_root),
        types=list(DELEGATION_NODE_TYPES),
        limit=limit,
    )
    # Keep only edges that involve handoff or work_item (materializer already filtered nodes)
    node_ids = {n["id"] for n in out["nodes"]}
    out["edges"] = [
        e for e in out["edges"]
        if e["from"] in node_ids and e["to"] in node_ids
        and e.get("type") in ("work_item", "links_to")
    ]
    return out
