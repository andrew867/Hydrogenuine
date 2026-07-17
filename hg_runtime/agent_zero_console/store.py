"""Conversation persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.agent_zero_console.receipts import write_receipt
from hg_runtime.agent_zero_console.redaction import redact_text, sha256
from hg_runtime.agent_zero_console.schema import (
    ContextGrant,
    Conversation,
    ConversationMessage,
    ConversationMode,
    ConversationRole,
    new_conversation_id,
    new_message_id,
)

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / ".hg-local/agent_zero_console/conversations"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ROOT

    def start(self, *, mode: ConversationMode = ConversationMode.CHAT) -> Conversation:
        conv = Conversation(conversation_id=new_conversation_id(), started_at=_now(), mode=mode)
        self._save_conversation(conv)
        write_receipt(event_type="CONVERSATION_STARTED", conversation_id=conv.conversation_id, payload=conv.to_dict())
        return conv

    def _conv_dir(self, conversation_id: str) -> Path:
        d = self.root / conversation_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_conversation(self, conv: Conversation) -> None:
        path = self._conv_dir(conv.conversation_id) / "conversation.json"
        path.write_text(json.dumps(conv.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    def load(self, conversation_id: str) -> Conversation:
        path = self._conv_dir(conversation_id) / "conversation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        grants = [ContextGrant(**g) for g in data.get("context_grants", []) if "grant_id" in g]
        return Conversation(
            conversation_id=data["conversation_id"],
            started_at=data["started_at"],
            mode=ConversationMode(data.get("mode", "chat")),
            context_grants=grants,
            stopped_at=data.get("stopped_at"),
        )

    def append_message(
        self,
        *,
        conversation_id: str,
        role: ConversationRole,
        text: str,
        mode: ConversationMode = ConversationMode.CHAT,
    ) -> ConversationMessage:
        preview = redact_text(text)
        msg = ConversationMessage(
            message_id=new_message_id(),
            conversation_id=conversation_id,
            role=role,
            mode=mode,
            text_preview=preview,
            text_hash=sha256(text),
            created_at=_now(),
        )
        path = self._conv_dir(conversation_id) / "messages.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(msg.to_dict(), sort_keys=True) + "\n")
        write_receipt(
            event_type="MESSAGE_RECEIVED",
            conversation_id=conversation_id,
            payload={"message_id": msg.message_id, "role": role.value, "text_hash": msg.text_hash, "preview": preview},
        )
        return msg

    def grant_context(self, conversation_id: str, *, source_ref: str, scope: str) -> ContextGrant:
        conv = self.load(conversation_id)
        grant = ContextGrant(
            grant_id=f"grant-{len(conv.context_grants)+1}",
            source_ref=source_ref,
            granted_at=_now(),
            scope=scope,
            preview_hash=sha256(source_ref),
        )
        conv.context_grants.append(grant)
        self._save_conversation(conv)
        write_receipt(
            event_type="CONTEXT_GRANTED",
            conversation_id=conversation_id,
            payload=grant.to_dict(),
        )
        return grant

    def list_messages(self, conversation_id: str) -> list[dict]:
        path = self._conv_dir(conversation_id) / "messages.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


__all__ = ["ConversationStore", "ROOT"]
