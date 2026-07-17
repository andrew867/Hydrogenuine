"""ServiceNow adapter: format approval request for change, parse approval webhook."""
from __future__ import annotations

from typing import Any, Dict, Optional


BRIDGE_ID = "servicenow"


def format_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Format approval request for ServiceNow change approval. Minimal exposure."""
    return {
        "table": "change_request",
        "short_description": f"Approval: {request.get('work_item_id', '')}",
        "request_id": request.get("request_id"),
        "work_item_id": request.get("work_item_id"),
        "expires_ts": request.get("expires_ts"),
        "summary_artifact_id": request.get("summary_artifact_id"),
    }


def parse_receipt(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse ServiceNow approval webhook into standard receipt."""
    receipt_id = raw.get("receipt_id") or raw.get("sys_id") or raw.get("record_id") or ""
    request_id = raw.get("request_id", "")
    state = (raw.get("state") or raw.get("approval") or "").lower()
    decision = "approve" if state in ("approved", "complete") else "deny"
    approver = raw.get("approver") or {"id": raw.get("approver_id", ""), "source": "servicenow"}
    ts = raw.get("sys_updated_on") or raw.get("ts", "")
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
