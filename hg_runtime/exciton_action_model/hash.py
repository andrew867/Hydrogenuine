"""Deterministic hashing for EXCITON action model objects.

Volatile keys (receipt_id, generated timestamps in hash fields) are excluded so
two builds over identical semantic content produce the same hash.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

ACTION_HASH_EXCLUDE_KEYS = frozenset(
    {
        "item_hash",
        "receipt_hash",
        "action_hash",
        "generated_at",
        "snapshot_hash",
        "content_hash",
    }
)


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in ACTION_HASH_EXCLUDE_KEYS}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def action_hash(payload: dict[str, Any]) -> str:
    """Stable SHA-256 over canonical JSON. Never include secret values — use refs."""
    canonical = json.dumps(_strip(payload), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


ActionHash = str

__all__ = ["ACTION_HASH_EXCLUDE_KEYS", "ActionHash", "action_hash"]
