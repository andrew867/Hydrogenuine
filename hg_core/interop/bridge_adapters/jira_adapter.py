"""Jira adapter: format approval request for Jira, parse workflow transition webhook."""
from __future__ import annotations

from typing import Any, Dict, Optional


BRIDGE_ID = "jira"


def format_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Format approval request for Jira (issue or transition). Minimal exposure."""
    return {
        "project": "APPROVAL",
        "summary": f"Approval: {request.get('work_item_id', '')}",
        "request_id": request.get("request_id"),
        "work_item_id": request.get("work_item_id"),
        "expires_ts": request.get("expires_ts"),
        "summary_artifact_id": request.get("summary_artifact_id"),
    }


def parse_receipt(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Jira webhook (transition/issue event) into standard receipt."""
    # Jira webhook may have issue.key, transition.to, user
    issue = raw.get("issue") or {}
    user = raw.get("user") or raw.get("actor") or {}
    transition = raw.get("transition") or raw.get("changelog", {}).get("items", [{}])[0] or {}
    to_state = (transition.get("toString") or transition.get("to") or "").lower()
    decision = "approve" if "approv" in to_state or to_state == "done" else "deny"
    receipt_id = raw.get("receipt_id") or raw.get("webhook_id") or issue.get("key") or ""
    request_id = raw.get("request_id") or (raw.get("request_id_ref") or "")
    ts = raw.get("timestamp") or raw.get("ts", "")
    nonce = raw.get("nonce") or receipt_id
    return {
        "receipt_id": receipt_id,
        "request_id": request_id,
        "decision": decision,
        "approver": {"id": user.get("accountId") or user.get("key", ""), "source": "jira"},
        "ts": ts,
        "nonce": nonce,
        "signature": raw.get("signature"),
        "bridge_id": BRIDGE_ID,
        "raw_evidence_artifact_id": raw.get("raw_evidence_artifact_id"),
    }
