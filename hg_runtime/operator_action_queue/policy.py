"""Transition policy and execution eligibility for operator queue."""

from __future__ import annotations

from hg_runtime.exciton_action_model.action_types import PHASE3_FORBIDDEN_ACTION_TYPES, AgentActionType
from hg_runtime.exciton_action_model.status import AgentActionStatus, is_executable_status
from hg_runtime.exciton_action_model.validation import is_action_type_executable_in_phase3
from hg_runtime.operator_action_queue.schema import OperatorQueueItem

TERMINAL_STATUSES: frozenset[AgentActionStatus] = frozenset(
    {
        AgentActionStatus.DENIED,
        AgentActionStatus.EXPIRED,
        AgentActionStatus.CANCELLED,
        AgentActionStatus.EXECUTED,
        AgentActionStatus.FAILED,
        AgentActionStatus.INVALID,
        AgentActionStatus.BLOCKED,
    }
)

ALLOWED_TRANSITIONS: dict[AgentActionStatus, frozenset[AgentActionStatus]] = {
    AgentActionStatus.QUEUED: frozenset(
        {
            AgentActionStatus.APPROVED,
            AgentActionStatus.DENIED,
            AgentActionStatus.EXPIRED,
            AgentActionStatus.CANCELLED,
            AgentActionStatus.BLOCKED,
            AgentActionStatus.INVALID,
        }
    ),
    AgentActionStatus.APPROVED: frozenset(
        {
            AgentActionStatus.EXECUTED,
            AgentActionStatus.EXPIRED,
            AgentActionStatus.CANCELLED,
            AgentActionStatus.FAILED,
            AgentActionStatus.BLOCKED,
        }
    ),
    AgentActionStatus.DRY_RUN_ONLY: frozenset({AgentActionStatus.EXECUTED}),
}


def may_transition(current: AgentActionStatus, new: AgentActionStatus) -> bool:
    if current == new:
        return False
    if current in TERMINAL_STATUSES:
        return False
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    return new in allowed


def is_approval_blocked_status(status: AgentActionStatus) -> bool:
    return status != AgentActionStatus.QUEUED


def item_may_be_approved(item: OperatorQueueItem, *, stop_panic: bool) -> tuple[bool, str]:
    if stop_panic:
        return False, "stop_or_panic_active"
    if is_approval_blocked_status(item.status):
        return False, f"cannot_approve_from_{item.status.value}"
    if item.source_agent == "agent0" and item.action_request.operator_decision_ref:
        op = item.action_request.operator_decision_ref.operator_ref
        if op == "agent0":
            return False, "self_approval_forbidden"
    action_type = item.action_request.action_type
    if action_type in PHASE3_FORBIDDEN_ACTION_TYPES:
        return False, "forbidden_action_type_in_phase3"
    return True, "ok"


def item_execution_eligible(
    item: OperatorQueueItem,
    *,
    stop_panic: bool,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Eligible for external executor — queue does not execute."""
    if stop_panic:
        return False, "stop_or_panic_active"
    if item.status == AgentActionStatus.DRY_RUN_ONLY:
        if not dry_run:
            return False, "dry_run_only_no_live"
        return True, "dry_run_eligible"
    if not is_executable_status(item.status):
        return False, f"not_approved:{item.status.value}"
    action_type = item.action_request.action_type
    if not is_action_type_executable_in_phase3(action_type):
        return False, "not_executable_in_phase3"
    return True, "eligible"


def item_may_mark_executed(
    item: OperatorQueueItem,
    *,
    dry_run: bool = False,
) -> tuple[bool, str]:
    if item.status == AgentActionStatus.EXECUTED:
        return False, "already_executed"
    if item.status == AgentActionStatus.DRY_RUN_ONLY:
        if dry_run:
            return True, "ok"
        return False, "dry_run_receipt_required"
    if item.status != AgentActionStatus.APPROVED:
        return False, f"cannot_execute_from_{item.status.value}"
    return True, "ok"


def high_risk_not_executable_in_phase3(action_type: AgentActionType) -> bool:
    return action_type in {
        AgentActionType.WEB_FORM_SUBMIT,
        AgentActionType.SHELL_COMMAND,
        AgentActionType.SOURCE_PATCH,
        AgentActionType.MEMORY_MUTATION,
        AgentActionType.WEB_LOGIN,
        AgentActionType.WEB_PURCHASE,
    }


__all__ = [
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STATUSES",
    "high_risk_not_executable_in_phase3",
    "is_approval_blocked_status",
    "item_execution_eligible",
    "item_may_be_approved",
    "item_may_mark_executed",
    "may_transition",
]
