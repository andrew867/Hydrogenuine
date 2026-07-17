"""Append-only consent ledger (G15 / CS-5)."""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_CONSENT_CLASSES = frozenset({"none", "session", "workspace", "research"})
SESSION_CLASSES = frozenset({"session"})


def _default_ledger_path() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root()) / "memory" / "governance" / "consent_ledger.jsonl"
    except Exception:
        return Path("memory/governance/consent_ledger.jsonl")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class ConsentLedger:
    """Append-only JSONL consent event log."""

    path: Path = None  # type: ignore[assignment]
    _lock: threading.Lock = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.path is None:
            self.path = _default_ledger_path()
        if self._lock is None:
            self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, row: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def grant(
        self,
        *,
        subject_id: str,
        consent_class: str,
        purpose: str,
        granted_by: str,
        expires_at: Optional[str] = None,
        proof_bundle_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        cls = str(consent_class).strip().lower()
        if cls not in VALID_CONSENT_CLASSES - {"none"}:
            raise ValueError(f"invalid consent_class: {consent_class}")
        if cls in SESSION_CLASSES and not expires_at:
            raise ValueError("session consent requires expires_at")
        record_id = f"cg_{uuid.uuid4().hex[:10]}"
        row = {
            "event": "CONSENT_GRANTED",
            "record_id": record_id,
            "subject_id": subject_id,
            "consent_class": cls,
            "purpose": purpose,
            "granted_at": _iso_now(),
            "expires_at": expires_at,
            "granted_by": granted_by,
            "revoked_at": None,
            "proof_bundle_ref": proof_bundle_ref,
            "ts": time.time(),
        }
        return self._append(row)

    def revoke(self, *, record_id: str, subject_id: str, revoked_by: str) -> Dict[str, Any]:
        row = {
            "event": "CONSENT_REVOKED",
            "record_id": record_id,
            "subject_id": subject_id,
            "revoked_at": _iso_now(),
            "revoked_by": revoked_by,
            "ts": time.time(),
        }
        return self._append(row)

    def expire(self, *, record_id: str, subject_id: str, consent_class: str) -> Dict[str, Any]:
        row = {
            "event": "CONSENT_EXPIRED",
            "record_id": record_id,
            "subject_id": subject_id,
            "consent_class": consent_class,
            "expired_at": _iso_now(),
            "ts": time.time(),
        }
        return self._append(row)

    def deny_request(self, *, subject_id: str, reason: str, source: str = "enforcement") -> Dict[str, Any]:
        row = {
            "event": "CONSENT_DENIED_REQUEST",
            "subject_id": subject_id,
            "reason": reason,
            "source": source,
            "ts": time.time(),
            "denied_at": _iso_now(),
        }
        return self._append(row)

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def tail(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.read_all()
        return rows[-limit:] if limit > 0 else rows
