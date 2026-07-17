"""Deterministic hashing for agent zero state records."""

from __future__ import annotations

from typing import Any, Mapping

from hg_core.policy_safety.hashing import compute_record_hash


def hash_record(payload: Mapping[str, Any]) -> str:
    """Compute stable hash excluding hash/record_hash keys."""
    return compute_record_hash(payload)


def verify_record_hash(payload: Mapping[str, Any], expected: str) -> bool:
    if not expected:
        return False
    return hash_record(payload) == expected


__all__ = ["hash_record", "verify_record_hash"]
