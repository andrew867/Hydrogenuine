"""EGI stable hashing — deterministic record digests."""

from __future__ import annotations

from typing import Any, Mapping

from hg_core.governance.canonical_hash import canonical_hash


def compute_record_hash(payload: Mapping[str, Any]) -> str:
    """Hash a serializable payload excluding any existing hash field."""
    body = {k: v for k, v in payload.items() if k != "hash"}
    return canonical_hash(body)


__all__ = ["compute_record_hash"]
