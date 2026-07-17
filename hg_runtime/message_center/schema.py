"""Message Center schemas."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from hg_runtime.agent_zero_console.redaction import sha256
from hg_runtime.agent_zero_console.schema import TrustBoundaryVerdict


def _frozen() -> dict:
    return {
        "authority_created": False,
        "permission_granted": False,
        "redaction_applied": True,
        "hidden_chain_of_thought_present": False,
    }


class MessageClassification(str, Enum):
    INFORMATIONAL = "informational"
    REQUEST = "request"
    SPAM = "spam"
    PHISHING = "phishing"
    PROMPT_INJECTION = "prompt_injection"
    UNKNOWN = "unknown"


class MessageImportMode(str, Enum):
    PASTED_TEXT = "pasted_text"
    LOCAL_FILE_SAFE_TEXT = "local_file_safe_text"
    FIXTURE_MESSAGE = "fixture_message"


class MessageStatus(str, Enum):
    IMPORTED = "imported"
    CLASSIFIED = "classified"
    DRAFTED = "drafted"
    QUEUED = "queued"


@dataclass
class DraftReply:
    draft_id: str
    source_message_id: str
    conversation_id: str | None
    target_surface: str
    recipient_display: str | None
    draft_text: str
    draft_text_hash: str
    tone: str
    risk_class: str
    status: str = "draft"
    approval_ref: str | None = None
    send_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "send_ref": None,
            **_frozen(),
        }


@dataclass
class MessageCenterItem:
    message_id: str
    source_type: str
    imported_at: str
    sender_display: str | None
    subject: str | None
    sanitized_body_preview: str
    body_hash: str
    sensitivity: str
    trust_boundary_verdict: TrustBoundaryVerdict
    classification: MessageClassification
    status: MessageStatus
    import_mode: MessageImportMode

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "source_type": self.source_type,
            "imported_at": self.imported_at,
            "sender_display": self.sender_display,
            "subject": self.subject,
            "sanitized_body_preview": self.sanitized_body_preview,
            "body_hash": self.body_hash,
            "sensitivity": self.sensitivity,
            "trust_boundary_verdict": self.trust_boundary_verdict.value,
            "classification": self.classification.value,
            "status": self.status.value,
            "import_mode": self.import_mode.value,
            **_frozen(),
        }


def new_message_id() -> str:
    return f"mcmsg-{uuid.uuid4().hex[:12]}"


def new_draft_id() -> str:
    return f"mcdraft-{uuid.uuid4().hex[:12]}"


__all__ = [
    "DraftReply",
    "MessageCenterItem",
    "MessageClassification",
    "MessageImportMode",
    "MessageStatus",
    "new_draft_id",
    "new_message_id",
]
