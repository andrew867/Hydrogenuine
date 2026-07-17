from __future__ import annotations

from typing import Any, Dict


_STATUS_ALIASES = {
    "approve": "approved",
    "approved": "approved",
    "allow": "approved",
    "deny": "denied",
    "denied": "denied",
    "reject": "denied",
    "pending": "pending",
}


def normalize_approval_status(value: Any) -> str:
    raw = str(value or "pending").strip().lower()
    return _STATUS_ALIASES.get(raw, raw or "pending")


def normalize_approval_kind(value: Any) -> str:
    raw = str(value or "other").strip().lower()
    aliases = {
        "tool_invoke": "tool_use",
        "tool": "tool_use",
        "chat_turn": "external_request",
        "injection_review": "external_request",
    }
    return aliases.get(raw, raw or "other")


def build_approval_origin(entry: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    chat_id = entry.get("chat_id") or payload.get("chat_id")
    run_id = payload.get("run_id") or payload.get("swarm_run_id") or payload.get("dag_run_id")
    workflow_id = payload.get("workflow_id") or payload.get("graph_id") or payload.get("task_name")
    origin_type = "chat" if chat_id else "run" if run_id else "workflow" if workflow_id else "unknown"
    route = None
    if chat_id:
        route = f"/chat/{chat_id}"
    elif run_id:
        route = f"/runs/{run_id}"
    elif workflow_id:
        route = f"/workflows/{workflow_id}"
    return {
        "type": origin_type,
        "chat_id": chat_id,
        "run_id": run_id,
        "workflow_id": workflow_id,
        "route": route,
        "label": workflow_id or run_id or chat_id or "unknown",
    }


def normalize_runtime_approval(entry: Dict[str, Any]) -> Dict[str, Any]:
    payload = entry.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    created_at = entry.get("createdAt") or entry.get("created_at") or entry.get("timestamp")
    resolved_at = entry.get("resolvedAt") or entry.get("resolved_at")
    requested_by = entry.get("requestedBy") or entry.get("requested_by") or "unknown"
    assigned_principal = entry.get("assignedPrincipalId") or entry.get("assigned_principal_id")
    status = normalize_approval_status(entry.get("status") or entry.get("decision"))
    kind = normalize_approval_kind(entry.get("kind"))
    origin = build_approval_origin(entry, payload)
    return {
        "id": entry.get("id") or "",
        "createdAt": created_at,
        "timestamp": created_at,
        "resolvedAt": resolved_at,
        "status": status,
        "decision": status,
        "kind": kind,
        "title": entry.get("title") or "",
        "summary": entry.get("summary") or "",
        "risk": entry.get("risk") or "",
        "requestedBy": requested_by,
        "requested_by": requested_by,
        "payload": payload,
        "resolutionNote": entry.get("resolutionNote") or entry.get("resolution_note"),
        "assignedPrincipalId": assigned_principal,
        "assigned_principal_id": assigned_principal,
        "chat_id": origin.get("chat_id"),
        "origin": origin,
        "workflow": origin.get("workflow_id"),
        "workflow_id": origin.get("workflow_id"),
        "run_id": origin.get("run_id"),
        "origin_route": origin.get("route"),
    }
