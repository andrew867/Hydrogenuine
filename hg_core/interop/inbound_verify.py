"""
Interop Pack 3: Inbound approval receipt verification — signature, scope, expiry, anti-replay, independence.
Emits APPROVAL_GRANTED / APPROVAL_DENIED on success, EXTERNAL_APPROVAL_REJECTED on failure.
"""
from __future__ import annotations

import hmac as hm
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from hg_core.ledger import emit
from hg_core.interop.approval_bridge import load_approval_request


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_bridge_config(workspace_root: Path, bridge_id: str) -> Optional[Dict[str, Any]]:
    path = workspace_root / "artifacts" / "bridges" / f"{bridge_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sign_receipt(
    receipt: Dict[str, Any],
    bridge_id: str,
    workspace_root: Path,
) -> Dict[str, Any]:
    """Sign a receipt using bridge trust root. Returns receipt with signature set (copy)."""
    config = _load_bridge_config(workspace_root, bridge_id)
    if not config:
        return {**receipt, "signature": ""}
    secret = config.get("hmac_secret") or config.get("signing_key")
    if isinstance(secret, dict):
        secret = secret.get("k") or secret.get("key") or ""
    if not secret:
        return {**receipt, "signature": ""}
    payload = _signature_payload(receipt)
    sig = hm.new(secret.encode() if isinstance(secret, str) else secret, payload.encode(), hashlib.sha256).hexdigest()
    return {**receipt, "signature": sig, "bridge_id": bridge_id}


def _signature_payload(receipt: Dict[str, Any]) -> str:
    return "|".join([
        receipt.get("receipt_id", ""),
        receipt.get("request_id", ""),
        receipt.get("decision", ""),
        receipt.get("ts", ""),
        receipt.get("nonce", ""),
    ])


def _verify_signature(receipt: Dict[str, Any], bridge_config: Dict[str, Any], workspace_root: Path) -> bool:
    """Verify receipt signature using bridge trust root (hmac_secret)."""
    secret = bridge_config.get("hmac_secret") or bridge_config.get("signing_key")
    if not secret:
        return False
    if isinstance(secret, dict):
        secret = secret.get("k") or secret.get("key") or ""
    payload = _signature_payload(receipt)
    expected = hm.new(secret.encode() if isinstance(secret, str) else secret, payload.encode(), hashlib.sha256).hexdigest()
    sig = receipt.get("signature")
    if isinstance(sig, dict):
        sig = sig.get("hmac") or sig.get("value") or ""
    return hm.compare_digest(expected, sig or "")


def _seen_receipts_path(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "bridges" / "_seen_receipts.jsonl"


def _is_replay(workspace_root: Path, receipt_id: str, nonce: str) -> bool:
    """Return True if (receipt_id, nonce) already seen (replay)."""
    path = _seen_receipts_path(workspace_root)
    if not path.is_file():
        return False
    key = f"{receipt_id}:{nonce}"
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("receipt_id") == receipt_id or rec.get("nonce") == nonce:
                    return True
            except Exception:
                continue
    return False


def _record_receipt_seen(workspace_root: Path, receipt_id: str, nonce: str) -> None:
    path = _seen_receipts_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"receipt_id": receipt_id, "nonce": nonce}) + "\n")


def verify_and_apply_receipt(
    *,
    receipt: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    now_ts: Optional[str] = None,
    disallowed_approver_ids: Optional[Set[str]] = None,
) -> tuple:
    """
    Verify inbound approval receipt and emit APPROVAL_GRANTED or APPROVAL_DENIED, or EXTERNAL_APPROVAL_REJECTED.
    Returns (accepted: bool, event_id: str, rejection_reason: Optional[str]).
    """
    workspace_root = Path(workspace_root or ".")
    now = now_ts or _iso_ts()
    disallowed = disallowed_approver_ids or set()

    request_id = receipt.get("request_id")
    receipt_id = receipt.get("receipt_id")
    nonce = receipt.get("nonce", "")
    decision = (receipt.get("decision") or "").lower()
    approver = receipt.get("approver") or {}
    approver_id = approver.get("id") or approver.get("sub") or approver.get("agent_id") or ""

    if not request_id or not receipt_id:
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id or "unknown",
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "missing_request_or_receipt_id", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "missing_request_or_receipt_id"

    req = load_approval_request(workspace_root, request_id)
    if not req:
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "request_not_found", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "request_not_found"

    if req.get("expires_ts") and req["expires_ts"] < now:
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "expired", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "expired"

    bridge_id = receipt.get("bridge_id", "")
    if not bridge_id:
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "missing_bridge_id", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "missing_bridge_id"

    bridge_config = _load_bridge_config(workspace_root, bridge_id)
    if not bridge_config:
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "unknown_bridge", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "unknown_bridge"

    if not _verify_signature(receipt, bridge_config, workspace_root):
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "invalid_signature", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "invalid_signature"

    req_scope = req.get("scope") or {}
    for k, v in (scope or {}).items():
        if req_scope.get(k) != v:
            ev = emit(
                "EXTERNAL_APPROVAL_REJECTED",
                "approval_receipt",
                receipt_id,
                {"receipt_id": receipt_id, "request_id": request_id, "reason": "scope_mismatch", "ts": now},
                scope=scope,
                actor=actor,
                workspace_root=workspace_root,
            )
            return False, ev, "scope_mismatch"

    if _is_replay(workspace_root, receipt_id, nonce):
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "replay", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "replay"

    if approver_id and approver_id in disallowed:
        ev = emit(
            "EXTERNAL_APPROVAL_REJECTED",
            "approval_receipt",
            receipt_id,
            {"receipt_id": receipt_id, "request_id": request_id, "reason": "independence_rule", "ts": now},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev, "independence_rule"

    _record_receipt_seen(workspace_root, receipt_id, nonce)

    if decision == "approve":
        ev = emit(
            "APPROVAL_GRANTED",
            "approval_receipt",
            receipt_id,
            {
                "receipt_id": receipt_id,
                "request_id": request_id,
                "work_item_id": req.get("work_item_id"),
                "approver": approver,
                "receipt_artifact_ref": receipt.get("raw_evidence_artifact_id"),
                "ts": now,
            },
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return True, ev, None
    else:
        ev = emit(
            "APPROVAL_DENIED",
            "approval_receipt",
            receipt_id,
            {
                "receipt_id": receipt_id,
                "request_id": request_id,
                "work_item_id": req.get("work_item_id"),
                "approver": approver,
                "receipt_artifact_ref": receipt.get("raw_evidence_artifact_id"),
                "ts": now,
            },
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return True, ev, None
