"""Anchor signing receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.anchor_signing.schema import FROZEN_FALSE


def new_id(prefix: str = "asr") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class SigningKeyInitReceipt:
    receipt_id: str
    signer_key_id: str
    public_key_path: str
    private_key_path_redacted: str = "[REDACTED_PRIVATE_KEY_PATH]"
    rotated: bool = False
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "anchor-signing-key-init-receipt",
            "receipt_id": self.receipt_id,
            "signer_key_id": self.signer_key_id,
            "public_key_path": self.public_key_path,
            "private_key_path": self.private_key_path_redacted,
            "rotated": self.rotated,
            "created_utc": self.created_utc,
            **FROZEN_FALSE,
        }


__all__ = ["SigningKeyInitReceipt", "new_id"]
