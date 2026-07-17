"""Deterministic hashing for web action requests."""

from __future__ import annotations

from hg_runtime.exciton_action_model.hash import action_hash

WEB_HASH_EXCLUDE = frozenset({"web_action_hash", "receipt_hash"})


def web_action_hash(payload: dict) -> str:
    stripped = {k: v for k, v in payload.items() if k not in WEB_HASH_EXCLUDE}
    return action_hash(stripped)


__all__ = ["WEB_HASH_EXCLUDE", "web_action_hash"]
