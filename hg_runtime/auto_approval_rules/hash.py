"""Stable hashing for auto-approval rules."""

from __future__ import annotations

from hg_runtime.exciton_action_model.hash import action_hash

RULE_HASH_EXCLUDE = frozenset({"rule_hash"})


def rule_hash(payload: dict) -> str:
    stripped = {k: v for k, v in payload.items() if k not in RULE_HASH_EXCLUDE}
    return action_hash(stripped)


__all__ = ["RULE_HASH_EXCLUDE", "rule_hash"]
