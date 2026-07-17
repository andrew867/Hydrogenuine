"""Candidate tasks, allowed task classes, and selected work items.

A candidate task is a *proposal*, never execution. Before a candidate may become a
selected work item it must match an allowed task class, and the work item itself
must reference existing authority (GPP/HAL/UEAK) and carry a receipt plan. The
lifecycle never grants that authority -- it only refuses to proceed without it.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle.schemas import (
    ALLOWED_TASK_CLASS_SCHEMA,
    CANDIDATE_TASK_SCHEMA,
    SELECTED_WORK_ITEM_SCHEMA,
    GoalLifecycleError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def create_candidate_task(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Propose a candidate task. A candidate is never execution."""
    require_fields(payload, ("task_id", "goal_ref", "description", "proposed_task_class", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    return {
        "schema": CANDIDATE_TASK_SCHEMA,
        "task_id": data["task_id"],
        "goal_ref": data["goal_ref"],
        "description": data["description"],
        "proposed_task_class": data["proposed_task_class"],
        "status": "candidate",
        "is_execution": False,
        "execution_allowed": False,
        "class_validated": False,
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }


def define_allowed_task_class(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("task_class_id", "description"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": ALLOWED_TASK_CLASS_SCHEMA,
        "task_class_id": data["task_class_id"],
        "description": data["description"],
        "requires_authority_refs": True,
        "requires_receipt_plan": True,
        **neutral_flags(),
    }


def validate_allowed_task_class(
    candidate: Mapping[str, Any],
    allowed_classes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Mark a candidate task class-validated, or refuse if its class is not allowed."""
    allowed_ids = {str(c.get("task_class_id")) for c in allowed_classes}
    if str(candidate.get("proposed_task_class")) not in allowed_ids:
        raise GoalLifecycleError("candidate_task_requires_allowed_class")
    validated = dict(candidate)
    validated["class_validated"] = True
    validated["allowed_class_ref"] = str(candidate.get("proposed_task_class"))
    return validated


def candidate_task_from_failed_gate(gate_result: Mapping[str, Any], *, goal_ref: str, task_id: str) -> dict[str, Any]:
    """A failed gate generates a remediation candidate task -- not a silent pass."""
    failures = list(gate_result.get("failures", []))
    if gate_result.get("ok") and not failures:
        raise GoalLifecycleError("failed_gate_required_to_generate_candidate")
    return create_candidate_task(
        {
            "task_id": task_id,
            "goal_ref": goal_ref,
            "description": f"remediate failed gate: {gate_result.get('verdict', 'unknown')}",
            "proposed_task_class": "remediation",
            "source_gate_failures": failures,
            "claim_boundary": "goal_lifecycle_advisory_default",
        }
    )


def select_work_item(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Select a work item from a class-validated candidate.

    Requires authority refs (references to existing GPP/HAL/UEAK authority, never
    minted here) and a receipt plan. PANIC blocks selection entirely. A live work
    item additionally requires permit refs.
    """
    preempt_if_needed(control, stop_blocks=True)
    require_fields(
        payload,
        ("work_item_id", "candidate_task_ref", "allowed_class_ref", "authority_refs", "receipt_plan", "claim_boundary"),
    )
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    if not str(data.get("allowed_class_ref", "")):
        raise GoalLifecycleError("candidate_task_requires_allowed_class_before_execution")
    authority_refs = as_list(data, "authority_refs")
    if not authority_refs:
        raise GoalLifecycleError("selected_work_item_requires_authority_reference")
    receipt_plan = data.get("receipt_plan")
    if not receipt_plan:
        raise GoalLifecycleError("selected_work_item_requires_receipt_plan")
    if data.get("live"):
        if not as_list(data, "permit_refs"):
            raise GoalLifecycleError("dry_live_boundary_enforced:live_requires_permit")

    return {
        "schema": SELECTED_WORK_ITEM_SCHEMA,
        "work_item_id": data["work_item_id"],
        "candidate_task_ref": data["candidate_task_ref"],
        "allowed_class_ref": data["allowed_class_ref"],
        "authority_refs": authority_refs,
        "receipt_plan": receipt_plan,
        "permit_refs": as_list(data, "permit_refs"),
        "mode": "live" if data.get("live") else "dry",
        "authority_minted_here": False,
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }


__all__ = [
    "candidate_task_from_failed_gate",
    "create_candidate_task",
    "define_allowed_task_class",
    "select_work_item",
    "validate_allowed_task_class",
]
