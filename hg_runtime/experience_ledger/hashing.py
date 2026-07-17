"""Deterministic hashing helpers for P26 records."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash


HASH_FIELDS = {
    "record_hash",
    "policy_hash",
    "experience_hash",
    "memory_hash",
    "recall_hash",
    "request_hash",
    "decision_hash",
    "retraction_hash",
    "manifest_hash",
    "gate_hash",
}


def stable_hash(record: Mapping[str, Any]) -> str:
    return canonical_hash({k: v for k, v in record.items() if k not in HASH_FIELDS})


def with_hash(record: dict, hash_field: str = "record_hash") -> dict:
    record[hash_field] = stable_hash(record)
    return record

