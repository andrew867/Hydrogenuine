"""Classify operator chat requests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hg_runtime.agent_zero_console.policy import classify_operator_text, message_is_cargo_only
from hg_runtime.agent_zero_console.receipts import write_receipt
from hg_runtime.agent_zero_console.schema import ConsoleRequest, RequestIntent, RequestPolicyDecision, RequestSurface
from hg_runtime.agent_zero_console.redaction import sha256


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def classify_request(*, conversation_id: str, text: str, from_message_cargo: bool = False) -> ConsoleRequest:
    if from_message_cargo and message_is_cargo_only(text):
        intent, surface, reason = RequestIntent.ANSWER_ONLY, RequestSurface.MESSAGE, "cargo cannot override policy"
    else:
        intent, surface, reason = classify_operator_text(text)

    policy = RequestPolicyDecision(
        intent=intent,
        surface=surface,
        allowed=intent not in {RequestIntent.FORBIDDEN},
        reason=reason,
        queue_handoff=intent
        in {
            RequestIntent.CREATE_OPERATOR_QUEUE_ITEM,
            RequestIntent.CREATE_WEB_ACTION_QUEUE_ITEM,
            RequestIntent.CREATE_SOCIAL_DRAFT,
            RequestIntent.CREATE_MESSAGE_REPLY_DRAFT,
            RequestIntent.REQUEST_OPERATOR_REVIEW,
        },
    )
    req = ConsoleRequest(
        request_id=f"azreq-{uuid.uuid4().hex[:12]}",
        conversation_id=conversation_id,
        text=text,
        text_hash=sha256(text),
        intent=intent,
        policy=policy,
        created_at=_now(),
    )
    write_receipt(
        event_type="REQUEST_CLASSIFIED",
        conversation_id=conversation_id,
        payload={**req.to_dict(), "from_message_cargo": from_message_cargo},
    )
    return req


__all__ = ["classify_request"]
