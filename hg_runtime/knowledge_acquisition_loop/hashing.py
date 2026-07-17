"""Deterministic hashing helpers for P30 knowledge acquisition loop."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash

HASH_FIELDS = {
    "record_hash",
    "policy_hash",
    "candidate_hash",
    "task_hash",
    "source_hash",
    "result_hash",
    "gap_hash",
    "refusal_hash",
    "manifest_hash",
    "gate_hash",
    "stable_hash",
}


def stable_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in HASH_FIELDS})


def with_hash(record: dict, hash_field: str = "record_hash") -> dict:
    record[hash_field] = stable_hash(record)
    return record
