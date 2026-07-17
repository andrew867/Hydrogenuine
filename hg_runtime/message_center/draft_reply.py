"""Draft reply engine — draft only, never send."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.agent_zero_console.draft_policy import draft_may_send, operator_edit_invalidates_approval
from hg_runtime.agent_zero_console.receipts import write_receipt
from hg_runtime.agent_zero_console.redaction import redact_text, sha256
from hg_runtime.message_center.schema import DraftReply, MessageCenterItem, new_draft_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_draft_reply(
    message: MessageCenterItem,
    *,
    conversation_id: str | None = None,
    tone: str = "neutral",
) -> DraftReply:
    assert draft_may_send() is False
    body = (
        f"Draft reply to message {message.message_id}: "
        f"acknowledge receipt and note that live send is disabled. "
        f"Source preview hash {message.body_hash[:12]}."
    )
    draft = DraftReply(
        draft_id=new_draft_id(),
        source_message_id=message.message_id,
        conversation_id=conversation_id,
        target_surface="message",
        recipient_display=message.sender_display,
        draft_text=body,
        draft_text_hash=sha256(body),
        tone=tone,
        risk_class="low" if message.trust_boundary_verdict.value == "cargo" else "elevated",
        status="draft",
        send_ref=None,
    )
    write_receipt(
        event_type="DRAFT_REPLY_CREATED",
        conversation_id=conversation_id or "message-center",
        payload={**draft.to_dict(), "preview": redact_text(body)},
    )
    return draft


def record_operator_edit(draft: DraftReply, *, new_text: str) -> DraftReply:
    draft.draft_text = new_text
    draft.draft_text_hash = sha256(new_text)
    if operator_edit_invalidates_approval():
        draft.approval_ref = None
        draft.status = "edited"
    write_receipt(
        event_type="OPERATOR_EDIT_RECORDED",
        conversation_id=draft.conversation_id or "message-center",
        payload={"draft_id": draft.draft_id, "draft_text_hash": draft.draft_text_hash},
    )
    return draft


__all__ = ["create_draft_reply", "record_operator_edit"]
