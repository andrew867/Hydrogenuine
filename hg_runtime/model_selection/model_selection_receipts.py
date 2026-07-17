"""Model selection receipts — JSONL log of every selection decision.

No promotion. No model authority. Operator review required.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def write_selection_receipt(
    out_dir: str,
    model_id: str,
    call_intent: str,
    reason: str,
    variation_reason: str = "",
    timeout_cooldown_applied: bool = False,
    resource_risk: str = "unknown",
) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model_selection_receipts.jsonl")
    receipt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_model_id": model_id,
        "call_intent": call_intent,
        "selection_reason": reason,
        "variation_reason": variation_reason,
        "timeout_cooldown_applied": timeout_cooldown_applied,
        "resource_risk": resource_risk,
        "model_selection_is_not_authority": True,
        "model_output_is_not_truth": True,
        "consensus_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": True,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt) + "\n")
    return path


def write_rotation_summary(out_dir: str, summary: dict) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model_rotation_summary.json")
    summary["timestamp"] = datetime.now(timezone.utc).isoformat()
    summary["promotion_allowed"] = False
    summary["operator_review_required"] = True
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return path
