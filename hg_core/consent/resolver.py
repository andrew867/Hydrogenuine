"""Effective consent class resolution (G15 / CS-1 fail-closed)."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .errors import ConsentDeniedError
from .ledger import VALID_CONSENT_CLASSES, ConsentLedger

CLASS_RANK = {"none": 0, "session": 1, "workspace": 2, "research": 3}


def is_consent_surface_enabled() -> bool:
    return os.environ.get("HG_CONSENT_SURFACE_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _parse_iso(ts: Optional[str]) -> Optional[float]:
    if not ts:
        return None
    try:
        normalized = str(ts).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except Exception:
        return None


def _ledger_for(workspace_root: Optional[Path]) -> ConsentLedger:
    if workspace_root is not None:
        return ConsentLedger(path=Path(workspace_root) / "memory" / "governance" / "consent_ledger.jsonl")
    return ConsentLedger()


def resolve_consent_class(subject_id: str, *, workspace_root: Optional[Path] = None) -> str:
    """Return effective consent class for subject; fail-closed to 'none' on any error (CS-1)."""
    try:
        ledger = _ledger_for(workspace_root)
        now = time.time()
        revoked_ids: set[str] = set()
        expired_ids: set[str] = set()
        active_by_class: dict[str, str] = {}

        for row in ledger.read_all():
            event = str(row.get("event") or "")
            if event == "CONSENT_REVOKED":
                revoked_ids.add(str(row.get("record_id") or ""))
            elif event == "CONSENT_EXPIRED":
                expired_ids.add(str(row.get("record_id") or ""))

        for row in ledger.read_all():
            if str(row.get("event") or "") != "CONSENT_GRANTED":
                continue
            record_id = str(row.get("record_id") or "")
            if record_id in revoked_ids or record_id in expired_ids:
                continue
            if str(row.get("subject_id") or "") != subject_id:
                continue
            cls = str(row.get("consent_class") or "none").lower()
            if cls not in VALID_CONSENT_CLASSES:
                continue
            expires_at = _parse_iso(row.get("expires_at"))
            if expires_at is not None and now >= expires_at:
                ledger.expire(record_id=record_id, subject_id=subject_id, consent_class=cls)
                expired_ids.add(record_id)
                continue
            active_by_class[cls] = record_id

        if not active_by_class:
            return "none"
        return max(active_by_class.keys(), key=lambda c: CLASS_RANK.get(c, 0))
    except Exception:
        return "none"


def assert_recognition_consent(
    subject_id: str,
    *,
    min_class: str = "session",
    workspace_root: Optional[Path] = None,
    source: str = "enforcement",
) -> str:
    """Raise ConsentDeniedError and log denial when consent is insufficient (CS-3)."""
    effective = resolve_consent_class(subject_id, workspace_root=workspace_root)
    need = CLASS_RANK.get(str(min_class).lower(), 1)
    have = CLASS_RANK.get(effective, 0)
    if have < need:
        ledger = _ledger_for(workspace_root)
        ledger.deny_request(subject_id=subject_id, reason="consent_required", source=source)
        raise ConsentDeniedError(subject_id, reason="consent_required")
    return effective
