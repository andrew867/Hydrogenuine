"""Consent surface operator service (G15)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.consent import is_consent_surface_enabled, resolve_consent_class
from hg_core.consent.ledger import ConsentLedger


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _ledger() -> ConsentLedger:
    return ConsentLedger(path=_workspace_root() / "memory" / "governance" / "consent_ledger.jsonl")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _recognition_active(effective_class: str) -> bool:
    if not is_consent_surface_enabled() or effective_class == "none":
        return False
    try:
        from hg_core.repr_interp.user_recognition import is_user_recognition_enabled

        return is_user_recognition_enabled()
    except Exception:
        return False


def _active_grants(subject_id: str) -> List[Dict[str, Any]]:
    ledger = _ledger()
    revoked: set[str] = set()
    expired: set[str] = set()
    for row in ledger.read_all():
        event = str(row.get("event") or "")
        if event == "CONSENT_REVOKED":
            revoked.add(str(row.get("record_id") or ""))
        elif event == "CONSENT_EXPIRED":
            expired.add(str(row.get("record_id") or ""))
    active: List[Dict[str, Any]] = []
    for row in ledger.read_all():
        if str(row.get("event") or "") != "CONSENT_GRANTED":
            continue
        if str(row.get("subject_id") or "") != subject_id:
            continue
        record_id = str(row.get("record_id") or "")
        if record_id in revoked or record_id in expired:
            continue
        active.append(dict(row))
    return active


def get_consent_status(subject_id: str) -> Dict[str, Any]:
    effective = resolve_consent_class(subject_id, workspace_root=_workspace_root())
    return {
        "ok": True,
        "subject_id": subject_id,
        "effective_class": effective,
        "active_grants": _active_grants(subject_id),
        "surface_enabled": is_consent_surface_enabled(),
        "recognition_active": _recognition_active(effective),
        "generated_at": _iso_now(),
    }


def grant_consent(
    *,
    subject_id: str,
    consent_class: str,
    purpose: str,
    granted_by: str,
    expires_at: Optional[str] = None,
    proof_bundle_ref: Optional[str] = None,
) -> Dict[str, Any]:
    record = _ledger().grant(
        subject_id=subject_id,
        consent_class=consent_class,
        purpose=purpose,
        granted_by=granted_by,
        expires_at=expires_at,
        proof_bundle_ref=proof_bundle_ref,
    )
    return {"ok": True, "record": record, "status": get_consent_status(subject_id)}


def revoke_consent(*, record_id: str, subject_id: str, revoked_by: str) -> Dict[str, Any]:
    record = _ledger().revoke(record_id=record_id, subject_id=subject_id, revoked_by=revoked_by)
    return {"ok": True, "revocation": record, "status": get_consent_status(subject_id)}


def get_ledger_page(*, offset: int = 0, limit: int = 50) -> Dict[str, Any]:
    rows = _ledger().read_all()
    page = rows[offset : offset + limit] if limit > 0 else rows[offset:]
    return {
        "ok": True,
        "offset": offset,
        "limit": limit,
        "total": len(rows),
        "events": page,
        "generated_at": _iso_now(),
    }


def seed_demo_grants() -> Dict[str, Any]:
    """Seed demo grants from eval fixtures when present."""
    fixtures = _workspace_root() / "evals" / "g15" / "consent_surface" / "fixtures.json"
    if not fixtures.exists():
        return {"ok": False, "error": "fixtures_missing"}
    import json

    data = json.loads(fixtures.read_text(encoding="utf-8"))
    seeded: List[Dict[str, Any]] = []
    for grant in data.get("seed_grants") or []:
        seeded.append(
            grant_consent(
                subject_id=str(grant["subject_id"]),
                consent_class=str(grant["consent_class"]),
                purpose=str(grant.get("purpose") or "demo"),
                granted_by=str(grant.get("granted_by") or "operator"),
                expires_at=grant.get("expires_at"),
            )["record"]
        )
    return {"ok": True, "seeded": len(seeded), "records": seeded}
