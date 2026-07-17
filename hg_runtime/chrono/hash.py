"""Stable hashing for CHRONO receipts and contexts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

HASH_EXCLUDE_KEYS = frozenset(
    {"hash", "content_hash", "receipt_id", "receipt_ref", "receipt_hash", "drift_finding_ref", "previous_hash"}
)


def chrono_hash(payload: dict[str, Any]) -> str:
    filtered = {k: v for k, v in payload.items() if k not in HASH_EXCLUDE_KEYS}
    blob = json.dumps(filtered, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


__all__ = ["HASH_EXCLUDE_KEYS", "chrono_hash"]
