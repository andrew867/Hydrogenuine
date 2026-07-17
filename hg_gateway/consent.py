"""Recognition consent dependencies for HG Gateway (G15)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException, Query

from hg_core.consent import resolve_consent_class
from hg_core.consent.ledger import ConsentLedger


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _ledger() -> ConsentLedger:
    return ConsentLedger(path=_workspace_root() / "memory" / "governance" / "consent_ledger.jsonl")


def require_recognition_consent(
    subject_id: str = Query(..., description="Subject whose consent is required"),
    min_class: str = Query("session", description="Minimum consent class"),
    x_subject_id: Optional[str] = Header(default=None, alias="X-Subject-ID"),
) -> str:
    """Fail-closed recognition consent guard for gateway routes flagged user_recognition=True."""
    sid = (x_subject_id or subject_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="subject_id_required")
    effective = resolve_consent_class(sid, workspace_root=_workspace_root())
    rank = {"none": 0, "session": 1, "workspace": 2, "research": 3}
    need = rank.get(str(min_class).lower(), 1)
    have = rank.get(effective, 0)
    if have < need:
        _ledger().deny_request(subject_id=sid, reason="consent_required", source="gateway")
        raise HTTPException(status_code=403, detail="consent_required")
    return effective
