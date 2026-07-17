"""Web action receipts."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.web_action_queue.schema import (
    WebActionDecisionKind,
    WebActionReceipt,
    WebActionRequest,
    new_web_action_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def receipt_for_policy(
    request: WebActionRequest,
    decision: WebActionDecisionKind,
    reason: str,
) -> WebActionReceipt:
    return WebActionReceipt(
        receipt_id=new_web_action_id().replace("wact-", "wrec-"),
        web_action_id=request.web_action_id,
        action_type=request.action_type.value,
        decision=decision,
        reason=reason,
        created_at=_now(),
        web_action_hash=request.to_payload()["web_action_hash"],
    )


__all__ = ["receipt_for_policy"]
