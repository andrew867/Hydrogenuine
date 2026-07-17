from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.executable_registry_service import (
    get_executable_registry_overview,
    get_executable_registry_record,
    get_executable_registry_record_versions,
    sync_executable_registry_service,
)

router = APIRouter()


class ExecutableSyncBody(BaseModel):
    root: str | None = None


@router.get("/registry")
def executable_registry(_=Depends(require_api_key)):
    return {"ok": True, **get_executable_registry_overview()}


@router.get("/registry/{tool_id:path}/versions")
def executable_registry_versions(tool_id: str, _=Depends(require_api_key)):
    return {"ok": True, "tool_id": tool_id, "versions": get_executable_registry_record_versions(tool_id)}


@router.get("/registry/{tool_id:path}")
def executable_registry_record(tool_id: str, _=Depends(require_api_key)):
    record = get_executable_registry_record(tool_id)
    if record is None:
        raise HTTPException(status_code=404, detail="executable record not found")
    return {"ok": True, "executable": record}


@router.post("/registry/sync")
def executable_registry_sync(body: ExecutableSyncBody, _=Depends(require_api_key)):
    sync_summary = sync_executable_registry_service(root=body.root)
    overview = get_executable_registry_overview()
    return {"ok": True, "sync": sync_summary, **overview}
