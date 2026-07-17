"""Delegation API: summary, anomaly, graph, and incident report endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from ..core.auth import require_api_key
from ..services.json_artifact import read_json_artifact
from ..services.incident_report import generate_incident_report, incident_report_md

router = APIRouter()


@router.get("/{run_id}/delegation/summary")
def delegation_summary(run_id: str, _=Depends(require_api_key)):
    """GET delegation summary for run (delegation_summary.json)."""
    res = read_json_artifact(run_id, "delegation_summary")
    if not res.get("ok"):
        code = res.get("error", {}).get("code", "NOT_FOUND")
        if code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=res["error"])
        if code == "MISSING":
            raise HTTPException(status_code=404, detail=res["error"])
        raise HTTPException(status_code=400, detail=res["error"])
    return {"ok": True, "run_id": run_id, "summary": res["data"]}


@router.get("/{run_id}/delegation/graph")
def delegation_graph(run_id: str, _=Depends(require_api_key)):
    """GET delegation graph for run (delegation_graph.json)."""
    res = read_json_artifact(run_id, "delegation_graph")
    if not res.get("ok"):
        code = res.get("error", {}).get("code", "NOT_FOUND")
        if code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=res["error"])
        if code == "MISSING":
            raise HTTPException(status_code=404, detail=res["error"])
        raise HTTPException(status_code=400, detail=res["error"])
    return {"ok": True, "run_id": run_id, "graph": res["data"]}


@router.get("/{run_id}/delegation/anomalies")
def delegation_anomalies(run_id: str, _=Depends(require_api_key)):
    """GET anomalies for run (from delegation_summary.anomalies)."""
    res = read_json_artifact(run_id, "delegation_summary")
    if not res.get("ok"):
        if res.get("error", {}).get("code") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=res["error"])
        if res.get("error", {}).get("code") == "MISSING":
            return {"ok": True, "run_id": run_id, "anomalies": []}
        raise HTTPException(status_code=400, detail=res["error"])
    anomalies = res.get("data", {}).get("anomalies", [])
    return {"ok": True, "run_id": run_id, "anomalies": anomalies}


@router.get("/{run_id}/incident-report")
def incident_report_json(run_id: str, _=Depends(require_api_key)):
    """GET incident report (anomalies + interventions) as JSON."""
    res = generate_incident_report(run_id)
    if not res.get("ok"):
        if res.get("error", {}).get("code") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=res["error"])
        raise HTTPException(status_code=404, detail=res.get("error", {}))
    return res


@router.get("/{run_id}/incident-report.md", response_class=PlainTextResponse)
def incident_report_markdown(run_id: str, _=Depends(require_api_key)):
    """GET incident report as Markdown."""
    return incident_report_md(run_id)
