from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..core.auth import require_api_key
from ..services.content_registry_service import (
    archive_content_registry_document,
    create_content_registry_document,
    get_content_registry_document,
    get_content_registry_overview,
    get_content_registry_versions,
    restore_content_registry_document,
    save_content_registry_document,
    sync_content_registry,
)
from hg_gateway.content_cms import CONTENT_CLASS_DEFINITIONS
from dataclasses import asdict

router = APIRouter()


class ContentSaveBody(BaseModel):
    content_markdown: str
    title: str | None = None
    actor_id: str | None = None
    change_summary: str | None = None


class ContentCreateBody(BaseModel):
    class_key: str
    file_path: str
    content_markdown: str
    title: str | None = None
    actor_id: str | None = None
    change_summary: str | None = None


class ContentSyncBody(BaseModel):
    root: str | None = None


class ContentActionBody(BaseModel):
    actor_id: str | None = None
    change_summary: str | None = None


@router.get("/registry")
def content_registry(_=Depends(require_api_key)):
    return {"ok": True, **get_content_registry_overview()}


@router.get("/registry/classes")
def content_registry_classes(_=Depends(require_api_key)):
    return {"ok": True, "classes": [asdict(cls) for cls in CONTENT_CLASS_DEFINITIONS]}


@router.get("/registry/{content_id:path}")
def content_registry_document(content_id: str, _=Depends(require_api_key)):
    doc = get_content_registry_document(content_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="content document not found")
    return {"ok": True, "document": doc}


@router.get("/registry/{content_id:path}/versions")
def content_registry_versions(content_id: str, _=Depends(require_api_key)):
    return {"ok": True, "content_id": content_id, "versions": get_content_registry_versions(content_id)}


@router.post("/registry/sync")
def content_registry_sync(body: ContentSyncBody, _=Depends(require_api_key)):
    sync_summary = sync_content_registry(root=body.root)
    overview = get_content_registry_overview()
    return {"ok": True, "sync": sync_summary, **overview}


@router.post("/registry")
def content_registry_create(body: ContentCreateBody, _=Depends(require_api_key)):
    try:
        return {"ok": True, "document": create_content_registry_document(
            body.class_key,
            body.file_path,
            body.content_markdown,
            title=body.title,
            actor_id=body.actor_id,
            change_summary=body.change_summary,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/registry/{content_id:path}")
def content_registry_save(content_id: str, body: ContentSaveBody, _=Depends(require_api_key)):
    try:
        return {"ok": True, "document": save_content_registry_document(
            content_id,
            body.content_markdown,
            title=body.title,
            actor_id=body.actor_id,
            change_summary=body.change_summary,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/registry/{content_id:path}/archive")
def content_registry_archive(content_id: str, body: ContentActionBody, _=Depends(require_api_key)):
    try:
        return {"ok": True, "document": archive_content_registry_document(
            content_id,
            actor_id=body.actor_id,
            change_summary=body.change_summary,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/registry/{content_id:path}/restore")
def content_registry_restore(content_id: str, body: ContentActionBody, _=Depends(require_api_key)):
    try:
        return {"ok": True, "document": restore_content_registry_document(
            content_id,
            actor_id=body.actor_id,
            change_summary=body.change_summary,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
