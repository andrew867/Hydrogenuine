"""Product API v1: read-only resources + RBAC with wired operator actions."""

import os
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse

from ..core.product_auth import require_product_auth, require_product_role
from ..services import product_service as svc
from ..services.activity_service import resolve_dashboard_report_path
from ..services.demo_config import get_demo_config
from ..services.audit_log import append_audit
from hg_gateway.shared_storage import append_approval_override, use_shared_gateway_db
from ..services.graph_ops import submit_run
from ..services.replay_ops import replay_run
from ..core.config import settings

router = APIRouter()


def _default_action_mode(demo: dict | None = None) -> str:
    cfg = demo if isinstance(demo, dict) else get_demo_config()
    if cfg.get("demo_mode") and cfg.get("live_actions_enabled"):
        return "live"
    return "shadow"


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return None


def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _load_workflow_dag(wf_id: str) -> dict | None:
    root = _workspace_root()
    if not root:
        return None
    registry = _load_json(root / "memory" / "automation" / "dag_registry.json")
    rel = registry.get(wf_id)
    if not isinstance(rel, str) or not rel.strip():
        return None
    dag_path = root / rel
    if not dag_path.exists():
        return None
    dag_blob = _load_json(dag_path)
    return dag_blob if dag_blob else None


def _merge_graph_inputs(dag: dict, extra_inputs: dict | None) -> dict:
    if not isinstance(extra_inputs, dict) or not extra_inputs:
        return dag
    out = dict(dag)
    base_inputs = out.get("inputs") if isinstance(out.get("inputs"), dict) else {}
    out["inputs"] = {**base_inputs, **extra_inputs}
    return out


# ----- Health (no auth) -----


@router.get("/health")
def health():
    return {"ok": True, "status": "ok"}


@router.get("/env")
def env_banner():
    """Return environment label for UI banner (Demo / Staging / Prod). No auth required."""
    demo = get_demo_config()
    action_mode = "live" if demo.get("live_actions_enabled") else "shadow"
    return {
        "env": os.getenv("HG_ENV", "Demo"),
        "safe_local_only": settings.safe_local_only,
        "runtime_mode": settings.runtime_mode,
        "action_mode": action_mode,
        "live_actions_enabled": bool(demo.get("live_actions_enabled")),
        "demo_mode": bool(demo.get("demo_mode")),
    }


@router.get("/config/demo")
def demo_config(_role: str = Depends(require_product_role("viewer"))):
    """Demo toggles for product UI (live vs shadow actions)."""
    return get_demo_config()


@router.get("/openapi.json")
def openapi_spec():
    """Serve OpenAPI 3 spec for product API (for docs page / Swagger)."""
    try:
        from hg_lib.config import get_workspace_root
        root = get_workspace_root()
        if root:
            yaml_path = root / "docs" / "specs" / "ch4" / "openapi_v1.yaml"
            if yaml_path.exists():
                import yaml
                with open(yaml_path, encoding="utf-8") as f:
                    return yaml.safe_load(f)
    except Exception:
        pass
    return {"openapi": "3.0.3", "info": {"title": "Hydrogenuine Product API", "version": "0.1.0"}, "paths": {}}


# ----- Workflows (viewer+) -----


