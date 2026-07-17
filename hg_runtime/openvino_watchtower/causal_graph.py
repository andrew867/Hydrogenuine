"""Causal graph model for organ trace — explanatory only."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

OrganTraceState = Literal[
    "idle", "active", "waiting", "blocked", "degraded", "stale", "error", "complete"
]

CausalEdgeKind = Literal[
    "organ_requested_inference",
    "inference_started",
    "inference_completed",
    "inference_failed",
    "queue_item_created",
    "queue_item_approved",
    "queue_item_denied",
    "receipt_written",
    "proof_written",
    "stop_triggered",
    "panic_triggered",
    "stale_detected",
]


@dataclass
class CausalEdge:
    kind: CausalEdgeKind
    source: str
    target: str
    request_id: str | None = None
    span_id: str | None = None
    queue_item_id: str | None = None
    receipt_ref: str | None = None
    proof_ref: str | None = None
    verdict: str | None = None
    blocked_reason: str | None = None
    ts: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganTraceSpan:
    organ_id: str
    state: OrganTraceState = "idle"
    request_id: str | None = None
    span_id: str | None = None
    action_id: str | None = None
    queue_item_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    verdict: str | None = None
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganTraceEvent:
    organ_id: str
    event_type: str
    ts: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CausalGraph:
    nodes: dict[str, OrganTraceSpan] = field(default_factory=dict)
    edges: list[CausalEdge] = field(default_factory=list)
    missing_refs: list[str] = field(default_factory=list)

    def add_edge(self, edge: CausalEdge) -> None:
        self.edges.append(edge)
        if edge.source not in self.nodes:
            self.nodes[edge.source] = OrganTraceSpan(organ_id=edge.source, state="active")
        if edge.target not in self.nodes:
            self.nodes[edge.target] = OrganTraceSpan(organ_id=edge.target)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "missing_refs": list(self.missing_refs),
            "authority_created": False,
            "permission_granted": False,
            "advisory_only": True,
        }


__all__ = [
    "CausalEdge",
    "CausalEdgeKind",
    "CausalGraph",
    "OrganTraceEvent",
    "OrganTraceSpan",
    "OrganTraceState",
]
