"""Memory Promotion Quarantine — candidate knowledge sits here until
operator review and promotion gate passage.

Nothing leaves quarantine without explicit operator approval.
Candidate knowledge is NOT knowledge. Models CANNOT self-promote.
Promotion is NEVER allowed at the quarantine level without operator review.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

SCHEMA_VERSION = "memory_promotion_quarantine_v1"

QUARANTINE_STATES = {"quarantined", "under_review", "promoted", "rejected", "expired"}

_INVARIANTS = {
    "candidate_knowledge_is_not_knowledge": True,
    "promotion_requires_operator": True,
    "model_cannot_self_promote": True,
    "promotion_allowed": False,
    "operator_review_required": True,
    "no_auto_promotion": True,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_quarantine() -> dict:
    """Create an empty quarantine zone."""
    return {
        "schema": SCHEMA_VERSION,
        "entries": [],
        **copy.deepcopy(_INVARIANTS),
        "created_at": _utc_now_iso(),
    }


def quarantine_entry(
    *,
    entry_id: str,
    content_summary: str,
    source_receipt_id: str = "",
    quality_receipt_id: str = "",
    seed_id: str = "",
    claim_text: str = "",
    model_id: str = "",
    reason: str = "candidate_knowledge",
) -> dict:
    """Create a quarantine entry with state='quarantined'.

    This entry is a CANDIDATE — it is NOT knowledge until an operator
    explicitly promotes it.
    """
    return {
        "entry_id": entry_id,
        "content_summary": content_summary,
        "source_receipt_id": source_receipt_id,
        "quality_receipt_id": quality_receipt_id,
        "seed_id": seed_id,
        "claim_text": claim_text,
        "model_id": model_id,
        "reason": reason,
        "state": "quarantined",
        "reviewer": "",
        "decision_reason": "",
        "is_knowledge": False,
        "created_at": _utc_now_iso(),
        "reviewed_at": "",
    }


def add_to_quarantine(
    quarantine: dict,
    entry: dict,
    *,
    stop_panic: bool = False,
) -> dict:
    """Add an entry to the quarantine. Returns new quarantine.

    If stop_panic is True, returns the quarantine unchanged (STOP/PANIC block).
    """
    if stop_panic:
        return quarantine

    quarantine = dict(quarantine)
    quarantine["entries"] = list(quarantine.get("entries", [])) + [entry]

    # Re-enforce invariants
    quarantine.update(copy.deepcopy(_INVARIANTS))

    return quarantine


def review_entry(
    quarantine: dict,
    entry_id: str,
    *,
    reviewer: str = "operator",
    decision: str = "reject",
) -> dict:
    """Review a quarantine entry.

    decision must be 'promote' or 'reject'.

    CRITICAL SAFETY INVARIANT: if reviewer != 'operator' and
    decision == 'promote', the promotion is REJECTED with reason
    'model_cannot_self_promote'. Models and systems CANNOT promote
    their own outputs to knowledge.
    """
    if decision not in ("promote", "reject"):
        raise ValueError(
            f"Invalid decision '{decision}'. Must be 'promote' or 'reject'."
        )

    quarantine = dict(quarantine)
    quarantine["entries"] = [dict(e) for e in quarantine.get("entries", [])]

    for entry in quarantine["entries"]:
        if entry.get("entry_id") == entry_id:
            # First move to under_review
            entry["state"] = "under_review"
            entry["reviewer"] = reviewer
            entry["reviewed_at"] = _utc_now_iso()

            # CORE SAFETY: model/system cannot self-promote
            if decision == "promote" and reviewer != "operator":
                entry["state"] = "rejected"
                entry["decision_reason"] = "model_cannot_self_promote"
                entry["is_knowledge"] = False
            elif decision == "promote" and reviewer == "operator":
                entry["state"] = "promoted"
                entry["decision_reason"] = "operator_approved"
                entry["is_knowledge"] = True
            else:
                # reject
                entry["state"] = "rejected"
                entry["decision_reason"] = decision
                entry["is_knowledge"] = False

            break

    # Re-enforce quarantine-level invariants
    quarantine.update(copy.deepcopy(_INVARIANTS))

    return quarantine


def get_quarantined(quarantine: dict) -> list:
    """Get entries still in quarantine (state='quarantined')."""
    return [
        dict(e) for e in quarantine.get("entries", [])
        if e.get("state") == "quarantined"
    ]


def get_promoted(quarantine: dict) -> list:
    """Get promoted entries.

    Should be empty unless an operator explicitly approved promotion.
    """
    return [
        dict(e) for e in quarantine.get("entries", [])
        if e.get("state") == "promoted"
    ]


def get_rejected(quarantine: dict) -> list:
    """Get rejected entries."""
    return [
        dict(e) for e in quarantine.get("entries", [])
        if e.get("state") == "rejected"
    ]


def quarantine_summary(quarantine: dict) -> dict:
    """Summary statistics for the quarantine."""
    entries = quarantine.get("entries", [])

    counts = {}
    for e in entries:
        state = e.get("state", "unknown")
        counts[state] = counts.get(state, 0) + 1

    return {
        "total_entries": len(entries),
        "counts_by_state": counts,
        "quarantined": counts.get("quarantined", 0),
        "under_review": counts.get("under_review", 0),
        "promoted": counts.get("promoted", 0),
        "rejected": counts.get("rejected", 0),
        "expired": counts.get("expired", 0),
        "candidate_knowledge_is_not_knowledge": True,
        "promotion_requires_operator": True,
        "model_cannot_self_promote": True,
        "promotion_allowed": False,
        "no_auto_promotion": True,
    }


def validate_quarantine(quarantine: dict) -> list[str]:
    """Validate quarantine invariants. Returns list of errors (empty = valid)."""
    errors = []

    if quarantine.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, got {quarantine.get('schema')}"
        )

    # Core invariants — must ALWAYS hold
    if quarantine.get("candidate_knowledge_is_not_knowledge") is not True:
        errors.append("candidate_knowledge_is_not_knowledge must be True")

    if quarantine.get("promotion_requires_operator") is not True:
        errors.append("promotion_requires_operator must be True")

    if quarantine.get("model_cannot_self_promote") is not True:
        errors.append("model_cannot_self_promote must be True")

    if quarantine.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    if quarantine.get("operator_review_required") is not True:
        errors.append("operator_review_required must be True")

    if quarantine.get("no_auto_promotion") is not True:
        errors.append("no_auto_promotion must be True")

    # Check individual entries
    for i, entry in enumerate(quarantine.get("entries", [])):
        state = entry.get("state")
        if state not in QUARANTINE_STATES:
            errors.append(
                f"entry[{i}] has invalid state: {state}"
            )

        # Promoted entries must have been reviewed by operator
        if state == "promoted":
            if entry.get("reviewer") != "operator":
                errors.append(
                    f"entry[{i}] is promoted but reviewer is "
                    f"'{entry.get('reviewer')}', not 'operator'"
                )
            if entry.get("is_knowledge") is not True:
                errors.append(
                    f"entry[{i}] is promoted but is_knowledge is not True"
                )

        # Rejected entries must not be knowledge
        if state == "rejected":
            if entry.get("is_knowledge") is not False:
                errors.append(
                    f"entry[{i}] is rejected but is_knowledge is not False"
                )

    return errors
