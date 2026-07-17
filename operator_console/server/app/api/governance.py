from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from hg_core.constitutional_memory import add_checkpoint, add_drift_event, get_constitutional_root, list_constitutional_roots, upsert_constitutional_root
from hg_core.governance_contracts import list_contract_schemas
from hg_core.gate import create_benchmark_set, create_release_verdict, evaluate_benchmark_run, get_release_gate_status, list_benchmark_sets, list_gate_evaluations, record_benchmark_run
from hg_core.policy_registry import activate_policy_version, add_policy_feedback, create_policy_version, get_policy_version, list_policy_registry, rollback_policy_version, run_policy_simulation
from hg_core.receipts import export_receipt, get_receipt, list_receipts, verify_receipt
from hg_core.research_product import get_research_run, list_research_runs, sync_workspace

from ..services.drift_review_summary import build_drift_review_summary
from ..services.continuity_incident_summary import build_continuity_quality_overview
from ..services.entities_service import list_entities
from ..core.auth import require_api_key

router = APIRouter()


class ReceiptVerifyBody(BaseModel):
    receipt_id: str


class PolicyVersionBody(BaseModel):
    policy_key: str
    title: str
    category: str
    description: str | None = None
    content: dict
    rationale: str | None = None
    change_summary: str | None = None
    actor_id: str | None = None


class PolicySimulationBody(BaseModel):
    version_id: str
    scenario_label: str
    inputs: dict
    actor_id: str | None = None


class PolicyFeedbackBody(BaseModel):
    version_id: str
    summary: str
    sentiment: str | None = None
    details: dict | None = None
    author_id: str | None = None


class ConstitutionalRootBody(BaseModel):
    root_id: str | None = None
    workflow_family: str
    title: str
    root_goal: str
    owner_id: str | None = None
    accountable_actor: str | None = None
    material_constraints: list[str] = Field(default_factory=list)
    approved_subgoals: list[str] = Field(default_factory=list)
    policy_version_id: str | None = None
    status: str = "active"


class CheckpointBody(BaseModel):
    summary: str
    state: dict
    alignment_score: float | None = None
    actor_id: str | None = None


class DriftBody(BaseModel):
    severity: str
    summary: str
    details: dict = Field(default_factory=dict)
    actor_id: str | None = None


class BenchmarkSetBody(BaseModel):
    workflow_family: str
    title: str
    description: str | None = None
    weights: dict[str, float]


class BenchmarkRunBody(BaseModel):
    benchmark_set_id: str
    workflow_family: str
    candidate_label: str
    observations: dict
    actor_id: str | None = None


class GateEvaluationBody(BaseModel):
    benchmark_run_id: str
    policy_version_id: str | None = None


class ReleaseVerdictBody(BaseModel):
    workflow_family: str
    target_kind: str = "workflow"
    target_id: str
    evaluation_id: str | None = None
    verdict: str
    reason: str | None = None
    stale_after_hours: float = 24.0


class ResearchWorkspaceSyncBody(BaseModel):
    actor_id: str | None = None


@router.get("/drift")
def drift_review(
    workflow_family: str | None = Query(None),
    root_id: str | None = Query(None),
    baseline_root_id: str | None = Query(None),
    entity_id: str | None = Query(None),
    limit: int = Query(12, ge=1, le=50),
    _=Depends(require_api_key),
):
    return {
        "ok": True,
        "drift_review": build_drift_review_summary(
            workflow_family=workflow_family,
            root_id=root_id,
            baseline_root_id=baseline_root_id,
            entity_id=entity_id,
            limit=limit,
        ),
    }


