"""Build organ causal trace from watchtower events."""

from __future__ import annotations

from typing import Any

from hg_runtime.openvino_watchtower.causal_graph import CausalEdge, CausalGraph, OrganTraceSpan

_EVENT_TO_EDGE: dict[str, str] = {
    "INFERENCE_REQUEST_RECEIVED": "organ_requested_inference",
    "INFERENCE_STARTED": "inference_started",
    "INFERENCE_COMPLETED": "inference_completed",
    "INFERENCE_FAILED": "inference_failed",
    "QUEUE_DEPTH_CHANGED": "queue_item_created",
    "TELEMETRY_STALE": "stale_detected",
    "TELEMETRY_CONTACT_LOST": "stale_detected",
}


def build_organ_trace(events: list[dict[str, Any]], *, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    graph = CausalGraph()
    for ev in events:
        et = str(ev.get("event_type", ""))
        organ = ev.get("organ_id") or "model_provider"
        span_id = ev.get("span_id")
        request_id = ev.get("request_id")
        payload = ev.get("payload") or {}
        kind = _EVENT_TO_EDGE.get(et)
        if kind:
            graph.add_edge(
                CausalEdge(
                    kind=kind,  # type: ignore[arg-type]
                    source=organ,
                    target="inference" if "INFERENCE" in et else organ,
                    request_id=request_id,
                    span_id=span_id,
                    queue_item_id=payload.get("queue_item_id"),
                    receipt_ref=payload.get("receipt_ref"),
                    proof_ref=payload.get("proof_ref"),
                    ts=ev.get("ts"),
                    blocked_reason=payload.get("blocked_reason"),
                )
            )
        if organ in graph.nodes:
            node = graph.nodes[organ]
            if "FAILED" in et:
                node.state = "error"
            elif "STARTED" in et:
                node.state = "active"
            elif "COMPLETED" in et:
                node.state = "complete"
            node.span_id = span_id or node.span_id
            node.request_id = request_id or node.request_id

    if snapshot:
        for span in snapshot.get("active_inference_spans") or []:
            oid = span.get("organ_id") or "model_provider"
            if oid not in graph.nodes:
                graph.nodes[oid] = OrganTraceSpan(organ_id=oid, state="active", span_id=span.get("span_id"))
            elif not graph.nodes[oid].span_id and span.get("span_id"):
                graph.missing_refs.append(f"span_link:{oid}")

    if not graph.edges and not graph.nodes:
        graph.missing_refs.append("no_trace_events")
    data = graph.to_dict()
    data["verdict"] = "YELLOW_TRACE_INCOMPLETE" if graph.missing_refs else "GREEN_TRACE_OK"
    return data


def current_blocker(trace: dict[str, Any]) -> str | None:
    for node in (trace.get("nodes") or {}).values():
        if node.get("state") in {"blocked", "error", "stale"}:
            return node.get("blocked_reason") or node.get("state")
    if trace.get("missing_refs"):
        return "missing_trace_refs"
    return None


__all__ = ["build_organ_trace", "current_blocker"]
