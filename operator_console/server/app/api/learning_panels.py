"""Learning loop operator panels API (L1)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.evolution_panels_service import (
    approve_evolution_proposal,
    get_lineage_tree,
    list_evolution_proposals,
    propose_evolution,
    rollback_evolution,
)
from ..services.learning_panels_service import (
    deposit_capability_escrow,
    get_control_group_stats,
    get_learning_activity,
    get_learning_telemetry,
    get_live_priors,
    get_relabel_queue,
    get_shadow_ledger,
    get_track_records,
    list_capability_escrow,
    post_operator_relabel,
    replay_capability_escrow,
    resolve_learning_incident,
    run_shadow_feedback,
    sync_learning_corpus,
    unfreeze_learning_parameter,
    unfreeze_learning_path,
)

router = APIRouter()


class RelabelBody(BaseModel):
    verdict: str = Field(..., description="success | rejected | partial | unknown")
    actor_id: str = "operator"
    rationale: str = ""


class EvolutionApproveBody(BaseModel):
    operator_id: str = "operator"
    written_justification: str = ""


class EvolutionProposeBody(BaseModel):
    entity_id: str
    profile: Dict[str, Any] = Field(default_factory=dict)


@router.post("/sync")
def sync_corpus(_=Depends(require_api_key)) -> Dict[str, Any]:
    return sync_learning_corpus()


@router.get("/telemetry")
def telemetry(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_learning_telemetry()


@router.get("/relabel-queue")
def relabel_queue(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_relabel_queue()


@router.post("/relabel/{signal_id}")
def relabel_signal(signal_id: str, body: RelabelBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = post_operator_relabel(
        signal_id,
        verdict=body.verdict,
        actor_id=body.actor_id,
        rationale=body.rationale,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "invalid"))
    return result


@router.get("/track-records")
def track_records(entity_id: Optional[str] = None, _=Depends(require_api_key)) -> Dict[str, Any]:
    return get_track_records(entity_id=entity_id)


@router.get("/track-records/{entity_id}")
def track_record_detail(entity_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    return get_track_records(entity_id=entity_id)


@router.post("/shadow/run")
def shadow_run(_=Depends(require_api_key)) -> Dict[str, Any]:
    return run_shadow_feedback()


@router.get("/shadow/ledger")
def shadow_ledger(path: str | None = None, limit: int = 100, _=Depends(require_api_key)) -> Dict[str, Any]:
    return get_shadow_ledger(path_name=path, limit=limit)


@router.get("/activity")
def learning_activity(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_learning_activity()


@router.get("/live/priors")
def live_priors(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_live_priors()


@router.post("/live/unfreeze-path/{path_name}")
def unfreeze_path(path_name: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    return unfreeze_learning_path(path_name)


@router.post("/live/unfreeze-parameter/{parameter}")
def unfreeze_parameter(parameter: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    return unfreeze_learning_parameter(parameter)


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    return resolve_learning_incident(incident_id)


@router.get("/control-group/stats")
def control_group_stats(_=Depends(require_api_key)) -> Dict[str, Any]:
    return get_control_group_stats()


class EscrowDepositBody(BaseModel):
    source_entity: str
    profile: Dict[str, Any] = Field(default_factory=dict)
    steering: Dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)


class EscrowReplayBody(BaseModel):
    target_entity: str = "operator"


@router.get("/escrow")
def escrow_list(_=Depends(require_api_key)) -> Dict[str, Any]:
    return list_capability_escrow()


@router.post("/escrow/deposit")
def escrow_deposit(body: EscrowDepositBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = deposit_capability_escrow(body.model_dump())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "deposit_failed"))
    return result


@router.post("/escrow/{escrow_id}/replay")
def escrow_replay(escrow_id: str, body: EscrowReplayBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = replay_capability_escrow(escrow_id, target_entity=body.target_entity)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "replay_failed"))
    return result


@router.get("/lineage/{entity_id}")
def lineage_tree(entity_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    return get_lineage_tree(entity_id)


@router.get("/evolution/proposals")
def evolution_proposals(entity_id: Optional[str] = None, _=Depends(require_api_key)) -> Dict[str, Any]:
    return list_evolution_proposals(entity_id=entity_id)


@router.post("/evolution/propose")
def evolution_propose(_=Depends(require_api_key), req: EvolutionProposeBody = ...) -> Dict[str, Any]:
    return propose_evolution(req.entity_id, req.profile)


@router.post("/evolution/proposals/{proposal_id}/approve")
def evolution_approve(
    proposal_id: str,
    _=Depends(require_api_key),
    req: EvolutionApproveBody = ...,
) -> Dict[str, Any]:
    result = approve_evolution_proposal(
        proposal_id,
        operator_id=req.operator_id,
        written_justification=req.written_justification,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "invalid"))
    return result


@router.post("/evolution/rollback/{entity_id}")
def evolution_rollback(entity_id: str, _=Depends(require_api_key)) -> Dict[str, Any]:
    result = rollback_evolution(entity_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "invalid"))
    return result
