"""Retention API: redaction preview, purge execution, and purge audit listing."""

from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import require_api_key

router = APIRouter()

AUDIT_DIR = "memory/automation/audit"
PURGE_AUDIT_FILE = "purge_audit.jsonl"


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return Path(".")


@router.post("/redact-preview")
def redact_preview(body: dict = Body(...), _=Depends(require_api_key)):
    """Preview redaction of a payload (no secrets in stored artifacts)."""
    try:
        from hg_core.task_graph.retention_redaction_purge import redact_for_storage
        redacted = redact_for_storage(body)
        return {"ok": True, "redacted": redacted}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


class PurgeBody(BaseModel):
    run_id: str


@router.post("/purge")
def purge_by_run_id(body: PurgeBody, _=Depends(require_api_key)):
    """Purge artifacts by run_id; write audit log."""
    try:
        from hg_core.task_graph.retention_redaction_purge import purge_by_run_id as _purge
        root = _workspace_root()
        removed, audit_entry = _purge(root, body.run_id)
        return {"ok": True, "removed_count": len(removed), "audit_entry": audit_entry}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/audit")
def list_audit(limit: int = 50, _=Depends(require_api_key)):
    """List recent purge audit entries."""
    import json
    root = _workspace_root()
    audit_path = root / AUDIT_DIR / PURGE_AUDIT_FILE
    entries = []
    if audit_path.exists():
        try:
            lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-limit:]) if len(lines) > limit else reversed(lines):
                if line.strip():
                    entries.append(json.loads(line))
        except Exception:
            pass
    return {"ok": True, "entries": entries}
