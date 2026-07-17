"""Canonical JSON for stable anchor hashes."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from hg_core.ledger.canonical_json import canonical_dumps


def canonical_json_bytes(obj: Any) -> bytes:
    return canonical_dumps(obj)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def sha256_short(obj: Any, *, length: int = 12) -> str:
    return sha256_hex(obj)[:length]


__all__ = ["canonical_json_bytes", "sha256_hex", "sha256_short"]
