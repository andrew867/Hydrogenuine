"""
Pack 12: Parse job runner. Reads blob, runs parser + chunker, persists chunks; updates job and document; emits events.
Phase 4 will add real PDF/DOCX parsers and chunking; until then we just mark job completed and set parse_status.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from hg_core.docs import get_document_store, get_documents_root
from hg_core.docs.models import PARSE_STATUS_PARSED, PARSE_STATUS_FAILED, JOB_STATUS_RUNNING, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED


async def run_parse_job(tenant_id: str, document_id: str, job_id: str) -> None:
    """Run parse job: load document, parse (PDF/DOCX), chunk, persist chunks; update job and parse_status; emit events."""
    store = get_document_store()
    doc = store.document_get(tenant_id, document_id)
    if not doc:
        return
    store.job_update(tenant_id, job_id, JOB_STATUS_RUNNING, started_at=_now())
    try:
        blob_path = get_documents_root(tenant_id) / document_id / doc.filename
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {blob_path}")
        try:
            from hg_core.docs.parsers import parse_document_to_chunks
            parse_document_to_chunks(store, tenant_id, document_id, blob_path, doc.mime)
        except ImportError:
            pass
        store.document_update_parse_status(tenant_id, document_id, PARSE_STATUS_PARSED)
        store.job_update(tenant_id, job_id, JOB_STATUS_COMPLETED, ended_at=_now())
        _emit(document_id, "document.job.completed", {"job_id": job_id, "document_id": document_id})
        _emit(document_id, "document.parsed", {"document_id": document_id})
    except Exception as e:
        store.document_update_parse_status(tenant_id, document_id, PARSE_STATUS_FAILED)
        store.job_update(tenant_id, job_id, JOB_STATUS_FAILED, ended_at=_now(), error=str(e))
        _emit(document_id, "document.job.failed", {"job_id": job_id, "document_id": document_id, "error": str(e)})


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _emit(document_id: str, event: str, payload: dict) -> None:
    try:
        from hg_gateway import sse_hub
        sse_hub.emit(document_id, event, payload)
    except Exception:
        pass
