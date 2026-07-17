"""Quarantine manager for overnight research artifacts.

All model outputs are quarantined by default. Nothing promoted.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


def quarantine_model_output(*, model_output: dict, reason: str = "model output is not truth") -> dict:
    return {
        "quarantine_id": hashlib.sha256(json.dumps(model_output, sort_keys=True).encode()).hexdigest()[:16],
        "item_type": "model_output",
        "item_ref": model_output.get("prompt_id", ""),
        "quarantine_reason": reason,
        "promoted": False,
        "promotion_blocked_by": "overnight_research_doctrine",
        "operator_review_required": True,
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
    }


def quarantine_claim(*, claim: dict, reason: str = "candidate knowledge is not knowledge") -> dict:
    return {
        "quarantine_id": hashlib.sha256(claim.get("claim_text", "").encode()).hexdigest()[:16],
        "item_type": "claim",
        "item_ref": claim.get("claim_id", ""),
        "quarantine_reason": reason,
        "promoted": False,
        "promotion_blocked_by": "overnight_research_doctrine",
        "operator_review_required": True,
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
    }


def build_quarantine_ledger(*, model_outputs: list[dict], claims: dict) -> list[dict]:
    entries = []
    for mo in model_outputs:
        entries.append(quarantine_model_output(model_output=mo))
    for claim in claims.get("claims", []):
        entries.append(quarantine_claim(claim=claim))
    return entries


def write_quarantine_ledger(entries: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "quarantine_ledger.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return path
