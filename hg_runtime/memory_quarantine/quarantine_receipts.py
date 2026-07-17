"""Quarantine receipts — snapshot receipts of quarantine state.

Receipts are NOT authority. They are audit records.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from hg_runtime.memory_quarantine.quarantine_store import (
    SCHEMA_VERSION,
    _INVARIANTS,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _receipt_id(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def create_quarantine_receipt(store: dict, *, run_id: str = "") -> dict:
    """Create a snapshot receipt of quarantine state."""
    entries = store.get("entries", [])

    counts = {}
    for e in entries:
        state = e.get("state", "unknown")
        counts[state] = counts.get(state, 0) + 1

    receipt = {
        "schema": SCHEMA_VERSION,
        "receipt_type": "quarantine_snapshot",
        "run_id": run_id,
        "candidate_count": len(entries),
        "quarantined_count": counts.get("quarantined", 0),
        "promoted_count": counts.get("promoted", 0),
        "rejected_count": counts.get("rejected_overclaim", 0),
        "deferred_count": counts.get("deferred", 0),
        "awaiting_gate_count": sum(
            1 for e in entries
            if e.get("state") not in ("approved_for_memory_by_gate", "promoted", "rejected_overclaim", "deferred")
        ),
        **_INVARIANTS,
        "timestamp": _utc_now_iso(),
    }
    receipt["receipt_id"] = _receipt_id(receipt)
    return receipt


def validate_quarantine_receipt(receipt: dict) -> list:
    """Validate a quarantine receipt's invariants.

    Returns list of errors (empty = valid).
    """
    errors = []

    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, "
            f"got {receipt.get('schema')}"
        )

    for key, expected in _INVARIANTS.items():
        if receipt.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    return errors
