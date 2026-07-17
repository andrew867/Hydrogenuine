"""AIS hashing helpers."""

from __future__ import annotations

from hg_runtime.memory_ledger.hash_chain import canonical_hash


def record_hash(record: dict) -> str:
    copy = {k: v for k, v in record.items() if k != "record_hash"}
    return canonical_hash(copy)
