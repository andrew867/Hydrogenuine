"""
Pack 15.5: Analytics API — GET /v1/analytics/signals, summary, rules/triggers. Tenant-scoped.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from hg_core.tenancy.context import TenantContext
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.signals_store import signal_events_list
from hg_gateway.analytics_store import analytics_summary, analytics_rules_triggers
from hg_gateway.events_ledger import list_events, list_evidence
from hg_gateway.replay_engine import verify_run_replay

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(verify_api_key)])


@router.get("/timeline")
def get_analytics_timeline(
    tenant_context: TenantContext = Depends(get_tenant_context),
    run_id: Optional[str] = Query(None),
    chat_id: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    to_ts: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    types: Optional[str] = Query(None, description="Comma-separated event types"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Pack 25: List event_stream events for tenant, filtered by run_id, chat_id, time, types."""
    tenant_id = tenant_context.tenant_id
    event_types = [t.strip() for t in (types or "").split(",") if t.strip()] or None
    events = list_events(
        tenant_id,
        run_id=run_id,
        chat_id=chat_id,
        from_ts=from_ts,
        to_ts=to_ts,
        event_types=event_types,
        limit=limit,
        offset=offset,
    )
    return {"tenant_id": tenant_id, "events": events, "limit": limit, "offset": offset}


