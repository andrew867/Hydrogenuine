"""
Pack 12: File upload and download. Tenant-scoped; mime/size allowlist.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from hg_gateway.auth import verify_api_key, get_tenant_context
from hg_core.tenancy.context import TenantContext
from hg_core.docs import get_document_store, get_documents_root, get_exports_root

router = APIRouter(dependencies=[Depends(verify_api_key)])

ALLOWED_MIME_PREFIXES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml",
    "application/vnd.openxmlformats-officedocument.presentationml",
)
ALLOWED_MIME_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
)
DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
FILENAME_MIME_OVERRIDES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _max_upload_bytes() -> int:
    try:
        return int(os.environ.get("HG_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES)).strip())
    except (ValueError, TypeError):
        return DEFAULT_MAX_UPLOAD_BYTES


def _mime_allowed(mime: str) -> bool:
    if not mime:
        return False
    normalized = mime.lower().strip()
    return normalized in ALLOWED_MIME_TYPES or any(normalized.startswith(p) for p in ALLOWED_MIME_PREFIXES)


def _normalize_upload_mime(filename: str, mime: str) -> str:
    normalized = (mime or "").strip().lower()
    if _mime_allowed(normalized):
        return normalized
    suffix = Path(filename or "").suffix.lower()
    override = FILENAME_MIME_OVERRIDES.get(suffix)
    if override:
        return override
    return normalized or "application/octet-stream"


@router.post("/files/upload")
async def upload_file(
    file: UploadFile,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Upload a file; store blob under tenant path and create document row. Returns document_id."""
    tenant_id = tenant_context.tenant_id
    content = await file.read()
    size = len(content)
    if size > _max_upload_bytes():
        raise HTTPException(
            status_code=400,
            detail={"code": "file_too_large", "message": f"File exceeds max size ({_max_upload_bytes()} bytes)"},
        )
    filename = (file.filename or "upload").strip() or "upload"
    mime = _normalize_upload_mime(filename, file.content_type or "")
    if not _mime_allowed(mime):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "mime_not_allowed",
                "message": "File type not allowed",
                "allowed": sorted({*ALLOWED_MIME_TYPES, *ALLOWED_MIME_PREFIXES}),
            },
        )
    sha256 = hashlib.sha256(content).hexdigest()
    store = get_document_store()
    document_id = store.document_create(
        tenant_id=tenant_id,
        filename=filename,
        mime=mime,
        size_bytes=size,
        sha256=sha256,
    )
    blob_path = get_documents_root(tenant_id) / document_id / filename
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob_path.write_bytes(content)
    return {"document_id": document_id, "filename": filename, "mime": mime, "size_bytes": size}


def _resolve_file_to_path(tenant_id: str, file_id: str) -> Optional[tuple]:
    """Resolve file_id (document_id or export file_id) to (Path, filename). Returns None if not found or wrong tenant. Path is always under tenant documents or exports root."""
    store = get_document_store()
    doc = store.document_get(tenant_id, file_id)
    if doc:
        root = get_documents_root(tenant_id) / file_id / doc.filename
        if root.exists():
            return (root, doc.filename)
        return None
    export_root = get_exports_root(tenant_id)
    if export_root.exists():
        for p in export_root.iterdir():
            if p.is_file() and (p.stem == file_id or p.name == file_id):
                return (p, p.name)
    return None


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
):
    """Download a file by document_id or export file_id. Tenant-scoped; 404 if wrong tenant or missing."""
    tenant_id = tenant_context.tenant_id
    resolved = _resolve_file_to_path(tenant_id, file_id)
    if not resolved:
        raise HTTPException(status_code=404, detail="file not found")
    path, filename = resolved
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=filename,
    )