@router.get("/dashboard")
def governance_dashboard(_=Depends(require_api_key)):
    try:
        receipts = list_receipts(limit=10)
        policies = list_policy_registry()
        roots = list_constitutional_roots()
        evaluations = list_gate_evaluations(limit=10)
        research_runs = list_research_runs(tenant_id="default", limit=20)
        continuity_quality = build_continuity_quality_overview(list_entities())
        return {
            "ok": True,
            "counts": {
                "receipts": len(receipts),
                "policies": len(policies),
                "constitutional_roots": len(roots),
                "gate_evaluations": len(evaluations),
                "research_runs": len(research_runs),
            },
            "recent_receipts": receipts,
            "policies": policies[:10],
            "constitutional_roots": roots[:10],
            "gate_evaluations": evaluations,
            "continuity_quality": continuity_quality,
        }
    except Exception as e:
        return {
            "ok": True,
            "counts": {
                "receipts": 0,
                "policies": 0,
                "constitutional_roots": 0,
                "gate_evaluations": 0,
                "research_runs": 0,
            },
            "recent_receipts": [],
            "policies": [],
            "constitutional_roots": [],
            "gate_evaluations": [],
            "continuity_quality": {
                "status": "missing",
                "entity_count": 0,
                "healthy_count": 0,
                "watch_count": 0,
                "blocked_count": 0,
                "average_quality_score": 0.0,
                "average_coverage_score": 0.0,
                "average_attribution_score": 0.0,
                "average_operator_override_rate": 0.0,
                "average_promotion_accuracy": 0.0,
                "summary": "No continuity quality scores available.",
            },
            "backend_error": str(e),
        }


@router.get("/receipts")
def receipts(receipt_kind: str | None = Query(None), limit: int = Query(50, ge=1, le=200), _=Depends(require_api_key)):
    return {"ok": True, "receipts": list_receipts(receipt_kind=receipt_kind, limit=limit)}


@router.get("/receipts/{receipt_id}")
def receipt_detail(receipt_id: str, _=Depends(require_api_key)):
    receipt = get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="receipt not found")
    return {"ok": True, "receipt": receipt}


