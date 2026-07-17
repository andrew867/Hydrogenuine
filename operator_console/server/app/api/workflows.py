"""Workflow API: registry, checks, and scheduled DAG job editing."""

from datetime import datetime, timezone
from pathlib import Path

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.scheduled_jobs_service import (
    list_scheduled_jobs,
    read_scheduled_dag,
    save_scheduled_dag,
)
from ..services.review_handoff_summary import build_workflow_status_summary
from ..services.run_index_db import list_runs as list_runs_index
from ..services.graph_ops import submit_run
from ..services import approval_store
from hg_core.gate import enforce_release_gate

router = APIRouter()


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


@router.get("")
def list_workflows(_=Depends(require_api_key)):
    """List primary workflows (workflow_id, display_name, category, readiness, ...)."""
    try:
        from hg_core.task_graph.workflow_registry import (
            get_declared_workflow_ids,
            load_workflow_registry,
        )
        root = _workspace_root()
        registry = load_workflow_registry(root)
        ids = get_declared_workflow_ids()
        workflows = [registry.get(wid, {}) for wid in ids if wid in registry]
        return {"ok": True, "workflows": workflows}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class AcceptanceChecksBody(BaseModel):
    run_context: dict | None = None


class SaveScheduledDagBody(BaseModel):
    dag: dict


class RunScheduledJobBody(BaseModel):
    goal: str | None = None


def _schedule_recurrence_str(entry) -> str | None:
    """Human-readable schedule: 'every N min' or cron expression."""
    if getattr(entry, "interval_minutes", None) is not None:
        return f"every {int(entry.interval_minutes)} min"
    if getattr(entry, "cron", None):
        return entry.cron
    return None


@router.get("/scheduled-jobs")
def list_scheduled(_=Depends(require_api_key)):
    root = _workspace_root()
    if root is None:
        raise HTTPException(status_code=503, detail="workspace root unavailable")
    jobs = list_scheduled_jobs(root)
    # Last run per job (graph_id): list_runs is newest-first, so first occurrence = latest
    try:
        runs = list_runs_index(limit=500)
        last_by_graph = {}
        for r in runs:
            g = r.get("graph_id")
            if g and g not in last_by_graph:
                last_by_graph[g] = r.get("started_at")
    except Exception:
        last_by_graph = {}
    # Schedule recurrence and next run from realtime_schedule.json
    try:
        from hg_realtime.scheduler.schedule_config import load_schedule
        from hg_realtime.scheduler.schedule_config import _compute_next  # noqa: PLC2701
        state = load_schedule(root)
        by_job = {e.job_id: e for e in state.entries}
        now = datetime.now(timezone.utc)
        for j in jobs:
            entry = by_job.get(j["job_id"])
            if entry:
                j["schedule_recurrence"] = _schedule_recurrence_str(entry)
                try:
                    j["next_run"] = _compute_next(entry, now, workspace_root=root).isoformat()
                except Exception:
                    j["next_run"] = None
            else:
                j["schedule_recurrence"] = None
                j["next_run"] = None
            j["last_run"] = last_by_graph.get(j["job_id"])
    except Exception:
        for j in jobs:
            j.setdefault("schedule_recurrence", None)
            j.setdefault("next_run", None)
            j.setdefault("last_run", last_by_graph.get(j["job_id"]))
    return {"ok": True, "jobs": jobs}


@router.get("/scheduled-jobs/{job_id}/dag")
def get_scheduled_dag(job_id: str, _=Depends(require_api_key)):
    root = _workspace_root()
    if root is None:
        raise HTTPException(status_code=503, detail="workspace root unavailable")
    try:
        payload = read_scheduled_dag(root, job_id)
        return {"ok": True, **payload}
    except KeyError:
        raise HTTPException(status_code=404, detail="scheduled job not found")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"DAG file missing: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"DAG parse error: {e}")


