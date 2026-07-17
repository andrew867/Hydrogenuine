"""Auto-approval policy — forbidden types and risk ceilings."""

from __future__ import annotations

from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.risk import AgentActionRiskClass, classify_action_risk
from hg_runtime.exciton_action_model.validation import can_be_auto_approval_candidate

FORBIDDEN_RULE_ACTION_TYPES: frozenset[str] = frozenset(
    {
        AgentActionType.SOCIAL_POST.value,
        AgentActionType.WEB_FORM_SUBMIT.value,
        AgentActionType.WEB_LOGIN.value,
        AgentActionType.WEB_UPLOAD.value,
        AgentActionType.WEB_POST_COMMENT.value,
        AgentActionType.WEB_PURCHASE.value,
        AgentActionType.WEB_ACCOUNT_CHANGE.value,
        AgentActionType.EMAIL_SEND.value,
        AgentActionType.SHELL_COMMAND.value,
        AgentActionType.SOURCE_PATCH.value,
        AgentActionType.MEMORY_MUTATION.value,
        AgentActionType.ANCHOR_PUSH.value,
        AgentActionType.ACCOUNT_ACTION.value,
        "oea",
        "ter",
        "srp",
        "approve_all",
        "*",
    }
)

ALLOWED_RULE_ACTION_TYPES: frozenset[str] = frozenset(
    {
        AgentActionType.STATUS_REFRESH.value,
        AgentActionType.PROOF_OPEN.value,
        AgentActionType.OPERATOR_NOTE.value,
        AgentActionType.SOCIAL_DRAFT.value,
        AgentActionType.WEB_READ_URL.value,
        AgentActionType.WEB_SEARCH.value,
        AgentActionType.WEB_FORM_FILL.value,
        AgentActionType.WEB_CLICK_LINK.value,
    }
)

MAX_RISK_ORDER = {
    AgentActionRiskClass.READ_ONLY: 0,
    AgentActionRiskClass.DRAFT_ONLY: 1,
    AgentActionRiskClass.EXTERNAL_READ: 2,
    AgentActionRiskClass.LOCAL_WRITE: 3,
    AgentActionRiskClass.EXTERNAL_WRITE: 4,
    AgentActionRiskClass.ACCOUNT_SENSITIVE: 5,
    AgentActionRiskClass.CREDENTIAL_SENSITIVE: 6,
    AgentActionRiskClass.FINANCIAL: 7,
    AgentActionRiskClass.PRIVILEGED_SYSTEM: 8,
    AgentActionRiskClass.FORBIDDEN: 9,
    AgentActionRiskClass.UNKNOWN: 10,
}


def is_forbidden_rule_action_type(action_type: str) -> bool:
    if action_type in FORBIDDEN_RULE_ACTION_TYPES:
        return True
    if action_type in ("*", "all", "approve_all"):
        return True
    try:
        at = AgentActionType(action_type)
        return not can_be_auto_approval_candidate(at)
    except ValueError:
        return True


def risk_within_ceiling(action_type: str, max_risk_class: str) -> bool:
    try:
        at = AgentActionType(action_type)
        actual = classify_action_risk(at)
        ceiling = AgentActionRiskClass(max_risk_class)
    except ValueError:
        return False
    return MAX_RISK_ORDER.get(actual, 99) <= MAX_RISK_ORDER.get(ceiling, 0)


def validate_rule_scope(action_type: str, allowed_surfaces: list[str]) -> list[str]:
    errors: list[str] = []
    if not action_type or action_type in ("*", "all"):
        errors.append("wildcard action_type forbidden")
    if is_forbidden_rule_action_type(action_type):
        errors.append(f"forbidden action_type: {action_type}")
    if not allowed_surfaces:
        errors.append("allowed_surfaces required")
    if "*" in allowed_surfaces and action_type not in ALLOWED_RULE_ACTION_TYPES:
        errors.append("wildcard surface only for read-only scoped rules")
    return errors


__all__ = [
    "ALLOWED_RULE_ACTION_TYPES",
    "FORBIDDEN_RULE_ACTION_TYPES",
    "is_forbidden_rule_action_type",
    "risk_within_ceiling",
    "validate_rule_scope",
]
