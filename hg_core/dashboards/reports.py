"""
Role-based dashboards and narrative reports: evidence-backed, with optional investor_mode (safe demo, redact sensitive).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger.ledger_writer import iterate_events

ROLES = ("operator", "reviewer", "admin", "viewer", "investor")


def _decision_rows_from_ledger(workspace_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in iterate_events(workspace_root, action="DECISION_COMMITTED"):
        payload = ev.get("payload") or {}
        decision_id = payload.get("decision_id") or (ev.get("object") or {}).get("id")
        if not decision_id:
            continue
        rows.append(
            {
                "decision_id": decision_id,
                "title": payload.get("title", ""),
                "event_id": ev.get("event_id"),
                "scope_type": ev.get("scope", {}).get("type"),
                "scope_id": ev.get("scope", {}).get("id"),
                "agent_id": (ev.get("actor") or {}).get("agent_id", ""),
                "based_on_claim_ids": payload.get("based_on_claim_ids", []),
                "value_weights": payload.get("value_weights", []),
                "context_ref": payload.get("context_ref", {}),
                "produced_artifact_ids": payload.get("produced_artifact_ids", []),
            }
        )
    return rows


def _incident_rows_from_ledger(workspace_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in iterate_events(workspace_root):
        action = ev.get("action") or ""
        if not action.startswith("INCIDENT_"):
            continue
        payload = ev.get("payload") or {}
        incident_id = payload.get("incident_id") or payload.get("candidate_id") or (ev.get("object") or {}).get("id") or ev.get("event_id")
        if not incident_id:
            continue
        rows.append(
            {
                "incident_id": incident_id,
                "status": payload.get("status", ""),
                "severity": payload.get("severity", ""),
                "event_id": ev.get("event_id"),
                "scope_type": ev.get("scope", {}).get("type"),
                "scope_id": ev.get("scope", {}).get("id"),
                "agent_id": (ev.get("actor") or {}).get("agent_id", ""),
            }
        )
    return rows


def _work_item_rows_from_ledger(workspace_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in iterate_events(workspace_root):
        action = ev.get("action") or ""
        if not action.startswith("WORK_ITEM_"):
            continue
        payload = ev.get("payload") or {}
        work_item_id = payload.get("work_item_id") or payload.get("id") or (ev.get("object") or {}).get("id") or ev.get("event_id")
        if not work_item_id:
            continue
        rows.append(
            {
                "work_item_id": work_item_id,
                "title": payload.get("title", ""),
                "status": payload.get("status", ""),
                "event_id": ev.get("event_id"),
                "scope_type": ev.get("scope", {}).get("type"),
                "scope_id": ev.get("scope", {}).get("id"),
                "agent_id": (ev.get("actor") or {}).get("agent_id", ""),
            }
        )
    return rows


def _audit_rows_from_ledger(workspace_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in iterate_events(workspace_root):
        action = ev.get("action") or ""
        if not (action.endswith("_EXPORTED") or action.startswith("AUDIT_")):
            continue
        rows.append(
            {
                "action": action,
                "resource": (ev.get("object") or {}).get("type") or ev.get("object_type") or "",
                "event_id": ev.get("event_id"),
            }
        )
    return rows


def get_dashboard_for_role(
    workspace_root: Path,
    role: str,
    *,
    investor_mode: bool = False,
) -> Dict[str, Any]:
    """
    Return dashboard payload for role: operator (full), reviewer (decisions + incidents), admin (all + governance), viewer (read-only summary), investor (narrative + evidence links, redacted).
    """
    workspace_root = Path(workspace_root)
    dashboard: Dict[str, Any] = {"role": role, "investor_mode": investor_mode, "widgets": []}
    if role not in ROLES:
        role = "viewer"
    decisions = _decision_rows_from_ledger(workspace_root)[-20:]
    incidents = _incident_rows_from_ledger(workspace_root)[-10:]
    work_items = _work_item_rows_from_ledger(workspace_root)[-15:]
    if role in ("operator", "admin", "reviewer") and not investor_mode:
        dashboard["widgets"].append({"id": "recent_decisions", "type": "list", "count": len(decisions), "evidence_refs": [d.get("event_id") for d in decisions if d.get("event_id")]})
        dashboard["widgets"].append({"id": "recent_incidents", "type": "list", "count": len(incidents), "evidence_refs": [i.get("event_id") for i in incidents if i.get("event_id")]})
    if role in ("operator", "admin"):
        dashboard["widgets"].append({"id": "work_queue", "type": "list", "count": len(work_items)})
    if role == "viewer" or investor_mode:
        dashboard["widgets"] = [
            {"id": "summary", "type": "summary", "decisions_count": len(decisions), "incidents_count": len(incidents), "work_items_count": len(work_items)},
        ]
    if investor_mode:
        dashboard["evidence_links"] = True
        dashboard["redact_sensitive"] = True
    return dashboard


def get_narrative_report(
    workspace_root: Path,
    report_type: str,
    *,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    investor_mode: bool = False,
) -> Dict[str, Any]:
    """
    report_type: decision_report | incident_report | governance_report.
    Returns narrative structure with evidence_refs; investor_mode redacts sensitive fields.
    """
    workspace_root = Path(workspace_root)
    report: Dict[str, Any] = {"report_type": report_type, "evidence_refs": [], "sections": []}
    if report_type == "decision_report":
        rows = _decision_rows_from_ledger(workspace_root)
        if scope_type:
            rows = [r for r in rows if r.get("scope_type") == scope_type]
        if scope_id:
            rows = [r for r in rows if r.get("scope_id") == scope_id]
        report["sections"].append({"title": "Decisions", "count": len(rows), "items": [{"decision_id": r.get("decision_id"), "title": r.get("title"), "event_id": r.get("event_id")} for r in rows[-20:]]})
        report["evidence_refs"] = [r.get("event_id") for r in rows if r.get("event_id")][-20:]
    elif report_type == "incident_report":
        rows = _incident_rows_from_ledger(workspace_root)
        report["sections"].append({"title": "Incidents", "count": len(rows), "items": [{"incident_id": r.get("incident_id"), "status": r.get("status"), "severity": r.get("severity"), "event_id": r.get("event_id")} for r in rows[-10:]]})
        report["evidence_refs"] = [r.get("event_id") for r in rows if r.get("event_id")][-10:]
    elif report_type == "governance_report":
        audit = _audit_rows_from_ledger(workspace_root)
        report["sections"].append({"title": "Audit trail", "count": len(audit), "items": [{"action": r.get("action"), "resource": r.get("resource"), "event_id": r.get("event_id")} for r in audit[-15:]]})
        report["evidence_refs"] = [r.get("event_id") for r in audit if r.get("event_id")][-15:]
    else:
        report["sections"].append({"title": "Unknown report type", "count": 0})
    if investor_mode:
        report["redact_sensitive"] = True
    return report
