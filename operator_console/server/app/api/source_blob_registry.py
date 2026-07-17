from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.source_blob_registry_service import (
    archive_source_blob_registry_record,
    compare_source_blob_registry_versions,
    create_source_blob_registry_record,
    get_source_blob_registry_overview,
    get_source_blob_registry_record,
    get_source_blob_registry_record_versions,
    restore_source_blob_registry_record,
    run_source_blob_registry_record,
    save_source_blob_registry_record,
    sync_source_blob_registry_service,
)

router = APIRouter()


class SourceBlobSyncBody(BaseModel):
    root: str | None = None


class SourceBlobCreateBody(BaseModel):
    class_key: str
    file_path: str
    source_text: str
    title: str | None = None
    actor_id: str | None = None
    change_summary: str | None = None


class SourceBlobSaveBody(BaseModel):
    source_text: str
    title: str | None = None
    actor_id: str | None = None
    change_summary: str | None = None


class SourceBlobActionBody(BaseModel):
    actor_id: str | None = None
    change_summary: str | None = None


class SourceBlobRunBody(BaseModel):
    entrypoint: str | None = None
    args: list[str] | None = None
    timeout_s: int | None = 120
    actor_id: str | None = None
    change_summary: str | None = None


@router.get("/registry")
def source_blob_registry(_=Depends(require_api_key)):
    return {"ok": True, **get_source_blob_registry_overview()}


@router.get("/registry/{source_blob_id:path}/versions")
def source_blob_registry_versions(source_blob_id: str, _=Depends(require_api_key)):
    return {"ok": True, "source_blob_id": source_blob_id, "versions": get_source_blob_registry_record_versions(source_blob_id)}


@router.get("/registry/{source_blob_id:path}/diff")
def source_blob_registry_diff(
    source_blob_id: str,
    left_version_id: str | None = None,
    right_version_id: str | None = None,
    _=Depends(require_api_key),
):
    diff = compare_source_blob_registry_versions(source_blob_id, left_version_id, right_version_id)
    if diff is None:
        raise HTTPException(status_code=404, detail="source blob diff not available")
    return {"ok": True, "diff": diff}


@router.get("/registry/{source_blob_id:path}")
def source_blob_registry_record(source_blob_id: str, _=Depends(require_api_key)):
    record = get_source_blob_registry_record(source_blob_id)
    if record is None:
        raise HTTPException(status_code=404, detail="source blob record not found")
    return {"ok": True, "source_blob": record}


@router.post("/registry/sync")
def source_blob_registry_sync(body: SourceBlobSyncBody, _=Depends(require_api_key)):
    sync_summary = sync_source_blob_registry_service(root=body.root)
    overview = get_source_blob_registry_overview()
    return {"ok": True, "sync": sync_summary, **overview}


@router.post("/registry")
def source_blob_registry_create(body: SourceBlobCreateBody, _=Depends(require_api_key)):
    try:
        return {
            "ok": True,
            "source_blob": create_source_blob_registry_record(
                body.class_key,
                body.file_path,
                body.source_text,
                title=body.title,
                actor_id=body.actor_id,
                change_summary=body.change_summary,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/registry/{source_blob_id:path}")
def source_blob_registry_save(source_blob_id: str, body: SourceBlobSaveBody, _=Depends(require_api_key)):
    try:
        return {
            "ok": True,
            "source_blob": save_source_blob_registry_record(
                source_blob_id,
                body.source_text,
                title=body.title,
                actor_id=body.actor_id,
                change_summary=body.change_summary,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/registry/{source_blob_id:path}/archive")
def source_blob_registry_archive(source_blob_id: str, body: SourceBlobActionBody, _=Depends(require_api_key)):
    try:
        return {
            "ok": True,
            "source_blob": archive_source_blob_registry_record(
                source_blob_id,
                actor_id=body.actor_id,
                change_summary=body.change_summary,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/registry/{source_blob_id:path}/restore")
def source_blob_registry_restore(source_blob_id: str, body: SourceBlobActionBody, _=Depends(require_api_key)):
    try:
        return {
            "ok": True,
            "source_blob": restore_source_blob_registry_record(
                source_blob_id,
                actor_id=body.actor_id,
                change_summary=body.change_summary,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/registry/{source_blob_id:path}/run")
def source_blob_registry_run(source_blob_id: str, body: SourceBlobRunBody, _=Depends(require_api_key)):
    try:
        return {
            "ok": True,
            **run_source_blob_registry_record(
                source_blob_id,
                entrypoint=body.entrypoint,
                args=body.args or [],
                timeout_s=body.timeout_s or 120,
                actor_id=body.actor_id,
                change_summary=body.change_summary,
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
