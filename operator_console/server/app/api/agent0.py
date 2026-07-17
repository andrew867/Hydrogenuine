"""Agent #0 operator surface API — runtime cockpit read + bounded control."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from hg_plt.control import ControlError, execute_control_action
from hg_plt.service import AgentZeroService

from ..core.auth import require_api_key

router = APIRouter()


def _workspace() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return Path.cwd()


def _service() -> AgentZeroService:
    return AgentZeroService(_workspace())


class ControlRequest(BaseModel):
    target_hash: str = Field(..., min_length=8)
    target_id: str = "runtime"
    operator_id: str = "op:local"
    reason: Optional[str] = None
    bundle_hash: Optional[str] = None
    provided_bundle_hash: Optional[str] = None
    binding_hash: Optional[str] = None
    provided_binding_hash: Optional[str] = None


def _control(action_type: str, body: ControlRequest) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if body.reason:
        extra["reason"] = body.reason
    if body.bundle_hash:
        extra["bundle_hash"] = body.bundle_hash
        extra["provided_bundle_hash"] = body.provided_bundle_hash or body.target_hash
    if body.binding_hash:
        extra["binding_hash"] = body.binding_hash
        extra["provided_binding_hash"] = body.provided_binding_hash or body.target_hash
    try:
        return execute_control_action(
            action_type,
            workspace=_workspace(),
            operator_id=body.operator_id,
            target_id=body.target_id,
            target_hash=body.target_hash,
            extra=extra or None,
        )
    except ControlError as exc:
        raise HTTPException(status_code=403, detail=exc.reason) from exc


@router.get("/status")
def agent0_status(_=Depends(require_api_key)):
    return _service().status()


@router.get("/world-state")
def agent0_world_state(_=Depends(require_api_key)):
    return _service().world_state_summary()


@router.get("/events")
def agent0_events(
    since_seq: Optional[int] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    subsystem: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _=Depends(require_api_key),
):
    return _service().events(
        since_seq=since_seq,
        event_type=event_type,
        subsystem=subsystem,
        limit=limit,
    )


@router.get("/proposals")
def agent0_proposals(_=Depends(require_api_key)):
    return _service().proposals()


@router.get("/governance")
def agent0_governance(_=Depends(require_api_key)):
    return _service().governance()


@router.get("/arousal")
def agent0_arousal(_=Depends(require_api_key)):
    return _service().arousal()


@router.get("/recovery")
def agent0_recovery(_=Depends(require_api_key)):
    return _service().recovery()


@router.get("/execution")
def agent0_execution(_=Depends(require_api_key)):
    return _service().execution()


@router.get("/maintenance")
def agent0_maintenance(_=Depends(require_api_key)):
    return _service().maintenance()


@router.get("/memory")
def agent0_memory(_=Depends(require_api_key)):
    return _service().memory()


@router.get("/proofs")
def agent0_proofs(_=Depends(require_api_key)):
    return _service().proofs()


@router.get("/subsystems")
def agent0_subsystems(_=Depends(require_api_key)):
    return _service().subsystems()


@router.get("/receipts")
def agent0_receipts(limit: int = Query(default=50, ge=1, le=200), _=Depends(require_api_key)):
    return _service().operator_receipts(limit=limit)


@router.post("/pause")
def agent0_pause(body: ControlRequest, _=Depends(require_api_key)):
    result = _control("pause", body)
    if not result.get("accepted"):
        raise HTTPException(status_code=403, detail=result.get("refusal_reason"))
    return result


@router.post("/resume")
def agent0_resume(body: ControlRequest, _=Depends(require_api_key)):
    result = _control("resume", body)
    if not result.get("accepted"):
        raise HTTPException(status_code=403, detail=result.get("refusal_reason"))
    return result


@router.post("/panic")
def agent0_panic(body: ControlRequest, _=Depends(require_api_key)):
    result = _control("panic", body)
    if not result.get("accepted"):
        raise HTTPException(status_code=403, detail=result.get("refusal_reason"))
    return result


@router.post("/request-recovery")
def agent0_request_recovery(body: ControlRequest, _=Depends(require_api_key)):
    result = _control("request-recovery", body)
    if not result.get("accepted"):
        raise HTTPException(status_code=403, detail=result.get("refusal_reason"))
    return result


@router.post("/request-replay")
def agent0_request_replay(body: ControlRequest, _=Depends(require_api_key)):
    result = _control("request-replay", body)
    if not result.get("accepted"):
        raise HTTPException(status_code=403, detail=result.get("refusal_reason"))
    return result


@router.post("/request-proof-gate")
def agent0_request_proof_gate(body: ControlRequest, _=Depends(require_api_key)):
    result = _control("request-proof-gate", body)
    raise HTTPException(status_code=403, detail=result.get("refusal_reason", "refused"))


@router.post("/srp/approve-bundle")
def agent0_srp_approve(body: ControlRequest, _=Depends(require_api_key)):
    if not body.bundle_hash:
        raise HTTPException(status_code=400, detail="bundle_hash_required")
    result = _control("srp-approve-bundle", body)
    raise HTTPException(status_code=403, detail=result.get("refusal_reason", "refused"))


@router.post("/srp/reject-bundle")
def agent0_srp_reject(body: ControlRequest, _=Depends(require_api_key)):
    if not body.bundle_hash:
        raise HTTPException(status_code=400, detail="bundle_hash_required")
    result = _control("srp-reject-bundle", body)
    if not result.get("accepted"):
        raise HTTPException(status_code=403, detail=result.get("refusal_reason"))
    return result


@router.post("/oea/confirm-capability")
def agent0_oea_confirm(body: ControlRequest, _=Depends(require_api_key)):
    if not body.binding_hash:
        raise HTTPException(status_code=400, detail="binding_hash_required")
    result = _control("oea-confirm-capability", body)
    raise HTTPException(status_code=403, detail=result.get("refusal_reason", "refused"))
