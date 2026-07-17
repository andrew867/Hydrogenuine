from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.artifact_registry_service import (
    get_artifact_registry_overview,
    get_artifact_registry_record,
    get_artifact_registry_record_versions,
    sync_artifact_registry_service,
)
from hg_gateway.artifact_registry import ARTIFACT_CLASS_DEFINITIONS

router = APIRouter()


class ArtifactSyncBody(BaseModel):
    root: str | None = None


@router.get("/registry")
def artifact_registry(_=Depends(require_api_key)):
    return {"ok": True, **get_artifact_registry_overview()}


@router.get("/registry/classes")
def artifact_registry_classes(_=Depends(require_api_key)):
    return {"ok": True, "classes": [asdict(cls) for cls in ARTIFACT_CLASS_DEFINITIONS]}


@router.get("/registry/{artifact_id:path}/versions")
def artifact_registry_versions(artifact_id: str, _=Depends(require_api_key)):
    return {"ok": True, "artifact_id": artifact_id, "versions": get_artifact_registry_record_versions(artifact_id)}


@router.get("/registry/{artifact_id:path}")
def artifact_registry_record(artifact_id: str, _=Depends(require_api_key)):
    record = get_artifact_registry_record(artifact_id)
    if record is None:
        raise HTTPException(status_code=404, detail="artifact record not found")
    return {"ok": True, "artifact": record}


@router.post("/registry/sync")
def artifact_registry_sync(body: ArtifactSyncBody, _=Depends(require_api_key)):
    sync_summary = sync_artifact_registry_service(root=body.root)
    overview = get_artifact_registry_overview()
    return {"ok": True, "sync": sync_summary, **overview}
