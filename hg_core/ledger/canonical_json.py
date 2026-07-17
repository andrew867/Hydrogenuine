"""
Canonical JSON encoding for ledger events: stable key order, UTF-8, no insignificant whitespace.
Event hashes and signatures are computed over this encoding.
"""

from __future__ import annotations

import json
from typing import Any


def canonical_dumps(obj: Any) -> bytes:
    """
    Encode obj to canonical JSON bytes: sorted keys recursively, UTF-8, no whitespace.
    Arrays are preserved as-is (order matters).
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
