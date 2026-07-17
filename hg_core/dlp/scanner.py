"""
DLP scanner: scan artifacts, emit DLP_SCAN_COMPLETED; quarantine/release; legal holds; key rotation event.
Production-grade PII detection: SSN, email, phone, address snippets, credit-card-like sequences.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


ScanResult = Literal["pass", "warn", "fail"]

# Compiled PII patterns
_RE_SSN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_RE_PHONE_US = re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_RE_E164 = re.compile(r"\+\d{10,15}\b")
# Address: 5+ digit ZIP (US) or "street"/"st"/"ave"/"blvd" + digits
_RE_ZIP = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_RE_STREET = re.compile(r"\b\d+\s+(?:north|south|east|west|n|s|e|w\.?)?\s*(?:street|st\.?|avenue|ave\.?|blvd\.?|road|rd\.?|drive|dr\.?|lane|ln\.?)\b", re.I)
# Credit card: 4 groups of 4 digits, optional space/dash (Luhn not required for detection)
_RE_CC = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")

# Allowlist: patterns that look like PII but are test/example (don't fail)
_EMAIL_ALLOWLIST = frozenset({"example.com", "test.com", "user@example.com", "sample@test.com"})
_PHONE_ALLOWLIST = frozenset({"555-0100", "555-0199", "5550100", "+15550100"})


def _luhn_checksum(digits: str) -> bool:
    """Return True if digits pass Luhn check (for CC validation). From right, double every second digit."""
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _simple_scan_content(path: Path) -> ScanResult:
    """
    Production-grade content scan for PII. Returns pass/warn/fail.
    Fail: SSN, email (non-allowlist), phone (non-allowlist), credit-card (Luhn if 16 digits).
    Warn: confidential/internal only, address snippets, or any exception (safe default).
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = raw.lower()
        categories: List[str] = []
        redacted: List[str] = []

        # SSN
        if _RE_SSN.search(raw):
            categories.append("ssn")
            redacted.append("ssn")

        # Email (skip allowlist)
        for m in _RE_EMAIL.finditer(raw):
            addr = m.group(0).lower()
            if not any(allow in addr for allow in _EMAIL_ALLOWLIST):
                categories.append("email")
                redacted.append("email")
                break

        # Phone (skip 555 test numbers)
        for m in _RE_PHONE_US.finditer(raw):
            num = re.sub(r"\D", "", m.group(0))
            if num.endswith("5550100") or num.endswith("5550199") or m.group(0) in _PHONE_ALLOWLIST:
                continue
            if len(num) >= 10:
                categories.append("phone")
                redacted.append("phone")
                break
        if not any(c == "phone" for c in categories):
            for m in _RE_E164.finditer(raw):
                num = m.group(0).replace("+", "")
                if num not in ("15550100", "15550199") and len(num) >= 10:
                    categories.append("phone")
                    redacted.append("phone")
                    break

        # Credit card (strict: 16 digits, Luhn)
        for m in _RE_CC.finditer(raw):
            digits = re.sub(r"\D", "", m.group(0))
            if len(digits) == 16 and _luhn_checksum(digits):
                categories.append("credit_card")
                redacted.append("credit_card")
                break

        if categories:
            return "fail"

        # Warn: address-like or confidential
        if _RE_ZIP.search(raw) and _RE_STREET.search(raw):
            return "warn"
        if "confidential" in text or "internal only" in text:
            return "warn"

        return "pass"
    except Exception:
        return "warn"


def run_dlp_scan(
    *,
    artifact_path: Path,
    artifact_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    details_artifact_id: Optional[str] = None,
) -> tuple[ScanResult, str]:
    """
    Run DLP scan on artifact, write details to artifacts/dlp/scans/, emit DLP_SCAN_COMPLETED.
    Returns (result, event_id). result is pass | warn | fail.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    scan_id = "dlp_" + hashlib.sha256(f"{artifact_id}:{ts}".encode()).hexdigest()[:16]
    result = _simple_scan_content(artifact_path)
    root = workspace_root / "artifacts" / "dlp" / "scans"
    root.mkdir(parents=True, exist_ok=True)
    details_path = root / f"{scan_id}.json"
    details_path.write_text(
        json.dumps({"scan_id": scan_id, "artifact_id": artifact_id, "result": result, "ts": ts, "path": str(artifact_path)}, indent=2),
        encoding="utf-8",
    )
    payload = {"scan_id": scan_id, "artifact_id": artifact_id, "result": result, "ts": ts, "details_artifact_id": str(details_path)}
    event_id = emit("DLP_SCAN_COMPLETED", "dlp_scan", scan_id, payload, scope=scope, actor=actor, workspace_root=workspace_root)
    return result, event_id


def quarantine_artifact(
    *,
    artifact_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit DATA_QUARANTINED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "DATA_QUARANTINED",
        "quarantine",
        artifact_id,
        {"artifact_id": artifact_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def release_from_quarantine(
    *,
    artifact_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit DATA_RELEASED (release from quarantine). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "DATA_RELEASED",
        "quarantine",
        artifact_id,
        {"artifact_id": artifact_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def apply_legal_hold(
    *,
    artifact_ref: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    hold_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LEGAL_HOLD_APPLIED. Legal holds prevent retention deletion. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    hid = hold_id or "hold_" + hashlib.sha256(f"{artifact_ref}:{ts}".encode()).hexdigest()[:16]
    return emit(
        "LEGAL_HOLD_APPLIED",
        "legal_hold",
        hid,
        {"hold_id": hid, "artifact_ref": artifact_ref, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def release_legal_hold(
    *,
    hold_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    reason: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit LEGAL_HOLD_RELEASED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "LEGAL_HOLD_RELEASED",
        "legal_hold",
        hold_id,
        {"hold_id": hold_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_key_rotated(
    *,
    key_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    tenant_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit KEY_ROTATED for key rotation audit. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "KEY_ROTATED",
        "key_rotation",
        key_id,
        {"key_id": key_id, "tenant_id": tenant_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
