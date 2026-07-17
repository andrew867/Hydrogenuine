"""Stable hashing for policy-safety records."""

from __future__ import annotations

from typing import Any, Mapping

from hg_core.governance.canonical_hash import canonical_hash


def compute_record_hash(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k not in {"hash", "record_hash"}}
    return canonical_hash(body)


__all__ = ["compute_record_hash"]
