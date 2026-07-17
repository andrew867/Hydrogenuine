"""Phase 32 Long-Horizon Goal Lifecycle.

Turns operator intent into durable goals, subgoals, candidate tasks, selected work
items, receipts, outcomes, and replanning across sessions. It is a lifecycle
manager, not an authority layer: it never self-authorizes work, continues through
STOP/PANIC, executes live actions, bypasses GPP/HAL/UEAK/OEA, or treats a goal,
plan, generalization result, or workbench capability as permission.
"""

from __future__ import annotations

from hg_runtime.goal_lifecycle.schemas import (
    GoalLifecycleError,
    neutral_flags,
    reject_authority_payload,
)
from hg_runtime.goal_lifecycle.intent import (
    intake_operator_intent,
    is_ambiguous,
    require_scoped_intent,
)
from hg_runtime.goal_lifecycle.goals import (
    attach_advisory_evidence,
    create_goal,
    create_subgoal,
)
from hg_runtime.goal_lifecycle.tasks import (
    candidate_task_from_failed_gate,
    create_candidate_task,
    define_allowed_task_class,
    select_work_item,
    validate_allowed_task_class,
)
from hg_runtime.goal_lifecycle.state import (
    apply_panic,
    apply_stop,
    resume_goal,
    transition_goal,
)
from hg_runtime.goal_lifecycle.receipts import (
    bind_receipt,
    build_lifecycle_receipt,
    record_failure,
    record_outcome,
)
from hg_runtime.goal_lifecycle.replanning import create_replan
from hg_runtime.goal_lifecycle.operator_questions import ask_operator, require_ask_operator
from hg_runtime.goal_lifecycle.replay import (
    GoalLifecycleLog,
    GoalRecord,
    GoalReplayResult,
)
from hg_runtime.goal_lifecycle.gate import (
    evaluate_phase32_gate,
    validate_phase32_proof_bundle,
)

__all__ = [
    "GoalLifecycleError",
    "GoalLifecycleLog",
    "GoalRecord",
    "GoalReplayResult",
    "apply_panic",
    "apply_stop",
    "ask_operator",
    "attach_advisory_evidence",
    "bind_receipt",
    "build_lifecycle_receipt",
    "candidate_task_from_failed_gate",
    "create_candidate_task",
    "create_goal",
    "create_replan",
    "create_subgoal",
    "define_allowed_task_class",
    "evaluate_phase32_gate",
    "intake_operator_intent",
    "is_ambiguous",
    "neutral_flags",
    "record_failure",
    "record_outcome",
    "reject_authority_payload",
    "require_ask_operator",
    "require_scoped_intent",
    "resume_goal",
    "select_work_item",
    "transition_goal",
    "validate_allowed_task_class",
    "validate_phase32_proof_bundle",
]
