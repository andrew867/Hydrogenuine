"""Goal receipt bindings, outcomes, and failure records.

Outcomes and failures are first-class and preserved. A green outcome cannot be
recorded without receipts, and cannot be recorded over a failed bound gate. A
failure record preserves its failed receipt refs so replanning cannot quietly
erase the history.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle.schemas import (
    GOAL_FAILURE_RECORD_SCHEMA,
    GOAL_LIFECYCLE_RECEIPT_SCHEMA,
    GOAL_OUTCOME_RECORD_SCHEMA,
    GOAL_RECEIPT_BINDING_SCHEMA,
    GREEN_LIKE,
    GoalLifecycleError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def bind_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("goal_ref", "receipt_ref", "kind"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": GOAL_RECEIPT_BINDING_SCHEMA,
        "goal_ref": data["goal_ref"],
        "receipt_ref": data["receipt_ref"],
        "kind": data["kind"],
        "preserved": True,
        **neutral_flags(),
    }


def record_outcome(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Record a goal outcome. A green outcome demands receipts and a clean gate set."""
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("outcome_id", "goal_ref", "status", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    status = str(data["status"]).strip().lower()
    receipt_refs = as_list(data, "receipt_refs")
    gate_results = as_list(data, "gate_results")

    if status in GREEN_LIKE:
        failed = [g for g in gate_results if isinstance(g, Mapping) and not g.get("ok", g.get("passed"))]
        if failed:
            raise GoalLifecycleError("fake_green_rejected:failed_gate_present")
        if not receipt_refs:
            raise GoalLifecycleError("missing_receipt_blocks_success")

    return {
        "schema": GOAL_OUTCOME_RECORD_SCHEMA,
        "outcome_id": data["outcome_id"],
        "goal_ref": data["goal_ref"],
        "status": status,
        "receipt_refs": receipt_refs,
        "gate_results": gate_results,
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }


def record_failure(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Record a failure, preserving the failed receipt refs."""
    require_fields(payload, ("failure_id", "goal_ref", "failure_reason"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": GOAL_FAILURE_RECORD_SCHEMA,
        "failure_id": data["failure_id"],
        "goal_ref": data["goal_ref"],
        "failure_reason": data["failure_reason"],
        "receipt_refs": as_list(data, "receipt_refs"),
        "preserved": True,
        "hidden": False,
        **neutral_flags(),
    }


def build_lifecycle_receipt(
    *,
    goal_ref: str,
    status: str,
    receipt_refs: list[str],
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if str(status).lower() in GREEN_LIKE and not receipt_refs:
        raise GoalLifecycleError("missing_receipt_blocks_success")
    receipt = {
        "schema": GOAL_LIFECYCLE_RECEIPT_SCHEMA,
        "goal_ref": goal_ref,
        "status": status,
        "receipt_refs": list(receipt_refs),
        "summary": dict(summary or {}),
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


__all__ = ["bind_receipt", "build_lifecycle_receipt", "record_failure", "record_outcome"]
