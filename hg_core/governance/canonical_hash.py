"""Canonical hashing helpers for GPP trace records."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from hg_core.ledger.canonical_json import canonical_dumps

HASH_PREFIX = "sha256:"


def canonical_hash(value: Any) -> str:
    """Hash a JSON-serializable value with the ledger canonical JSON rules."""
    return HASH_PREFIX + hashlib.sha256(canonical_dumps(jsonable(value))).hexdigest()


def jsonable(value: Any) -> Any:
    """Copy read-only mappings/tuples back into canonical JSON containers."""
    if isinstance(value, Mapping):
        return {key: jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def without_keys(value: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    blocked = set(keys)
    return {key: jsonable(val) for key, val in value.items() if key not in blocked}


def trace_record_hash(record: Mapping[str, Any]) -> str:
    """Hash a trace record body, excluding the stored event hash."""
    return canonical_hash(without_keys(record, {"event_hash"}))


__all__ = ["HASH_PREFIX", "canonical_hash", "jsonable", "trace_record_hash", "without_keys"]
