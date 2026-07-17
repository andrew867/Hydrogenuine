"""Fault injection API: list scenarios and execute simulated runs."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key

router = APIRouter()


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


@router.get("/scenarios")
def list_scenarios(_=Depends(require_api_key)):
    """List fault scenario IDs and per-workflow coverage."""
    try:
        from hg_core.task_graph.fault_injection import (
            get_scenarios_for_workflow,
            WORKFLOW_SCENARIOS,
        )
        from hg_core.task_graph.workflow_registry import get_primary_workflow_ids
        ids = get_primary_workflow_ids()
        by_workflow = {wid: get_scenarios_for_workflow(wid) for wid in ids}
        scenarios = list({s for wf_scenarios in by_workflow.values() for s in wf_scenarios})
        return {"ok": True, "scenarios": scenarios, "by_workflow": by_workflow}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class RunScenarioBody(BaseModel):
    workflow_id: str
    scenario_id: str
    step_index: int = 0
    fake_destination_ledger: list | None = None


@router.post("/run")
def run_scenario(body: RunScenarioBody, _=Depends(require_api_key)):
    """Run a single fault scenario (fake destinations only; no side effects)."""
    try:
        from hg_core.task_graph.fault_injection import run_scenario as _run_scenario
        ledger = body.fake_destination_ledger if body.fake_destination_ledger is not None else []
        outcome = _run_scenario(
            workflow_id=body.workflow_id,
            scenario_id=body.scenario_id,
            step_index=body.step_index,
            fake_destination_ledger=ledger,
        )
        return {"ok": True, "outcome": outcome}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
