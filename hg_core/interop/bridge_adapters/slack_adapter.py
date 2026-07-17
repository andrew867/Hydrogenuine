"""Slack adapter: format approval request for Slack, parse webhook receipt."""
from __future__ import annotations

from typing import Any, Dict, Optional


BRIDGE_ID = "slack"


def format_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Format approval request for Slack (message payload). Minimal exposure."""
    return {
        "channel": "approvals",
        "text": f"Approval request {request.get('request_id', '')} for work item {request.get('work_item_id', '')}",
        "request_id": request.get("request_id"),
        "work_item_id": request.get("work_item_id"),
        "expires_ts": request.get("expires_ts"),
        "summary_artifact_id": request.get("summary_artifact_id"),
    }


def parse_receipt(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Slack webhook payload into standard receipt. Returns None if invalid."""
    # Slack interactive payload may have actions[].value = "approve" or "deny"
    actions = raw.get("actions") or []
    decision = "deny"
    for a in actions:
        v = (a.get("value") or "").lower()
        if v in ("approve", "deny"):
            decision = v
            break
    user = raw.get("user") or {}
    user_id = user.get("id") or user.get("name") or ""
    ts = raw.get("message_ts") or raw.get("response_url") or raw.get("ts", "")
    req_id = raw.get("request_id") or (raw.get("callback_id") or "").split(":")[0]
    receipt_id = raw.get("receipt_id") or f"slack_{user_id}_{ts}".replace(".", "_")
    nonce = raw.get("nonce") or receipt_id
    return {
        "receipt_id": receipt_id,
        "request_id": req_id,
        "decision": decision,
        "approver": {"id": user_id, "source": "slack"},
        "ts": ts,
        "nonce": nonce,
        "signature": raw.get("signature"),
        "bridge_id": BRIDGE_ID,
        "raw_evidence_artifact_id": raw.get("raw_evidence_artifact_id"),
    }
