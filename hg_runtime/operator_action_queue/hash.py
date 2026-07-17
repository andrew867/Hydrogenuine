"""Deterministic hashing for operator queue items and receipts."""

from __future__ import annotations

from hg_runtime.exciton_action_model.hash import ACTION_HASH_EXCLUDE_KEYS, action_hash

QUEUE_HASH_EXCLUDE_KEYS = ACTION_HASH_EXCLUDE_KEYS | frozenset({"queue_hash"})


def queue_hash(payload: dict) -> str:
    """Stable hash over queue item payload (excludes queue_hash itself)."""
    stripped = {k: v for k, v in payload.items() if k not in QUEUE_HASH_EXCLUDE_KEYS}
    return action_hash(stripped)


__all__ = ["QUEUE_HASH_EXCLUDE_KEYS", "queue_hash"]
