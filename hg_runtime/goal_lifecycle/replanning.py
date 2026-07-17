"""Replan records.

Replanning revises the approach to a goal after a failure. It must carry the prior
failure history forward; it may never erase failed receipts or discard the failure
record. A replan that tries to forget is refused.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle.schemas import (
    REPLAN_RECORD_SCHEMA,
    GoalLifecycleError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)

_ERASE_KEYS = ("erase_receipts", "discard_failures", "drop_failure_history", "forget_failures", "clear_receipts")


def create_replan(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Create a replan record that preserves the prior failure history."""
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("replan_id", "goal_ref", "prior_failure_refs", "new_plan", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    for key in _ERASE_KEYS:
        if data.get(key):
            raise GoalLifecycleError("replan_cannot_erase_receipts")

    prior_failures = as_list(data, "prior_failure_refs")
    if not prior_failures:
        raise GoalLifecycleError("replan_must_preserve_failure_history")

    return {
        "schema": REPLAN_RECORD_SCHEMA,
        "replan_id": data["replan_id"],
        "goal_ref": data["goal_ref"],
        "prior_failure_refs": prior_failures,
        "preserved_receipt_refs": as_list(data, "preserved_receipt_refs"),
        "new_plan": data["new_plan"],
        "failure_history_preserved": True,
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }


__all__ = ["create_replan"]
