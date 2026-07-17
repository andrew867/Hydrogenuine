"""Goal and subgoal records, plus advisory evidence attachments.

A goal is created only from scoped, unambiguous intent. It is a durable record of
what the operator wants -- never a grant of authority to pursue it. Generalization
results, workbench capabilities, and memory references attach as advisory evidence
only; none of them is permission.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle.schemas import (
    ACTIVE,
    ADVISORY_ATTACHMENT_SCHEMA,
    GOAL_RECORD_SCHEMA,
    SUBGOAL_RECORD_SCHEMA,
    GoalLifecycleError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)
from hg_runtime.goal_lifecycle.intent import require_scoped_intent

_ADVISORY_KINDS = {
    "generalization_result",
    "workbench_capability",
    "memory_reference",
    "skill_transfer",
    "domain_readiness",
}


def create_goal(
    intent: Mapping[str, Any],
    payload: Mapping[str, Any] | None = None,
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Create an active goal from scoped intent. Refuses ambiguity and any authority grant."""
    preempt_if_needed(control, stop_blocks=True)
    require_scoped_intent(intent)
    data = dict(payload or {})
    require_fields(data, ("goal_id",))
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    return {
        "schema": GOAL_RECORD_SCHEMA,
        "goal_id": data["goal_id"],
        "intent_ref": intent["intent_id"],
        "scope": intent.get("scope"),
        "title": data.get("title", str(intent.get("statement", ""))[:120]),
        "state": ACTIVE,
        "subgoal_refs": list(data.get("subgoal_refs", [])),
        "advisory_attachments": [],
        "claim_boundary": data.get("claim_boundary", "goal_lifecycle_advisory_default"),
        **neutral_flags(),
    }


def create_subgoal(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Create a subgoal. A subgoal cannot exist without a parent goal."""
    if not str(payload.get("parent_goal_ref", "")):
        raise GoalLifecycleError("subgoal_requires_parent_goal")
    require_fields(payload, ("subgoal_id", "parent_goal_ref", "description"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    return {
        "schema": SUBGOAL_RECORD_SCHEMA,
        "subgoal_id": data["subgoal_id"],
        "parent_goal_ref": data["parent_goal_ref"],
        "description": data["description"],
        "state": ACTIVE,
        "claim_boundary": data.get("claim_boundary", "goal_lifecycle_advisory_default"),
        **neutral_flags(),
    }


def attach_advisory_evidence(
    *,
    goal_ref: str,
    kind: str,
    refs: list[str],
    as_permission: bool = False,
) -> dict[str, Any]:
    """Attach generalization/workbench/memory evidence to a goal as advisory only.

    Asking for the evidence to be treated as permission is refused: a
    generalization result, a workbench capability, and a memory reference are all
    evidence about what is possible, never a grant of authority to do it.
    """
    if kind not in _ADVISORY_KINDS:
        raise GoalLifecycleError(f"schema_violation:unknown_advisory_kind:{kind}")
    if as_permission:
        raise GoalLifecycleError(f"{kind}_is_not_permission")
    return {
        "schema": ADVISORY_ATTACHMENT_SCHEMA,
        "goal_ref": goal_ref,
        "kind": kind,
        "refs": list(refs),
        "advisory_only": True,
        "used_as_permission": False,
        **neutral_flags(),
    }


__all__ = ["attach_advisory_evidence", "create_goal", "create_subgoal"]
