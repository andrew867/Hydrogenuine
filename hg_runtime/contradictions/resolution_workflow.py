"""Contradiction resolution workflow — operator-guided only.

Automated suggestions allowed. Automated truth resolution forbidden.
No promotion. No memory write. No external action. No operator approval.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

RESOLUTION_STATES = {
    "unresolved",
    "needs_primary_source",
    "needs_operator_review",
    "scope_difference",
    "source_quality_difference",
    "rejected_overclaim",
    "deferred",
    "resolved_by_operator_review",
}

_SUGGESTION_STATES = {
    "needs_primary_source",
    "scope_difference",
    "source_quality_difference",
    "rejected_overclaim",
    "deferred",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id() -> str:
    import secrets
    return secrets.token_hex(12)


def suggest_resolution(contradiction: dict) -> dict:
    """Suggest a resolution state for a contradiction.

    This is an automated suggestion only. It does NOT resolve the
    contradiction. Operator review is required for resolution.
    """
    summary = contradiction.get("summary", "").lower()
    c_type = contradiction.get("contradiction_type", "")

    suggested = "needs_operator_review"
    reason = "Default: requires operator judgment."

    if "quality" in summary and "issues" in summary:
        suggested = "source_quality_difference"
        reason = "Quality issues suggest source quality difference."
    elif "scope" in summary or "different context" in summary:
        suggested = "scope_difference"
        reason = "Summary suggests scope difference between claims."
    elif "overclaim" in summary or "unsupported" in summary:
        suggested = "rejected_overclaim"
        reason = "Summary suggests an unsupported overclaim."

    return {
        "contradiction_id": contradiction.get("contradiction_id", ""),
        "suggested_state": suggested,
        "suggestion_reason": reason,
        "is_automated_suggestion": True,
        "is_final_resolution": False,
        "promotion_allowed": False,
        "operator_review_required": True,
    }


def operator_resolve(
    *,
    contradiction: dict,
    new_state: str,
    note: str = "",
    operator_id: str = "",
    review_dir: str = "",
) -> dict:
    """Record an operator resolution for a contradiction.

    Writes a new receipt to review_dir. Does NOT mutate the original
    proof directory. Does NOT promote knowledge.
    """
    if new_state not in RESOLUTION_STATES:
        raise ValueError(
            f"Invalid state '{new_state}'. Must be one of: {RESOLUTION_STATES}"
        )

    receipt = {
        "resolution_receipt_id": _make_id(),
        "contradiction_id": contradiction.get("contradiction_id", ""),
        "previous_state": "unresolved",
        "new_state": new_state,
        "operator_id": operator_id,
        "operator_note": note,
        "resolved_at": _utc_now(),
        "is_final_resolution": new_state == "resolved_by_operator_review",
        "promotion_allowed": False,
        "operator_review_required": True,
        "knowledge_promoted": False,
        "memory_written": False,
        "external_action_taken": False,
    }

    if review_dir:
        os.makedirs(review_dir, exist_ok=True)
        path = os.path.join(review_dir, "resolution_receipts.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, sort_keys=True) + "\n")
        receipt["written_to"] = path

    return receipt


def list_contradictions_with_status(
    contradictions: list[dict],
    review_dir: str = "",
) -> list[dict]:
    """List contradictions with their resolution status."""
    resolutions = {}
    if review_dir:
        path = os.path.join(review_dir, "resolution_receipts.jsonl")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        r = json.loads(line)
                        cid = r.get("contradiction_id", "")
                        resolutions[cid] = r

    results = []
    for c in contradictions:
        cid = c.get("contradiction_id", "")
        resolution = resolutions.get(cid)
        results.append({
            "contradiction_id": cid,
            "contradiction_type": c.get("contradiction_type", ""),
            "summary": c.get("summary", ""),
            "state": resolution["new_state"] if resolution else "unresolved",
            "operator_note": resolution.get("operator_note", "") if resolution else "",
        })
    return results
