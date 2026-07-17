"""Stable hashing for Trust Boundary data and receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

HASH_EXCLUDE_KEYS = frozenset(
    {"hash", "content_hash", "datum_id", "advisory_id", "receipt_id", "receipt_ref", "previous_hash"}
)


def tb_hash(payload: dict[str, Any]) -> str:
    filtered = {k: v for k, v in payload.items() if k not in HASH_EXCLUDE_KEYS}
    blob = json.dumps(filtered, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


__all__ = ["HASH_EXCLUDE_KEYS", "tb_hash"]