@router.put("/scheduled-jobs/{job_id}/dag")
def put_scheduled_dag(job_id: str, body: SaveScheduledDagBody, _=Depends(require_api_key)):
    root = _workspace_root()
    if root is None:
        raise HTTPException(status_code=503, detail="workspace root unavailable")
    try:
        payload = save_scheduled_dag(root, job_id, body.dag)
        return {"ok": True, **payload}
    except KeyError:
        raise HTTPException(status_code=404, detail="scheduled job not found")
    except ValueError as e:
        msg = str(e)
        try:
            detail = json.loads(msg)
        except json.JSONDecodeError:
            detail = {"code": "INVALID_DAG", "message": msg}
        raise HTTPException(status_code=400, detail=detail)


@router.post("/scheduled-jobs/{job_id}/run")
def run_scheduled_job(job_id: str, body: RunScheduledJobBody | None = None, _=Depends(require_api_key)):
    """Manually trigger a scheduled DAG job run. Returns { ok, run_id } or error."""
    root = _workspace_root()
    if root is None:
        raise HTTPException(status_code=503, detail="workspace root unavailable")
    try:
        scheduled_jobs = list_scheduled_jobs(root)
        scheduled_job = next((item for item in scheduled_jobs if item.get("job_id") == job_id), None)
        if not isinstance(scheduled_job, dict):
            raise KeyError(job_id)
        workflow_family = str(scheduled_job.get("workflow_id") or job_id).strip() or job_id
        gate = enforce_release_gate(workflow_family=workflow_family, target_kind="workflow", target_id=workflow_family)
        if not gate.get("ok"):
            raise HTTPException(status_code=423, detail={"code": gate.get("code"), "message": gate.get("reason")})
        agency_control = scheduled_job.get("agency_control") or {}
        if str((agency_control or {}).get("effective_mode") or (agency_control or {}).get("mode") or "").strip().lower() == "held":
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "AGENCY_CONTROL_HELD",
                    "message": (agency_control or {}).get("reason") or "scheduled job is held by operator agency control",
                },
            )
        if bool((agency_control or {}).get("outbound_budget_exhausted")):
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "AGENCY_OUTBOUND_BUDGET_EXHAUSTED",
                    "message": (
                        (agency_control or {}).get("reason")
                        or f"scheduled job exhausted outbound budget ({(agency_control or {}).get('recent_outbound_action_count')}/{(agency_control or {}).get('daily_outbound_budget')})"
                    ),
                },
            )
        continuity_recovery = scheduled_job.get("continuity_recovery_readiness") or {}
        continuity_status = str((continuity_recovery or {}).get("status") or "").strip().lower()
        if continuity_status == "blocked":
            blocking = list((continuity_recovery or {}).get("blocking") or [])
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "POST_REBUILD_CONTINUITY_CHECK_BLOCKED" if "post_rebuild_continuity_check_blocked" in blocking else "CONTINUITY_RECOVERY_BLOCKED",
                    "message": ", ".join(blocking) or "scheduled job is blocked by continuity recovery state",
                },
            )
        if continuity_status == "caution" and not bool((continuity_recovery or {}).get("resume_permitted")):
            cautions = list((continuity_recovery or {}).get("cautions") or [])
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "POST_REBUILD_CONTINUITY_CHECK_REQUIRED" if "post_rebuild_continuity_check_pending" in cautions else "CONTINUITY_RECOVERY_ACK_REQUIRED",
                    "message": ", ".join(cautions) or "scheduled job requires continuity recovery acknowledgment before resume",
                },
            )
        operational_resume_governance = scheduled_job.get("operational_resume_governance_summary") or {}
        operational_resume_checkpoint = scheduled_job.get("operational_resume_checkpoint") or {}
        identity_restore_validation = scheduled_job.get("identity_restore_validation") or {}
        supervised_resume_validation = scheduled_job.get("supervised_resume_validation") or {}
        bounded_autonomy_policy = scheduled_job.get("bounded_autonomy_policy_summary") or {}
        blockers = list((bounded_autonomy_policy or {}).get("blockers") or [])
        if "identity_restore_validation_required" in blockers or "identity_restore_validation_blocked" in blockers:
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "IDENTITY_RESTORE_VALIDATION_REQUIRED",
                    "message": str((identity_restore_validation or {}).get("summary") or "scheduled job requires identity restore validation before resume"),
                },
            )
        if "supervised_resume_validation_required" in blockers:
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "SUPERVISED_RESUME_VALIDATION_REQUIRED",
                    "message": str((supervised_resume_validation or {}).get("summary") or "scheduled job requires supervised resume validation before resume"),
                },
            )
        if (
            str((operational_resume_governance or {}).get("status") or "").strip().lower() == "ready"
            and not bool((operational_resume_checkpoint or {}).get("approved"))
        ):
            checkpoint_reason = str((operational_resume_checkpoint or {}).get("invalidated_reason") or "").strip()
            checkpoint_message = "scheduled job requires a fresh operational resume checkpoint"
            if checkpoint_reason:
                checkpoint_message = f"{checkpoint_message}: {checkpoint_reason}"
            raise HTTPException(
                status_code=423,
                detail={
                    "code": "OPERATIONAL_RESUME_CHECKPOINT_REQUIRED",
                    "message": checkpoint_message,
                },
            )
        payload = read_scheduled_dag(root, job_id)
        dag = payload.get("dag")
        if not isinstance(dag, dict):
            raise HTTPException(status_code=500, detail="DAG load failed")
        dag_for_run = dict(dag)
        dag_inputs = dict(dag.get("inputs") or {})
        scheduled_inputs = scheduled_job.get("inputs") if isinstance(scheduled_job.get("inputs"), dict) else {}
        if not scheduled_inputs:
            try:
                from hg_realtime.scheduler.schedule_config import load_schedule

                state = load_schedule(root)
                entry = next((item for item in state.entries if item.job_id == job_id), None)
                if entry and isinstance(entry.inputs, dict):
                    scheduled_inputs = dict(entry.inputs)
            except Exception:
                scheduled_inputs = {}
        for key, value in scheduled_inputs.items():
            if key not in dag_inputs or dag_inputs.get(key) in ("", None):
                dag_inputs[key] = value
        dag_inputs.setdefault("scheduler_job_id", job_id)
        requested_goal = str(body.goal or "").strip() if body else ""
        if requested_goal:
            dag_inputs["goal"] = requested_goal
        dag_for_run["inputs"] = dag_inputs
        run_result = submit_run(dag_for_run)
        if run_result.get("ok") is not True:
            raise HTTPException(status_code=500, detail=run_result.get("error") or "run submission failed")
        return {
            "ok": True,
            "run_id": run_result.get("run_id"),
            "job_id": job_id,
            "status": run_result.get("status"),
            "goal": dag_inputs.get("goal"),
            "workflow_status_summary": build_workflow_status_summary(
                root,
                workflow_id=workflow_family,
                job_id=job_id,
                graph_id=str(dag.get("graph_id") or workflow_family).strip() or None,
                launch_run_id=str(run_result.get("run_id") or "").strip() or None,
                launch_status=str(run_result.get("status") or "").strip() or None,
                launch_goal=dag_inputs.get("goal"),
            ),
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="scheduled job not found")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"DAG file missing: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, _=Depends(require_api_key)):
    """Workflow declaration detail."""
    try:
        from hg_core.task_graph.workflow_registry import load_workflow_registry
        root = _workspace_root()
        registry = load_workflow_registry(root)
        if workflow_id not in registry:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"ok": True, "workflow": registry[workflow_id]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/{workflow_id}/acceptance-checks")
def run_acceptance_checks(workflow_id: str, body: AcceptanceChecksBody | None = None, _=Depends(require_api_key)):
    """Run acceptance checks for a workflow. Returns list of { check_id, passed, message }."""
    try:
        from hg_core.task_graph.workflow_registry import run_acceptance_checks
        root = _workspace_root()
        results = run_acceptance_checks(workflow_id, run_context=body.run_context if body else None, workspace_root=root)
        return {"ok": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{workflow_id}/dedup")
def workflow_dedup(workflow_id: str, limit: int = 100, _=Depends(require_api_key)):
    """Return dedupe ledger entries and run summary for a workflow."""
    try:
        root = _workspace_root()
        result = approval_store.get_workflow_dedup(
            workflow_id,
            workspace_root=root,
            limit=limit,
        )
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
