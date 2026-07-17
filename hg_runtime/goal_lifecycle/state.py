"""Goal state transitions, including STOP and PANIC handling.

State transitions are explicit and bounded. STOP moves a goal to STOPPED; PANIC
moves it to PANIC_HALTED, which is terminal -- a panic-halted goal must not
resume. Resume is refused under a panic state or a live PANIC signal.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle.schemas import (
    ACTIVE,
    ALLOWED_TRANSITIONS,
    GOAL_STATE_TRANSITION_SCHEMA,
    GOAL_STATES,
    PANIC_HALTED,
    STOPPED,
    GoalLifecycleError,
    neutral_flags,
    preempt_if_needed,
)


def _transition_record(goal_ref: str, frm: str, to: str, reason: str) -> dict[str, Any]:
    return {
        "schema": GOAL_STATE_TRANSITION_SCHEMA,
        "goal_ref": goal_ref,
        "from_state": frm,
        "to_state": to,
        "reason": reason,
        **neutral_flags(),
    }


def transition_goal(
    goal: Mapping[str, Any],
    to_state: str,
    *,
    reason: str = "",
    control: OperationControl | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply a bounded state transition. Returns (updated_goal, transition_record)."""
    # A live PANIC preempts any transition except the panic-halt itself.
    if to_state != PANIC_HALTED:
        preempt_if_needed(control, stop_blocks=False)
    if to_state not in GOAL_STATES:
        raise GoalLifecycleError(f"schema_violation:unknown_state:{to_state}")
    frm = str(goal.get("state"))
    if to_state not in ALLOWED_TRANSITIONS.get(frm, set()):
        raise GoalLifecycleError(f"illegal_goal_transition:{frm}->{to_state}")
    updated = dict(goal)
    updated["state"] = to_state
    return updated, _transition_record(str(goal.get("goal_id", "")), frm, to_state, reason)


def apply_stop(goal: Mapping[str, Any], *, reason: str = "operator_stop") -> tuple[dict[str, Any], dict[str, Any]]:
    """STOP transitions a goal to STOPPED."""
    frm = str(goal.get("state"))
    if STOPPED not in ALLOWED_TRANSITIONS.get(frm, set()):
        raise GoalLifecycleError(f"illegal_goal_transition:{frm}->{STOPPED}")
    updated = dict(goal)
    updated["state"] = STOPPED
    return updated, _transition_record(str(goal.get("goal_id", "")), frm, STOPPED, reason)


def apply_panic(goal: Mapping[str, Any], *, reason: str = "operator_panic") -> tuple[dict[str, Any], dict[str, Any]]:
    """PANIC halts a goal to PANIC_HALTED from any non-completed state."""
    frm = str(goal.get("state"))
    updated = dict(goal)
    updated["state"] = PANIC_HALTED
    return updated, _transition_record(str(goal.get("goal_id", "")), frm, PANIC_HALTED, reason)


def resume_goal(
    goal: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
    reason: str = "operator_resume",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resume a durable goal -- refused if it is panic-halted or PANIC is live."""
    preempt_if_needed(control, stop_blocks=False)
    if str(goal.get("state")) == PANIC_HALTED:
        raise GoalLifecycleError("durable_goal_resume_requires_non_panic_state")
    return transition_goal(goal, ACTIVE, reason=reason, control=control)


__all__ = ["apply_panic", "apply_stop", "resume_goal", "transition_goal"]