@router.get("/workflows")
def workflows_list(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.list_workflows(status=status, limit=limit, offset=offset)


@router.get("/workflows/{wf_id}")
def workflow_detail(wf_id: str, _role: str = Depends(require_product_role("viewer"))):
    w = svc.get_workflow(wf_id)
    if not w:
        raise HTTPException(status_code=404, detail="workflow not found")
    return w


@router.get("/workflows/{wf_id}/runs")
def workflow_runs(
    wf_id: str,
    limit: int = 50,
    offset: int = 0,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.list_workflow_runs(wf_id, limit=limit, offset=offset)


# ----- Runs (viewer+) -----


@router.get("/runs")
def runs_list(
    workflow_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.list_runs(workflow_id=workflow_id, status=status, limit=limit, offset=offset)


@router.get("/runs/{run_id}")
def run_detail(run_id: str, _role: str = Depends(require_product_role("viewer"))):
    r = svc.get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")
    return r


@router.get("/runs/{run_id}/artifacts")
def run_artifacts(run_id: str, _role: str = Depends(require_product_role("viewer"))):
    a = svc.list_run_artifacts(run_id)
    if a is None:
        raise HTTPException(status_code=404, detail="run not found")
    return a


# ----- Approvals (viewer+) -----


@router.get("/approvals")
def approvals_list(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.list_approvals(limit=limit, offset=offset, status=status)


@router.get("/approvals/{aid}")
def approval_detail(aid: str, _role: str = Depends(require_product_role("viewer"))):
    a = svc.get_approval(aid)
    if not a:
        raise HTTPException(status_code=404, detail="approval not found")
    return a


# ----- Incidents (viewer+) -----


@router.get("/incidents")
def incidents_list(
    limit: int = 50,
    offset: int = 0,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.list_deadletters(limit=limit, offset=offset)


@router.get("/incidents/{did}")
def incident_detail(did: str, _role: str = Depends(require_product_role("viewer"))):
    d = svc.get_deadletter(did)
    if not d:
        raise HTTPException(status_code=404, detail="incident not found")
    return d


@router.post("/incidents/{did}/replay")
def incident_replay(
    did: str,
    body: dict | None = None,
    role: str = Depends(require_product_role("operator")),
):
    """Replay a dead-letter incident in shadow mode (no side effects)."""
    incident = svc.get_deadletter(did)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    shadow = True
    if isinstance(body, dict) and body.get("shadow") is False:
        demo = get_demo_config()
        if demo.get("demo_mode") and not demo.get("live_actions_enabled"):
            shadow = True
        else:
            shadow = False
    from hg_core.task_graph import operator_ux

    result = operator_ux.replay_dead_letter(did, shadow=shadow, workspace_root=_workspace_root())
    append_audit(role, "incident_replay", did, {"shadow": shadow, "ok": result.get("ok")})
    return {"ok": bool(result.get("ok")), "incident_id": did, "shadow": shadow, **result}


@router.get("/runs/{run_id}/artifacts/download")
def run_artifact_download(
    run_id: str,
    name: str,
    _role: str = Depends(require_product_role("viewer")),
):
    path = svc.resolve_run_artifact_path(run_id, name)
    if not path:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path=str(path), filename=path.name, media_type="application/octet-stream")


# ----- Policies (viewer+) -----


@router.get("/policies/blacklist")
def policies_blacklist(_role: str = Depends(require_product_role("viewer"))):
    return svc.get_blacklist()


# ----- Metrics (viewer+) -----


@router.get("/metrics/summary")
def metrics_summary(
    period: str = "daily",
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.get_metrics_summary(period=period)


@router.get("/metrics/reports")
def metrics_reports(
    limit: int = 20,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.get_metrics_reports(limit=limit)


@router.get("/metrics/reports/file/{report_ref:path}")
def metrics_report_file(
    report_ref: str,
    _role: str = Depends(require_product_role("viewer")),
):
    path = resolve_dashboard_report_path(report_ref)
    if not path:
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(path=str(path), filename=path.name, media_type="application/octet-stream")


# ----- Templates (viewer+) -----


@router.get("/templates")
def templates_list(_role: str = Depends(require_product_role("viewer"))):
    return svc.list_templates()


@router.post("/templates/{template_id}/instantiate")
def templates_instantiate(
    template_id: str,
    body: dict | None = None,
    _role: str = Depends(require_product_role("viewer")),
):
    return svc.instantiate_template(template_id, body or {})


# ----- Audit export (viewer+) -----


@router.get("/runs/{run_id}/audit-report")
def run_audit_report(run_id: str, _role: str = Depends(require_product_role("viewer"))):
    r = svc.get_audit_report(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")
    return r


# ----- Actions (operator/admin) -----


@router.post("/workflows/{wf_id}/run")
def workflow_run(
    wf_id: str,
    body: dict,
    role: str = Depends(require_product_role("operator")),
):
    demo = get_demo_config()
    mode = body.get("mode") or _default_action_mode(demo)
    if demo.get("demo_mode") and mode == "live" and not demo.get("live_actions_enabled"):
        mode = "shadow"
    template_id = body.get("template_id")
    graph_inputs = body.get("inputs") if isinstance(body.get("inputs"), dict) else {}

    if mode not in {"shadow", "live"}:
        raise HTTPException(status_code=400, detail="mode must be shadow or live")

    if template_id:
        instantiated = svc.instantiate_template(template_id, body)
        if not instantiated.get("ok"):
            err = instantiated.get("error") if isinstance(instantiated.get("error"), dict) else {}
            raise HTTPException(status_code=400, detail=err.get("message") or "template instantiation failed")
        dag = instantiated.get("dag")
    else:
        dag = _load_workflow_dag(wf_id)

    if not isinstance(dag, dict):
        raise HTTPException(status_code=404, detail="workflow not found")

    dag = _merge_graph_inputs(dag, graph_inputs)
    run_result = submit_run(dag)
    if run_result.get("ok") is not True:
        raise HTTPException(status_code=500, detail="run submission failed")

    append_audit(role, "workflow_run", wf_id, {"mode": mode, "template_id": template_id})
    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "workflow_id": wf_id,
            "mode": mode,
            "template_id": template_id,
            "run_id": run_result.get("run_id"),
            "status": run_result.get("status"),
        },
    )


@router.post("/workflows/{wf_id}/pause")
def workflow_pause(wf_id: str, role: str = Depends(require_product_role("operator"))):
    from hg_core.task_graph import operator_ux

    result = operator_ux.pause_workflow(wf_id, workspace_root=_workspace_root())
    append_audit(role, "workflow_pause", wf_id)
    return {"ok": True, **result}


@router.post("/workflows/{wf_id}/resume")
def workflow_resume(wf_id: str, role: str = Depends(require_product_role("operator"))):
    from hg_core.task_graph import operator_ux

    result = operator_ux.resume_workflow(wf_id, workspace_root=_workspace_root())
    append_audit(role, "workflow_resume", wf_id)
    return {"ok": True, **result}


@router.post("/runs/{run_id}/replay")
def run_replay(
    run_id: str,
    body: dict | None = None,
    role: str = Depends(require_product_role("operator")),
):
    mode = (body or {}).get("mode", "shadow")
    if mode != "shadow":
        raise HTTPException(status_code=400, detail="only shadow replay is supported")
    result = replay_run(run_id)
    if result.get("ok") is not True:
        err = result.get("error") if isinstance(result.get("error"), dict) else {}
        if err.get("code") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=err.get("message") or "run not found")
        raise HTTPException(status_code=400, detail=err.get("message") or "replay failed")
    append_audit(role, "run_replay", run_id, {"mode": mode})
    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "run_id": run_id,
            "mode": mode,
            "replay_run_id": result.get("run_id"),
            "status": result.get("status"),
        },
    )


@router.post("/runs/{run_id}/rollback")
def run_rollback(
    run_id: str,
    body: dict | None = None,
    role: str = Depends(require_product_role("operator")),
):
    mode = (body or {}).get("mode", "shadow")
    if mode != "shadow":
        raise HTTPException(status_code=400, detail="only shadow rollback is supported")
    run = svc.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    workflow_id = str(run.get("graph_id") or "")
    if not workflow_id:
        raise HTTPException(status_code=400, detail="run missing workflow id")
    from hg_core.task_graph import operator_ux

    result = operator_ux.rollback_to_last_good(workflow_id, workspace_root=_workspace_root())
    append_audit(role, "run_rollback", run_id, {"mode": mode})
    return {
        "ok": True,
        "accepted": True,
        "run_id": run_id,
        "workflow_id": workflow_id,
        "mode": mode,
        **result,
    }


@router.post("/approvals/{aid}/override")
def approval_override(
    aid: str,
    body: dict,
    role: str = Depends(require_product_role("admin")),
):
    decision = body.get("decision", "approve")
    if decision not in {"approve", "deny"}:
        raise HTTPException(status_code=400, detail="decision must be approve or deny")

    root = _workspace_root()
    if root is not None:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        append_approval_override(aid, decision, role, timestamp)
        overrides_path = root / "memory" / "automation" / "approval_overrides.jsonl"
        if not use_shared_gateway_db(overrides_path):
            overrides_path.parent.mkdir(parents=True, exist_ok=True)
            with overrides_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "approval_id": aid,
                            "decision": decision,
                            "timestamp": timestamp,
                            "role": role,
                        }
                    )
                    + "\n"
                )

    append_audit(role, "approval_override", aid, {"decision": decision})
    return JSONResponse(status_code=202, content={"accepted": True, "approval_id": aid, "decision": decision})