@router.get("/evidence")
def get_analytics_evidence(
    tenant_context: TenantContext = Depends(get_tenant_context),
    run_id: Optional[str] = Query(None),
    chat_id: Optional[str] = Query(None),
    approval_id: Optional[str] = Query(None),
    evidence_types: Optional[str] = Query(None, description="Comma-separated evidence types"),
    from_ts: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    to_ts: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Pack 25: List evidence_ledger rows for tenant, filtered by run_id or chat_id."""
    tenant_id = tenant_context.tenant_id
    rows = list_evidence(
        tenant_id,
        run_id=run_id,
        chat_id=chat_id,
        approval_id=approval_id,
        evidence_types=[t.strip() for t in (evidence_types or "").split(",") if t.strip()] or None,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
        offset=offset,
    )
    return {"tenant_id": tenant_id, "evidence": rows, "limit": limit, "offset": offset}


@router.get("/replay")
def get_analytics_replay(
    tenant_context: TenantContext = Depends(get_tenant_context),
    run_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Pack 25: Replay verification report for run_id."""
    tenant_id = tenant_context.tenant_id
    if not run_id:
        return {"tenant_id": tenant_id, "run_id": None, "chain_ok": None, "errors": [], "report": {}}
    ok, errors, report = verify_run_replay(tenant_id, run_id)
    return {"tenant_id": tenant_id, "run_id": run_id, "chain_ok": ok, "errors": errors, "report": report}


@router.get("/signals")
def get_analytics_signals(
    tenant_context: TenantContext = Depends(get_tenant_context),
    chat_id: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    to_ts: Optional[str] = Query(None, description="ISO timestamp (inclusive)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """List signal events for tenant, optionally filtered by chat_id, entity_id, and time range."""
    tenant_id = tenant_context.tenant_id
    events = signal_events_list(
        tenant_id,
        chat_id=chat_id,
        entity_id=entity_id,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
        offset=offset,
    )
    return {"tenant_id": tenant_id, "events": events, "limit": limit, "offset": offset}


@router.get("/summary")
def get_analytics_summary(
    tenant_context: TenantContext = Depends(get_tenant_context),
    window: str = Query("7d", description="24h, 7d, or 30d"),
) -> Dict[str, Any]:
    """Summary for tenant: signal_events_count and rule_triggers counts in window."""
    tenant_id = tenant_context.tenant_id
    if window not in ("24h", "7d", "30d"):
        window = "7d"
    return analytics_summary(tenant_id, window=window)


@router.get("/rules/triggers")
def get_analytics_rules_triggers(
    tenant_context: TenantContext = Depends(get_tenant_context),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    """List rule trigger events (rule_id, chat_id, triggered_at) for tenant."""
    tenant_id = tenant_context.tenant_id
    triggers = analytics_rules_triggers(tenant_id, from_ts=from_ts, to_ts=to_ts, limit=limit)
    return {"tenant_id": tenant_id, "triggers": triggers}


@router.get("/utility/tag_means")
def get_analytics_utility_tag_means(
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Utility tag mean utilities for tenant (power, corrigibility, privacy, etc.)."""
    tenant_id = tenant_context.tenant_id
    return {"tenant_id": tenant_id, "tag_means": {}, "message": "Populated by utility proof run or elicitation."}


@router.get("/utility/trends")
def get_analytics_utility_trends(
    tenant_context: TenantContext = Depends(get_tenant_context),
    window: str = Query("7d"),
) -> Dict[str, Any]:
    """Utility trends over time."""
    tenant_id = tenant_context.tenant_id
    return {"tenant_id": tenant_id, "trends": [], "window": window}


@router.get("/utility/incidents")
def get_analytics_utility_incidents(
    tenant_context: TenantContext = Depends(get_tenant_context),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """Drift incidents (quarantine/pause/require_approval) for tenant."""
    tenant_id = tenant_context.tenant_id
    return {"tenant_id": tenant_id, "incidents": [], "limit": limit}


@router.get("/utility/governance-report")
def get_analytics_utility_governance_report(
    tenant_context: TenantContext = Depends(get_tenant_context),
    format: str = Query("docx", description="docx or json"),
    window: str = Query("7d"),
) -> Response:
    """Export Utility Governance Report: fit diagnostics, tag means, incidents, confidence. Returns DOCX or JSON."""
    tenant_id = tenant_context.tenant_id
    if format not in ("docx", "json"):
        format = "json"
    if window not in ("24h", "7d", "30d"):
        window = "7d"

    summary = analytics_summary(tenant_id, window=window)
    tag_means = {}
    incidents: List[Dict[str, Any]] = []
    fit_diagnostics = {"heldout_accuracy": None, "sample_size": 0, "convergence": False}

    if format == "json":
        body = json.dumps({
            "tenant_id": tenant_id,
            "window": window,
            "fit_diagnostics": fit_diagnostics,
            "tag_means": tag_means,
            "incidents": incidents,
            "summary": summary,
        }, indent=2)
        return Response(content=body, media_type="application/json")

    try:
        from hg_core.docs.office.docx_tool import docx_create, docx_add_heading, docx_add_paragraph, docx_add_table, docx_finalize
        title = f"Utility Governance Report — {tenant_id} ({window})"
        doc_id = docx_create(title, tenant_id)
        docx_add_heading(doc_id, "Fit diagnostics", level=1)
        docx_add_paragraph(doc_id, f"Heldout accuracy: {fit_diagnostics.get('heldout_accuracy', 'N/A')}")
        docx_add_paragraph(doc_id, f"Sample size: {fit_diagnostics.get('sample_size', 0)}")
        docx_add_paragraph(doc_id, f"Convergence: {fit_diagnostics.get('convergence', False)}")
        docx_add_heading(doc_id, "Tag means", level=1)
        docx_add_paragraph(doc_id, "Power, corrigibility, privacy, deception, shutdown_resistance (populated by proof run).")
        docx_add_table(doc_id, ["Tag", "Mean"], [["power", "—"], ["corrigibility", "—"], ["privacy", "—"], ["deception", "—"], ["shutdown_resistance", "—"]])
        docx_add_heading(doc_id, "Incidents", level=1)
        docx_add_paragraph(doc_id, "Drift incidents (quarantine/pause/require_approval) appear here when thresholds are exceeded.")
        docx_add_heading(doc_id, "Confidence", level=1)
        docx_add_paragraph(doc_id, "Sample size and heldout accuracy determine confidence. Minimum thresholds required for PASS.")
        file_id = docx_finalize(doc_id, "Utility_Governance_Report.docx")
        return Response(
            content=json.dumps({"file_id": file_id, "download": f"/v1/files/{file_id}/download"}),
            media_type="application/json",
        )
    except Exception as e:
        body = json.dumps({"error": str(e), "format": format}, indent=2)
        return Response(content=body, media_type="application/json")


@router.get("/governance-report")
def get_governance_report(
    tenant_context: TenantContext = Depends(get_tenant_context),
    window: str = Query("7d"),
    format: str = Query("docx", description="docx or json"),
) -> Response:
    """Export Governance Report: summary, notable events, evidence pointers. Returns DOCX or JSON."""
    tenant_id = tenant_context.tenant_id
    if format not in ("docx", "json"):
        format = "json"
    if window not in ("24h", "7d", "30d"):
        window = "7d"

    summary = analytics_summary(tenant_id, window=window)
    triggers_list = analytics_rules_triggers(tenant_id, limit=50)
    events = signal_events_list(tenant_id, limit=100, offset=0)

    if format == "json":
        import json
        body = json.dumps({
            "tenant_id": tenant_id,
            "window": window,
            "summary": summary,
            "triggers": triggers_list,
            "recent_events_count": len(events),
        }, indent=2)
        return Response(content=body, media_type="application/json")

    # DOCX export: build doc, finalize to tenant exports, return file_id for GET /v1/files/{file_id}/download
    try:
        from hg_core.docs.office.docx_tool import docx_create, docx_add_heading, docx_add_paragraph, docx_finalize
        title = f"Governance Report — {tenant_id} ({window})"
        doc_id = docx_create(title, tenant_id)
        docx_add_heading(doc_id, "Summary", level=1)
        docx_add_paragraph(doc_id, f"Signal events: {summary.get('signal_events_count', 0)}")
        docx_add_paragraph(doc_id, f"Rule triggers: {len(summary.get('rule_triggers', []))} rules triggered")
        docx_add_heading(doc_id, "Rule triggers", level=2)
        for t in summary.get("rule_triggers", []):
            docx_add_paragraph(doc_id, f"- {t.get('rule_id', '')}: {t.get('count', 0)}")
        docx_add_heading(doc_id, "Recent trigger events", level=2)
        for tr in triggers_list[:20]:
            docx_add_paragraph(doc_id, f"- {tr.get('rule_id')} @ {tr.get('chat_id', '')} at {tr.get('triggered_at', '')}")
        file_id = docx_finalize(doc_id, "governance_report.docx")
        import json
        return Response(
            content=json.dumps({"file_id": file_id, "download": f"/v1/files/{file_id}/download"}),
            media_type="application/json",
        )
    except Exception:
        pass
    import json
    body = json.dumps({"error": "DOCX export unavailable", "summary": summary}, indent=2)
    return Response(content=body, media_type="application/json")
