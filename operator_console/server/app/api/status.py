"""Status: dashboard (timeseries/summary) and autonomy (GET/PATCH). Plan: console-dashboard-api, status-autonomy-api."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.activity_service import get_dashboard_data, get_dashboard_reports, resolve_dashboard_report_path
from ..services.monitoring_service import get_monitoring_insight


router = APIRouter()


@router.get("/dashboard")
def status_dashboard(hours: int = 24, _=Depends(require_api_key)):
    """Dashboard data: latest_state + timeseries from memory/overseer (same info as PDF/PNG)."""
    data = get_dashboard_data(hours=min(168, max(1, hours)))
    return {"ok": True, **data}


@router.get("/reports")
def status_reports(limit: int = 20, _=Depends(require_api_key)):
    return {"ok": True, **get_dashboard_reports(limit=max(1, min(limit, 100)))}


@router.get("/reports/file/{report_ref:path}")
def status_report_file(report_ref: str, _=Depends(require_api_key)):
    path = resolve_dashboard_report_path(report_ref)
    if not path:
        raise HTTPException(status_code=404, detail="report not found")
    suffix = Path(path).suffix.lower()
    media_type = "application/pdf" if suffix == ".pdf" else "image/png" if suffix == ".png" else "application/octet-stream"
    return FileResponse(path=str(path), filename=path.name, media_type=media_type, content_disposition_type="inline")


@router.get("/insight")
def status_insight(
    hours: int = 24,
    limit_runs: int = 200,
    dag_only: bool = False,
    _=Depends(require_api_key),
):
    """Aggregated monitoring insight: workflow health, anomalies, and policy/steering violations."""
    return get_monitoring_insight(
        hours=hours,
        limit_runs=limit_runs,
        dag_only=dag_only,
    )


class AutonomyPatch(BaseModel):
    outbound_safety_gate_enabled: bool | None = None
    entity_dag_change_control: str | None = None


@router.get("/autonomy")
def get_autonomy(_=Depends(require_api_key)):
    """Autonomy config: outbound_safety_gate_enabled, entity_dag_change_control (off|on|pass-through)."""
    try:
        from hg_core.autonomy_config import get_autonomy_config
        config = get_autonomy_config()
        return {"ok": True, **config}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.patch("/autonomy")
def patch_autonomy(payload: AutonomyPatch, _=Depends(require_api_key)):
    """Update autonomy config; persist to memory/overseer/autonomy_config.json."""
    try:
        from hg_core.autonomy_config import save_autonomy_config, ENTITY_DAG_CHANGE_CONTROL_VALUES
        entity_dag = payload.entity_dag_change_control
        if entity_dag is not None and entity_dag.lower() not in ENTITY_DAG_CHANGE_CONTROL_VALUES:
            return {"ok": False, "error": f"entity_dag_change_control must be one of {ENTITY_DAG_CHANGE_CONTROL_VALUES}"}
        config = save_autonomy_config(
            entity_dag_change_control=entity_dag,
            outbound_safety_gate_enabled=payload.outbound_safety_gate_enabled,
        )
        return {"ok": True, **config}
    except Exception as e:
        return {"ok": False, "error": str(e)}
