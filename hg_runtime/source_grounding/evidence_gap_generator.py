"""Generate evidence gaps from claims that lack support."""

from __future__ import annotations

import hashlib
import json

SCHEMA_VERSION = "evidence_gap_v1"


def create_evidence_gap(*, seed_id: str, claim: str, gap_reason: str,
                        source_receipt_id: str = "", priority: str = "medium",
                        suggested_search: str = "") -> dict:
    gap = {
        "schema": SCHEMA_VERSION,
        "gap_id": "",
        "seed_id": seed_id,
        "claim": claim,
        "gap_reason": gap_reason,
        "source_receipt_id": source_receipt_id,
        "priority": priority,
        "suggested_search": suggested_search,
        "resolved": False,
        "resolution": "",
    }
    raw = json.dumps(gap, sort_keys=True)
    gap["gap_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return gap
