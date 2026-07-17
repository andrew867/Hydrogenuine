from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.task_registry_service import (
    get_task_registry_overview,
    get_task_registry_record,
    get_task_registry_record_versions,
    save_task_registry_record,
    sync_task_registry_service,
)

router = APIRouter()


class TaskSyncBody(BaseModel):
    root: str | None = None


class TaskSaveBody(BaseModel):
    metadata: dict[str, Any] | None = None
    disabled: bool | None = None
    archived: bool | None = None
    source_path: str | None = None
    mode: str | None = None
    model: str | None = None
    sandbox_mode: str | None = None
    sandbox_allowlist: list[str] | None = None


@router.get("/registry")
def task_registry(_=Depends(require_api_key)):
    return {"ok": True, **get_task_registry_overview()}


@router.get("/registry/{task_name:path}/versions")
def task_registry_versions(task_name: str, _=Depends(require_api_key)):
    return {"ok": True, "task_name": task_name, "versions": get_task_registry_record_versions(task_name)}


@router.get("/registry/{task_name:path}")
def task_registry_record(task_name: str, _=Depends(require_api_key)):
    record = get_task_registry_record(task_name)
    if record is None:
        raise HTTPException(status_code=404, detail="task record not found")
    return {"ok": True, "task": record}


@router.post("/registry/sync")
def task_registry_sync(body: TaskSyncBody, _=Depends(require_api_key)):
    sync_summary = sync_task_registry_service(root=body.root)
    overview = get_task_registry_overview()
    return {"ok": True, "sync": sync_summary, **overview}


@router.put("/registry/{task_name:path}")
def task_registry_save(task_name: str, body: TaskSaveBody, _=Depends(require_api_key)):
    record = save_task_registry_record(
        task_name,
        metadata=body.metadata,
        disabled=body.disabled,
        archived=body.archived,
        source_path=body.source_path,
        mode=body.mode,
        model=body.model,
        sandbox_mode=body.sandbox_mode,
        sandbox_allowlist=body.sandbox_allowlist,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="task record not found")
    return {"ok": True, "task": record}
