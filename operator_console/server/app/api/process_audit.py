"""
Layer 9 Phase 2: Process audit API — GET/POST process audit for decision_id or run_id.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from ..core.auth import require_api_key
from ..services.process_audit_service import get_process_audit as get_audit, run_process_audit as run_audit

router = APIRouter()


@router.get("/process-audit")
def process_audit_get(
    decision_id: str | None = Query(None),
    run_id: str | None = Query(None),
    _=Depends(require_api_key),
):
    """GET process audit: pass decision_id or run_id. Returns ProcessAuditResult or list for run_id, or 404."""
    if not decision_id and not run_id:
        return {"ok": False, "error": "decision_id or run_id required"}
    out = get_audit(decision_id=decision_id, run_id=run_id)
    if not out.get("ok") and out.get("error") == "not_found":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=out)
    return out


class RunProcessAuditBody(BaseModel):
    decision_id: str
    run_id: str | None = None
    emit_ledger: bool = True


@router.post("/process-audit")
def process_audit_post(
    body: RunProcessAuditBody,
    _=Depends(require_api_key),
):
    """POST run process audit for decision_id. Returns ProcessAuditResult."""
    return run_audit(decision_id=body.decision_id, run_id=body.run_id, emit_ledger=body.emit_ledger)
