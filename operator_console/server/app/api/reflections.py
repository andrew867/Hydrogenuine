from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.reflection_cycle_service import get_reflection_cycle_summary, run_reflection_cycles
from ..services.reflection_artifact_service import (
    discard_reflection_artifact_service,
    escalate_reflection_artifact_service,
    get_reflection_artifact,
    list_reflection_artifacts,
    promote_reflection_artifact_service,
    upsert_reflection_artifact_service,
)

router = APIRouter()


class ReflectionArtifactBody(BaseModel):
    artifact_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    findings_json: Any
    source_event_ids: list[str] = Field(default_factory=list)
    source_memory_ids: list[str] = Field(default_factory=list)
    source_links: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    verification_status: str = "provisional"
    reviewed_by: str | None = None
    promoted_at: str | None = None


class ReflectionCycleRunBody(BaseModel):
    force: bool = False


class ReflectionReviewBody(BaseModel):
    reviewed_by: str | None = None
    note: str | None = None


@router.get("/reflections")
def reflections(_=Depends(require_api_key)):
    return {"ok": True, "artifacts": list_reflection_artifacts()}


@router.get("/reflections/cycles")
def reflection_cycles(_=Depends(require_api_key)):
    from hg_lib.config import get_workspace_root

    return get_reflection_cycle_summary(get_workspace_root())


@router.post("/reflections/cycles/run")
def run_reflection_cycles_route(body: ReflectionCycleRunBody | None = None, _=Depends(require_api_key)):
    from hg_lib.config import get_workspace_root

    payload = body or ReflectionCycleRunBody()
    return run_reflection_cycles(get_workspace_root(), force=payload.force)


@router.post("/reflections/{artifact_id}/promote")
def promote_reflection(artifact_id: str, body: ReflectionReviewBody | None = None, _=Depends(require_api_key)):
    payload = body or ReflectionReviewBody()
    try:
        artifact = promote_reflection_artifact_service(
            artifact_id=artifact_id,
            actor_id="operator",
            reviewed_by=payload.reviewed_by or "operator_console",
            note=payload.note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="reflection artifact not found")
    return {"ok": True, "artifact": artifact}


@router.post("/reflections/{artifact_id}/discard")
def discard_reflection(artifact_id: str, body: ReflectionReviewBody | None = None, _=Depends(require_api_key)):
    payload = body or ReflectionReviewBody()
    try:
        artifact = discard_reflection_artifact_service(
            artifact_id=artifact_id,
            actor_id="operator",
            reviewed_by=payload.reviewed_by or "operator_console",
            note=payload.note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="reflection artifact not found")
    return {"ok": True, "artifact": artifact}


@router.post("/reflections/{artifact_id}/escalate")
def escalate_reflection(artifact_id: str, body: ReflectionReviewBody | None = None, _=Depends(require_api_key)):
    payload = body or ReflectionReviewBody()
    try:
        artifact = escalate_reflection_artifact_service(
            artifact_id=artifact_id,
            actor_id="operator",
            reviewed_by=payload.reviewed_by or "operator_console",
            note=payload.note,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="reflection artifact not found")
    return {"ok": True, "artifact": artifact}


@router.get("/reflections/{artifact_id}")
def reflection(artifact_id: str, _=Depends(require_api_key)):
    artifact = get_reflection_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="reflection artifact not found")
    return {"ok": True, "artifact": artifact}


@router.post("/reflections")
def create_reflection(body: ReflectionArtifactBody, _=Depends(require_api_key)):
    artifact = upsert_reflection_artifact_service(
        artifact_id=body.artifact_id,
        title=body.title,
        summary=body.summary,
        findings_json=body.findings_json,
        source_event_ids=body.source_event_ids,
        source_memory_ids=body.source_memory_ids,
        source_links=body.source_links,
        confidence=body.confidence,
        verification_status=body.verification_status,
        reviewed_by=body.reviewed_by,
        promoted_at=body.promoted_at,
        actor_id="operator",
        change_summary="created reflection artifact via api",
    )
    return {"ok": True, "artifact": artifact}
