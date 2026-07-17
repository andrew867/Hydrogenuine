"""Stable hashing for Audio I/O receipts and envelopes.

Hashes are computed over redacted payloads only. A raw secret or raw audio byte
never enters the hash domain — the receipt proves "an utterance/transcript was
produced" without revealing its secret-bearing original.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

HASH_EXCLUDE_KEYS = frozenset(
    {
        "hash",
        "content_hash",
        "receipt_id",
        "receipt_ref",
        "time_receipt_ref",
        "envelope_id",
        "request_id",
        "previous_hash",
    }
)


def audio_hash(payload: dict[str, Any]) -> str:
    filtered = {k: v for k, v in payload.items() if k not in HASH_EXCLUDE_KEYS}
    blob = json.dumps(filtered, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def text_hash(text: str) -> str:
    """Hash of (already-redacted) text. Never call on raw, unredacted content."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = ["HASH_EXCLUDE_KEYS", "audio_hash", "text_hash"]
