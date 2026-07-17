"""Phase 26 canonical hashing helpers."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from hg_core.ledger.canonical_json import canonical_dumps

GENESIS_HASH = "sha256:phase26_genesis"


def canonical_hash(payload: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_dumps(payload)).hexdigest()


def content_hash(payload: Mapping[str, Any]) -> str:
    return canonical_hash(payload)


def chain_hash(record: Mapping[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key == "chain_hash" or key != "chain_hash"}
    body.pop("chain_hash", None)
    return canonical_hash(body)


def stable_entry_id(record: Mapping[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key not in ("entry_id", "chain_hash")}
    return "p26-" + canonical_hash(body).removeprefix("sha256:")[:20]


__all__ = ["GENESIS_HASH", "canonical_hash", "chain_hash", "content_hash", "stable_entry_id"]
