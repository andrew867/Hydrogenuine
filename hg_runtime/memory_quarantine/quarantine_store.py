"""Memory Promotion Quarantine Store — candidate knowledge sits here until
operator review and promotion gate passage.

Nothing leaves quarantine without explicit operator approval.
Candidate knowledge is NOT knowledge. Models CANNOT self-promote.
Promotion is NEVER allowed at the quarantine level without operator review.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

SCHEMA_VERSION = "memory_quarantine_v2"

CANDIDATE_STATES = {
    "candidate",
    "quarantined",
    "needs_source",
    "needs_falsification",
    "needs_operator_review",
    "rejected_overclaim",
    "deferred",
    "approved_for_memory_by_gate",
    "promoted",
}

_INVARIANTS = {
    "candidate_knowledge_is_not_knowledge": True,
    "source_grounded_is_not_truth": True,
    "model_generated_is_not_memory": True,
    "evidence_graph_support_is_not_promotion": True,
    "promotion_requires_operator_review": True,
    "promotion_requires_gate_receipt": True,
    "candidate_cannot_grant_authority": True,
    "candidate_cannot_grant_tool_permission": True,
    "candidate_cannot_grant_external_effect": True,
    "promotion_allowed": False,
    "model_output_treated_as_truth": False,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_store() -> dict:
    """Create an empty quarantine store."""
    return {
        "schema": SCHEMA_VERSION,
        "entries": [],
        **copy.deepcopy(_INVARIANTS),
    }


def create_candidate(
    *,
    candidate_id: str,
    content_summary: str,
    source: str = "model_output",
    claim_text: str = "",
    model_id: str = "",
    seed_id: str = "",
    quality_receipt_id: str = "",
    source_receipt_id: str = "",
) -> dict:
    """Create a quarantine candidate entry.

    This entry is a CANDIDATE -- it is NOT knowledge until an operator
    explicitly promotes it through the gate.
    """
    return {
        "candidate_id": candidate_id,
        "content_summary": content_summary,
        "source": source,
        "claim_text": claim_text,
        "model_id": model_id,
        "seed_id": seed_id,
        "quality_receipt_id": quality_receipt_id,
        "source_receipt_id": source_receipt_id,
        "state": "quarantined",
        "promotion_allowed": False,
        "reviewer": "",
        "review_reason": "",
        "transitions": [],
        "created_at": _utc_now_iso(),
    }


def add_candidate(store: dict, candidate: dict) -> dict:
    """Add a candidate to the store. Returns a new store (immutable).

    Re-applies _INVARIANTS to ensure they are never overridden.
    """
    new_store = dict(store)
    new_store["entries"] = list(store.get("entries", [])) + [candidate]
    new_store.update(copy.deepcopy(_INVARIANTS))
    return new_store


def transition_state(
    store: dict,
    candidate_id: str,
    *,
    new_state: str,
    reason: str = "",
    reviewer: str = "",
) -> dict:
    """Transition a candidate to a new state.

    Rules:
    - "promoted" requires reviewer=="operator" AND previous state=="approved_for_memory_by_gate"
    - "approved_for_memory_by_gate" requires reviewer in ("gate", "operator")
    - "rejected_overclaim" can be set by anyone
    - If reviewer is "model" and new_state is "promoted" or
      "approved_for_memory_by_gate": force new_state to
      "needs_operator_review" with reason="model_cannot_self_promote"
    - promotion_allowed stays False always
    """
    new_store = dict(store)
    new_store["entries"] = [dict(e) for e in store.get("entries", [])]

    for entry in new_store["entries"]:
        if entry.get("candidate_id") != candidate_id:
            continue

        actual_state = new_state
        actual_reason = reason

        # Model cannot self-promote or self-approve
        if reviewer == "model" and new_state in ("promoted", "approved_for_memory_by_gate"):
            actual_state = "needs_operator_review"
            actual_reason = "model_cannot_self_promote"

        # "promoted" requires operator AND previous state approved_for_memory_by_gate
        elif new_state == "promoted":
            if reviewer != "operator" or entry.get("state") != "approved_for_memory_by_gate":
                actual_state = "needs_operator_review"
                actual_reason = reason or "promotion_prerequisites_not_met"

        # "approved_for_memory_by_gate" requires gate or operator reviewer
        elif new_state == "approved_for_memory_by_gate":
            if reviewer not in ("gate", "operator"):
                actual_state = "needs_operator_review"
                actual_reason = reason or "approval_requires_gate_or_operator"

        entry["state"] = actual_state
        entry["reviewer"] = reviewer
        entry["review_reason"] = actual_reason
        entry["promotion_allowed"] = False

        entry.setdefault("transitions", [])
        entry["transitions"].append({
            "to_state": actual_state,
            "reason": actual_reason,
            "reviewer": reviewer,
            "at": _utc_now_iso(),
        })

        break

    new_store.update(copy.deepcopy(_INVARIANTS))
    return new_store


def get_by_state(store: dict, state: str) -> list:
    """Get all entries in a given state."""
    return [
        dict(e) for e in store.get("entries", [])
        if e.get("state") == state
    ]


def get_promotable(store: dict) -> list:
    """Get entries in 'approved_for_memory_by_gate' state."""
    return get_by_state(store, "approved_for_memory_by_gate")


def store_summary(store: dict) -> dict:
    """Summary counts by state."""
    entries = store.get("entries", [])
    counts = {}
    for e in entries:
        state = e.get("state", "unknown")
        counts[state] = counts.get(state, 0) + 1
    return {
        "total_entries": len(entries),
        "counts_by_state": counts,
    }


def validate_store(store: dict) -> list:
    """Validate store invariants. Returns list of errors (empty = valid)."""
    errors = []

    if store.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, "
            f"got {store.get('schema')}"
        )

    for key, expected in _INVARIANTS.items():
        if store.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    for i, entry in enumerate(store.get("entries", [])):
        state = entry.get("state")
        if state not in CANDIDATE_STATES:
            errors.append(f"entry[{i}] has invalid state: {state}")

        if entry.get("promotion_allowed") is not False:
            errors.append(f"entry[{i}] promotion_allowed must be False")

        if state == "promoted" and entry.get("reviewer") != "operator":
            errors.append(
                f"entry[{i}] is promoted but reviewer is "
                f"'{entry.get('reviewer')}', not 'operator'"
            )

    return errors
