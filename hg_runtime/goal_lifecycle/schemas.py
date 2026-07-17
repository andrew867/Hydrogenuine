"""Phase 32 long-horizon goal-lifecycle schemas and authority guardrails.

A lifecycle manager, not an authority layer. Every record in this phase may
*record intent, define a goal, propose a candidate task, select a work item that
references existing authority, bind a receipt, or replan* -- it may never grant
authority, widen authority, authorize a tool, create a live side effect, continue
through STOP/PANIC, or treat a goal/plan/evidence/capability as permission.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

OPERATOR_INTENT_SCHEMA = "operator_intent_v1"
GOAL_RECORD_SCHEMA = "goal_record_v1"
SUBGOAL_RECORD_SCHEMA = "subgoal_record_v1"
GOAL_STATE_TRANSITION_SCHEMA = "goal_state_transition_v1"
CANDIDATE_TASK_SCHEMA = "candidate_task_v1"
ALLOWED_TASK_CLASS_SCHEMA = "allowed_task_class_v1"
SELECTED_WORK_ITEM_SCHEMA = "selected_work_item_v1"
GOAL_RECEIPT_BINDING_SCHEMA = "goal_receipt_binding_v1"
GOAL_OUTCOME_RECORD_SCHEMA = "goal_outcome_record_v1"
GOAL_FAILURE_RECORD_SCHEMA = "goal_failure_record_v1"
REPLAN_RECORD_SCHEMA = "replan_record_v1"
ASK_OPERATOR_RECORD_SCHEMA = "ask_operator_record_v1"
GOAL_LIFECYCLE_RECEIPT_SCHEMA = "goal_lifecycle_receipt_v1"
ADVISORY_ATTACHMENT_SCHEMA = "goal_advisory_attachment_v1"

GOAL_CLAIM_BOUNDARY = "goal_lifecycle_advisory_default"

# Goal lifecycle states.
DRAFT = "DRAFT"
ACTIVE = "ACTIVE"
BLOCKED = "BLOCKED"
ASK_OPERATOR = "ASK_OPERATOR"
REPLANNING = "REPLANNING"
STOPPED = "STOPPED"
PANIC_HALTED = "PANIC_HALTED"
COMPLETED = "COMPLETED"
FAILED = "FAILED"

GOAL_STATES = {
    DRAFT,
    ACTIVE,
    BLOCKED,
    ASK_OPERATOR,
    REPLANNING,
    STOPPED,
    PANIC_HALTED,
    COMPLETED,
    FAILED,
}

# Terminal states cannot transition onward (PANIC_HALTED is terminal by design:
# a panic-halted goal must not silently resume).
TERMINAL_STATES = {PANIC_HALTED, COMPLETED}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    DRAFT: {ACTIVE, ASK_OPERATOR, STOPPED, PANIC_HALTED},
    ACTIVE: {BLOCKED, REPLANNING, ASK_OPERATOR, COMPLETED, FAILED, STOPPED, PANIC_HALTED},
    BLOCKED: {ACTIVE, REPLANNING, FAILED, STOPPED, PANIC_HALTED},
    ASK_OPERATOR: {ACTIVE, FAILED, STOPPED, PANIC_HALTED},
    REPLANNING: {ACTIVE, FAILED, STOPPED, PANIC_HALTED},
    STOPPED: {ACTIVE, PANIC_HALTED},
    PANIC_HALTED: set(),
    COMPLETED: set(),
    FAILED: {REPLANNING, STOPPED, PANIC_HALTED},
}

GREEN_LIKE = {"completed", "success", "succeeded", "green", "passed", "done"}

# Substrings that mark an operator statement as ambiguous / under-scoped.
_AMBIGUITY_MARKERS = (
    "something",
    "figure out",
    "whatever",
    "and more",
    "etc",
    "somehow",
    "as needed",
    "do the right thing",
    "tbd",
)

# Keys that, if truthy anywhere in a payload, are a hard refusal.
_AUTHORITY_KEYS = {
    "authority_created",
    "permission_granted",
    "tool_authorized",
    "live_side_effects_created",
    "grants_authority",
    "grant_authority",
    "authorizes_tool",
    "authorize_tool",
    "authorizes_task_class",
    "authorizes_live_action",
    "permits_live_action",
    "widens_scope",
    "widen_authority",
    "widens_authority",
    "override_gpp",
    "override_hal",
    "override_ueak",
    "override_oea",
    "bypass_gpp",
    "bypass_hal",
    "bypass_ueak",
    "self_authorize",
    "self_authorized",
    "auto_execute",
    "auto_select",
}
# Keys that smuggle "X is permission" semantics.
_AS_PERMISSION_KEYS = {
    "goal_as_permission",
    "plan_as_permission",
    "generalization_as_permission",
    "evidence_as_permission",
    "workbench_as_permission",
    "capability_as_permission",
    "memory_as_permission",
}

_FORBIDDEN_CLAIM_BOUNDARIES = {
    "self_authorizing",
    "authority_grant",
    "permit",
    "goal_is_authority",
    "plan_is_authority",
    "evidence_is_authority",
}


class GoalLifecycleError(ValueError):
    """Phase 32 validation or operation refusal."""


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise GoalLifecycleError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise GoalLifecycleError(f"schema_violation:{key}_must_be_list")
    return value


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    """Refuse any attempt to grant/widen authority or treat a goal as permission."""
    for key, value in payload.items():
        if value:
            if key in _AS_PERMISSION_KEYS:
                raise GoalLifecycleError(f"goal_is_not_permission:{key}")
            if key in _AUTHORITY_KEYS:
                raise GoalLifecycleError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def reject_forbidden_claim_boundary(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_boundary") in _FORBIDDEN_CLAIM_BOUNDARIES:
        raise GoalLifecycleError("self_authorization_rejected:goal_is_intent_only")


def statement_is_ambiguous(statement: str) -> bool:
    low = str(statement).strip().lower()
    if not low:
        return True
    return any(marker in low for marker in _AMBIGUITY_MARKERS)


def neutral_flags() -> dict[str, bool]:
    """The authority-neutral footer stamped on every emitted record."""
    return {
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "widens_authority": False,
        "live_side_effects_created": False,
        "goal_treated_as_permission": False,
        "plan_treated_as_permission": False,
    }


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise GoalLifecycleError(reason)


__all__ = [
    "ACTIVE",
    "ALLOWED_TASK_CLASS_SCHEMA",
    "ALLOWED_TRANSITIONS",
    "ASK_OPERATOR",
    "ASK_OPERATOR_RECORD_SCHEMA",
    "ADVISORY_ATTACHMENT_SCHEMA",
    "BLOCKED",
    "CANDIDATE_TASK_SCHEMA",
    "COMPLETED",
    "DRAFT",
    "FAILED",
    "GOAL_CLAIM_BOUNDARY",
    "GOAL_FAILURE_RECORD_SCHEMA",
    "GOAL_LIFECYCLE_RECEIPT_SCHEMA",
    "GOAL_OUTCOME_RECORD_SCHEMA",
    "GOAL_RECEIPT_BINDING_SCHEMA",
    "GOAL_RECORD_SCHEMA",
    "GOAL_STATES",
    "GOAL_STATE_TRANSITION_SCHEMA",
    "GREEN_LIKE",
    "GoalLifecycleError",
    "OPERATOR_INTENT_SCHEMA",
    "PANIC_HALTED",
    "REPLANNING",
    "REPLAN_RECORD_SCHEMA",
    "SELECTED_WORK_ITEM_SCHEMA",
    "STOPPED",
    "SUBGOAL_RECORD_SCHEMA",
    "TERMINAL_STATES",
    "as_list",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "reject_forbidden_claim_boundary",
    "require_fields",
    "statement_is_ambiguous",
]
