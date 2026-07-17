"""Local/manual message import — cargo only."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.agent_zero_console.policy import message_is_cargo_only
from hg_runtime.agent_zero_console.receipts import write_receipt
from hg_runtime.agent_zero_console.redaction import redact_text, sha256
from hg_runtime.agent_zero_console.schema import TrustBoundaryVerdict
from hg_runtime.message_center.classifier import classify_message
from hg_runtime.message_center.schema import (
    MessageCenterItem,
    MessageImportMode,
    MessageStatus,
    new_message_id,
)
from hg_runtime.message_center.store import MessageCenterStore

WORKSPACE = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def import_pasted_text(
    body: str,
    *,
    sender_display: str | None = None,
    subject: str | None = None,
    conversation_id: str = "message-center",
) -> MessageCenterItem:
    classification, trust = classify_message(body)
    item = MessageCenterItem(
        message_id=new_message_id(),
        source_type="manual_paste",
        imported_at=_now(),
        sender_display=sender_display,
        subject=subject,
        sanitized_body_preview=redact_text(body),
        body_hash=sha256(body),
        sensitivity="normal",
        trust_boundary_verdict=trust,
        classification=classification,
        status=MessageStatus.IMPORTED,
        import_mode=MessageImportMode.PASTED_TEXT,
    )
    MessageCenterStore().append(item.to_dict())
    write_receipt(
        event_type="MESSAGE_IMPORTED",
        conversation_id=conversation_id,
        payload={
            **item.to_dict(),
            "cargo_only": True,
            "policy_override_attempt": message_is_cargo_only(body),
        },
    )
    return item


def import_fixture_message(body: str, *, fixture_id: str = "fixture-1") -> MessageCenterItem:
    return import_pasted_text(body, sender_display=f"fixture:{fixture_id}", subject="fixture")


def import_local_file(path: Path, *, conversation_id: str = "message-center") -> MessageCenterItem:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in {".txt", ".md", ".json"}:
        raise ValueError("unsupported file type for safe text import")
    body = path.read_text(encoding="utf-8", errors="replace")[:8000]
    item = import_pasted_text(body, subject=path.name, conversation_id=conversation_id)
    item.import_mode = MessageImportMode.LOCAL_FILE_SAFE_TEXT
    return item


__all__ = ["import_fixture_message", "import_local_file", "import_pasted_text"]
