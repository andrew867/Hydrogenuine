"""Task selection policy enforcement."""

from __future__ import annotations

from hg_runtime.task_selection.schema import (
    BLOCKED_TASK_TYPES,
    TaskRefusalReason,
    load_task_selection_policy,
)


def evaluate_candidate_policy(
    *,
    task_type: str,
    objective_scope: str,
    scope_allowed: bool,
    requires_external_action: bool,
    model_suggested: bool = False,
    live_read_command: bool = False,
) -> tuple[bool, TaskRefusalReason | None]:
    policy = load_task_selection_policy()
    if task_type in BLOCKED_TASK_TYPES:
        return False, TaskRefusalReason.BLOCKED_TASK_TYPE
    if not scope_allowed:
        return False, TaskRefusalReason.OUT_OF_SCOPE
    if requires_external_action and not policy.get("external_side_effects_allowed", False):
        return False, TaskRefusalReason.EXTERNAL_ACTION_NOT_ALLOWED
    if task_type == "publish_live" and not policy.get("direct_publish_allowed", False):
        return False, TaskRefusalReason.BLOCKED_TASK_TYPE
    if task_type == "send_live" and not policy.get("direct_send_allowed", False):
        return False, TaskRefusalReason.BLOCKED_TASK_TYPE
    if task_type in ("reply_live", "comment_live"):
        return False, TaskRefusalReason.BLOCKED_TASK_TYPE
    if task_type == "browse_live" and not policy.get("browser_side_effects_allowed", False):
        return False, TaskRefusalReason.BLOCKED_TASK_TYPE
    if task_type == "hardware_action" and not policy.get("hardware_actuation_allowed", False):
        return False, TaskRefusalReason.BLOCKED_TASK_TYPE
    if task_type in ("self_modify_code", "self_merge", "disable_safety"):
        return False, TaskRefusalReason.AUTHORITY_EXPANSION
    if model_suggested and not policy.get("zero_may_grant_authority", False):
        # model may suggest but cannot authorize — still allow if otherwise valid
        pass
    if live_read_command:
        return False, TaskRefusalReason.LIVE_CONTENT_NOT_COMMAND
    if task_type == "prepare_external_action_candidate":
        if not policy.get("prepare_external_action_candidate_allowed", False):
            return False, TaskRefusalReason.EXTERNAL_ACTION_NOT_ALLOWED
    return True, None


def policy_status() -> dict:
    return load_task_selection_policy()