@router.post("/receipts/{receipt_id}/verify")
def receipt_verify(receipt_id: str, _=Depends(require_api_key)):
    try:
        return {"ok": True, "receipt": verify_receipt(receipt_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="receipt not found")


@router.get("/receipts/{receipt_id}/export")
def receipt_export(receipt_id: str, _=Depends(require_api_key)):
    try:
        return {"ok": True, **export_receipt(receipt_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="receipt not found")


@router.get("/contracts")
def governance_contracts(_=Depends(require_api_key)):
    return {"ok": True, "contracts": list_contract_schemas()}


@router.get("/policies")
def policies(_=Depends(require_api_key)):
    return {"ok": True, "policies": list_policy_registry()}


@router.post("/policies/versions")
def policy_version_create(body: PolicyVersionBody, _=Depends(require_api_key)):
    return {"ok": True, **create_policy_version(**body.model_dump())}


@router.get("/policies/versions/{version_id}")
def policy_version_detail(version_id: str, _=Depends(require_api_key)):
    version = get_policy_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="policy version not found")
    return {"ok": True, "version": version}


@router.post("/policies/versions/{version_id}/simulate")
def policy_version_simulate(version_id: str, body: PolicySimulationBody, _=Depends(require_api_key)):
    if version_id != body.version_id:
        raise HTTPException(status_code=400, detail="version id mismatch")
    return {"ok": True, **run_policy_simulation(**body.model_dump())}


@router.post("/policies/versions/{version_id}/activate")
def policy_version_activate(version_id: str, actor_id: str | None = None, _=Depends(require_api_key)):
    try:
        return {"ok": True, **activate_policy_version(version_id, actor_id=actor_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="policy version not found")


@router.post("/policies/{policy_key}/rollback")
def policy_version_rollback(policy_key: str, actor_id: str | None = None, _=Depends(require_api_key)):
    try:
        return {"ok": True, **rollback_policy_version(policy_key, actor_id=actor_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail="policy rollback target not found")


@router.post("/policies/feedback")
def policy_feedback_create(body: PolicyFeedbackBody, _=Depends(require_api_key)):
    return {"ok": True, **add_policy_feedback(**body.model_dump())}


@router.get("/constitutional-roots")
def constitutional_roots(_=Depends(require_api_key)):
    return {"ok": True, "roots": list_constitutional_roots()}


@router.post("/constitutional-roots")
def constitutional_root_upsert(body: ConstitutionalRootBody, _=Depends(require_api_key)):
    return {"ok": True, **upsert_constitutional_root(**body.model_dump())}


@router.get("/constitutional-roots/{root_id}")
def constitutional_root_detail(root_id: str, _=Depends(require_api_key)):
    root = get_constitutional_root(root_id)
    if not root:
        raise HTTPException(status_code=404, detail="root not found")
    return {"ok": True, **root}


@router.post("/constitutional-roots/{root_id}/checkpoints")
def constitutional_root_checkpoint(root_id: str, body: CheckpointBody, _=Depends(require_api_key)):
    return {"ok": True, **add_checkpoint(root_id=root_id, **body.model_dump())}


@router.post("/constitutional-roots/{root_id}/drift")
def constitutional_root_drift(root_id: str, body: DriftBody, _=Depends(require_api_key)):
    return {"ok": True, **add_drift_event(root_id=root_id, **body.model_dump())}


@router.get("/gate/benchmark-sets")
def gate_benchmark_sets(_=Depends(require_api_key)):
    return {"ok": True, "benchmark_sets": list_benchmark_sets()}


@router.post("/gate/benchmark-sets")
def gate_benchmark_set_create(body: BenchmarkSetBody, _=Depends(require_api_key)):
    return {"ok": True, **create_benchmark_set(**body.model_dump())}


@router.post("/gate/benchmark-runs")
def gate_benchmark_run_create(body: BenchmarkRunBody, _=Depends(require_api_key)):
    return {"ok": True, **record_benchmark_run(**body.model_dump())}


@router.post("/gate/evaluate")
def gate_evaluate(body: GateEvaluationBody, _=Depends(require_api_key)):
    try:
        return {"ok": True, **evaluate_benchmark_run(**body.model_dump())}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"missing benchmark state: {exc}")


@router.get("/gate/evaluations")
def gate_evaluations(workflow_family: str | None = Query(None), limit: int = Query(50, ge=1, le=200), _=Depends(require_api_key)):
    return {"ok": True, "evaluations": list_gate_evaluations(workflow_family=workflow_family, limit=limit)}


@router.post("/gate/release-verdicts")
def gate_release_verdict_create(body: ReleaseVerdictBody, _=Depends(require_api_key)):
    return {"ok": True, **create_release_verdict(**body.model_dump())}


@router.get("/gate/check/{workflow_family}")
def gate_check(workflow_family: str, target_kind: str = Query("workflow"), target_id: str | None = Query(None), max_age_hours: float = Query(24.0, ge=1.0, le=168.0), _=Depends(require_api_key)):
    return {"ok": True, **get_release_gate_status(workflow_family=workflow_family, target_kind=target_kind, target_id=target_id, max_age_hours=max_age_hours)}


@router.get("/demo-path/{workflow_family}")
def gate_demo_path(workflow_family: str, _=Depends(require_api_key)):
    roots = [root for root in list_constitutional_roots() if str(root.get("workflow_family") or "") == workflow_family]
    evaluations = list_gate_evaluations(workflow_family=workflow_family, limit=5)
    receipts = list_receipts(limit=20)
    latest_root = roots[0] if roots else None
    latest_receipt = receipts[0] if receipts else None
    return {
        "ok": True,
        "workflow_family": workflow_family,
        "constitutional_root": latest_root,
        "drift_detected": bool(latest_root and str(latest_root.get("drift_severity") or "stable") != "stable"),
        "policy_evaluated": bool(evaluations),
        "gate_verdict": evaluations[0] if evaluations else None,
        "receipt_visible": latest_receipt,
        "export_ready": bool(latest_receipt),
    }


@router.post("/research/workspaces/{chat_id}/sync")
def research_workspace_sync(chat_id: str, body: ResearchWorkspaceSyncBody, _=Depends(require_api_key)):
    return {"ok": True, **sync_workspace(tenant_id="default", chat_id=chat_id, actor_id=body.actor_id)}


@router.get("/research/runs")
def research_runs(limit: int = Query(20, ge=1, le=100), _=Depends(require_api_key)):
    return {"ok": True, "runs": list_research_runs(tenant_id="default", limit=limit)}


@router.get("/research/runs/{research_run_id}")
def research_run_detail(research_run_id: str, _=Depends(require_api_key)):
    run = get_research_run(tenant_id="default", research_run_id=research_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="research run not found")
    return {"ok": True, "run": run}
