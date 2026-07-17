"""Operator review queue — build a queue of candidates needing human review.

The queue is NOT authority. It is a workflow aid.
"""

from __future__ import annotations

from hg_runtime.memory_quarantine.promotion_policy import promotion_prerequisites

_REVIEW_STATES = {
    "quarantined",
    "needs_source",
    "needs_falsification",
    "needs_operator_review",
    "approved_for_memory_by_gate",
}


def build_review_queue(store: dict) -> list:
    """Build a list of entries needing operator review.

    Includes entries in review-relevant states. Each entry includes
    candidate_id, content_summary, state, claim_text, and
    recommendation (from promotion_prerequisites).
    """
    queue = []

    for entry in store.get("entries", []):
        state = entry.get("state", "")
        if state not in _REVIEW_STATES:
            continue

        queue.append({
            "candidate_id": entry.get("candidate_id", ""),
            "content_summary": entry.get("content_summary", ""),
            "state": state,
            "claim_text": entry.get("claim_text", ""),
            "recommendation": promotion_prerequisites(entry),
        })

    return queue
