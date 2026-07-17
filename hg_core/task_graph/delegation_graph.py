"""
Delegation graph capture and summary (Autonomy Ch5).

Build graph incrementally from behavior events; persist graph and delegation summary per run.
Per docs/specs/delegation_graph_schema.md and docs/specs/behavior_telemetry_schema.md.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DELEGATION_EVENT_TYPES = frozenset({
    "delegation.assign", "delegation.handoff", "delegation.split", "delegation.merge",
})


class DelegationGraphBuilder:
    """Incremental delegation graph from behavior events."""

    def __init__(self, run_id: str, workflow_id: str, root_objective_summary: str = ""):
        self.run_id = run_id
        self.workflow_id = workflow_id
        self.root_objective_summary = root_objective_summary
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._handoff_count = 0
        self._split_count = 0
        self._merge_count = 0
        self._depth_by_node: Dict[str, int] = {}
        self._children: Dict[str, List[str]] = defaultdict(list)

    def ingest_event(self, event: Dict[str, Any]) -> None:
        """Process one behavior event; update nodes/edges and counts."""
        event_type = event.get("event_type", "")
        work_item_id = event.get("work_item_id", "")
        parent_id = event.get("parent_work_item_id")
        if not work_item_id:
            return
        if work_item_id not in self.nodes:
            self.nodes[work_item_id] = {
                "id": work_item_id,
                "owner": event.get("agent_id", ""),
                "scope": "",
                "status": "in_progress",
                "acceptance_checks": [],
                "budgets_used": {},
            }
        if event_type == "delegation.handoff":
            self._handoff_count += 1
        elif event_type == "delegation.split":
            self._split_count += 1
        elif event_type == "delegation.merge":
            self._merge_count += 1
        if event_type in DELEGATION_EVENT_TYPES and parent_id:
            self.edges.append({
                "from": parent_id,
                "to": work_item_id,
                "reason": event.get("payload_summary", {}).get("reason", ""),
                "receipt_aligned": event.get("payload_summary", {}).get("receipt_aligned", True),
                "event_type": event_type,
            })
            self._children[parent_id].append(work_item_id)
            depth = self._depth_by_node.get(parent_id, 0) + 1
            self._depth_by_node[work_item_id] = max(
                self._depth_by_node.get(work_item_id, 0), depth
            )

    def _max_depth(self) -> int:
        if not self._depth_by_node:
            return 0
        return max(self._depth_by_node.values()) if self.nodes else 0

    def _max_width(self) -> int:
        if not self._children:
            return len(self.nodes) if self.nodes else 0
        return max(len(children) for children in self._children.values()) if self._children else 0

    def to_graph_dict(self) -> Dict[str, Any]:
        """Full graph for persistence (nodes, edges)."""
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }

    def to_summary_dict(
        self,
        status: str = "success",
        external_writes_attempted: bool = False,
        external_writes_blocked: bool = False,
        anomalies: Optional[List[Dict[str, Any]]] = None,
        top_bottlenecks: Optional[List[Dict[str, Any]]] = None,
        rework_rate: float = 0.0,
        policy_block_rate: float = 0.0,
        retry_count: int = 0,
        token_spend_rate: float = 0.0,
    ) -> Dict[str, Any]:
        """Compact delegation summary per template."""
        anomalies = anomalies or []
        top_bottlenecks = top_bottlenecks or []
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "root_objective_summary": self.root_objective_summary,
            "metrics": {
                "delegation_depth_max": self._max_depth(),
                "delegation_width_max": self._max_width(),
                "total_work_items": len(self.nodes),
                "handoff_count": self._handoff_count,
                "split_count": self._split_count,
                "merge_count": self._merge_count,
                "rework_rate": rework_rate,
                "policy_block_rate": policy_block_rate,
                "retry_count": retry_count,
                "token_spend_rate": token_spend_rate,
            },
            "anomalies": anomalies,
            "top_bottlenecks": top_bottlenecks,
            "final_state": {
                "status": status,
                "external_writes_attempted": "yes" if external_writes_attempted else "no",
                "external_writes_blocked": "yes" if external_writes_blocked else "no",
            },
        }


def build_graph_from_events(
    run_id: str,
    workflow_id: str,
    events: List[Dict[str, Any]],
    root_objective_summary: str = "",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build graph and summary from a list of behavior events. Returns (graph_dict, summary_dict)."""
    builder = DelegationGraphBuilder(run_id, workflow_id, root_objective_summary)
    for ev in events:
        builder.ingest_event(ev)
    return builder.to_graph_dict(), builder.to_summary_dict()


def persist_delegation_artifacts(
    run_dir: Path,
    graph_dict: Dict[str, Any],
    summary_dict: Dict[str, Any],
) -> None:
    """Write delegation_graph.json and delegation_summary.json to run_dir."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "delegation_graph.json").write_text(
        json.dumps(graph_dict, indent=2), encoding="utf-8"
    )
    (run_dir / "delegation_summary.json").write_text(
        json.dumps(summary_dict, indent=2), encoding="utf-8"
    )
