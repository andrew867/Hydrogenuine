"""Email adapter: format approval request for email, parse link/token receipt."""
from __future__ import annotations

from typing import Any, Dict, Optional


BRIDGE_ID = "email"


def format_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Format approval request for email (signed link / token). Minimal exposure."""
    return {
        "to": "approvers@example.com",
        "subject": f"Approval: {request.get('work_item_id', '')}",
        "request_id": request.get("request_id"),
        "work_item_id": request.get("work_item_id"),
        "expires_ts": request.get("expires_ts"),
        "summary_artifact_id": request.get("summary_artifact_id"),
        "nonce": request.get("nonce"),
    }


def parse_receipt(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse email webhook or callback payload into standard receipt."""
    receipt_id = raw.get("receipt_id") or raw.get("token_id") or ""
    request_id = raw.get("request_id", "")
    decision = (raw.get("decision") or "deny").lower()
    if decision not in ("approve", "deny"):
        decision = "deny"
    approver = raw.get("approver") or {"id": raw.get("approver_id", ""), "source": "email"}
    ts = raw.get("ts", "")
    nonce = raw.get("nonce") or receipt_id
    return {
        "receipt_id": receipt_id,
        "request_id": request_id,
        "decision": decision,
        "approver": approver,
        "ts": ts,
        "nonce": nonce,
        "signature": raw.get("signature"),
        "bridge_id": BRIDGE_ID,
        "raw_evidence_artifact_id": raw.get("raw_evidence_artifact_id"),
    }
