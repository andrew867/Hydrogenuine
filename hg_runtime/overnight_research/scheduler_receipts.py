"""Scheduler receipts for overnight research backlog drain.

Every scheduling decision is receipted. No promotion.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

SCHEMA_VERSION = "scheduler_receipt_v1"


def make_receipt(
    *,
    run_id: str,
    event_type: str,
    topic_id: str = "",
    budget_before: dict | None = None,
    budget_after: dict | None = None,
    detail: str = "",
    errors: list[str] | None = None,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "topic_id": topic_id,
        "event_type": event_type,
        "budget_before": budget_before or {},
        "budget_after": budget_after or {},
        "detail": detail,
        "errors": errors or [],
        "promotion_allowed": False,
        "operator_review_required": True,
        "no_external_effects_except_allowed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_receipts(receipts: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "scheduler_receipts.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in receipts:
            f.write(json.dumps(r, default=str) + "\n")
    return path
