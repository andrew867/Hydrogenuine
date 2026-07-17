"""Action risk classification for EXCITON UX Phase 3."""

from __future__ import annotations

from enum import Enum

from hg_runtime.exciton_action_model.action_types import AgentActionType


class AgentActionRiskClass(str, Enum):
    READ_ONLY = "read_only"
    DRAFT_ONLY = "draft_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL_READ = "external_read"
    EXTERNAL_WRITE = "external_write"
    ACCOUNT_SENSITIVE = "account_sensitive"
    CREDENTIAL_SENSITIVE = "credential_sensitive"
    FINANCIAL = "financial"
    PHYSICAL_WORLD = "physical_world"
    PRIVILEGED_SYSTEM = "privileged_system"
    FORBIDDEN = "forbidden"
    UNKNOWN = "unknown"


# Default risk per action type. Unknown types map to UNKNOWN (blocked).
DEFAULT_RISK_BY_ACTION: dict[AgentActionType, AgentActionRiskClass] = {
    AgentActionType.SOCIAL_POST: AgentActionRiskClass.EXTERNAL_WRITE,
    AgentActionType.SOCIAL_READ: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.SOCIAL_DRAFT: AgentActionRiskClass.DRAFT_ONLY,
    AgentActionType.WEB_READ_URL: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.WEB_SEARCH: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.WEB_CLICK_LINK: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.WEB_DOWNLOAD_FILE: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.WEB_FORM_FILL: AgentActionRiskClass.DRAFT_ONLY,
    AgentActionType.WEB_FORM_SUBMIT: AgentActionRiskClass.FORBIDDEN,
    AgentActionType.WEB_LOGIN: AgentActionRiskClass.CREDENTIAL_SENSITIVE,
    AgentActionType.WEB_UPLOAD: AgentActionRiskClass.EXTERNAL_WRITE,
    AgentActionType.WEB_POST_COMMENT: AgentActionRiskClass.EXTERNAL_WRITE,
    AgentActionType.WEB_PURCHASE: AgentActionRiskClass.FINANCIAL,
    AgentActionType.WEB_ACCOUNT_CHANGE: AgentActionRiskClass.ACCOUNT_SENSITIVE,
    AgentActionType.EMAIL_DRAFT: AgentActionRiskClass.DRAFT_ONLY,
    AgentActionType.EMAIL_SEND: AgentActionRiskClass.EXTERNAL_WRITE,
    AgentActionType.CALENDAR_CREATE: AgentActionRiskClass.DRAFT_ONLY,
    AgentActionType.FILE_WRITE: AgentActionRiskClass.LOCAL_WRITE,
    AgentActionType.MEMORY_MUTATION: AgentActionRiskClass.PRIVILEGED_SYSTEM,
    AgentActionType.SOURCE_PATCH: AgentActionRiskClass.PRIVILEGED_SYSTEM,
    AgentActionType.ANCHOR_PUSH: AgentActionRiskClass.PRIVILEGED_SYSTEM,
    AgentActionType.TOOL_EXECUTE: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.SHELL_COMMAND: AgentActionRiskClass.PRIVILEGED_SYSTEM,
    AgentActionType.ACCOUNT_ACTION: AgentActionRiskClass.ACCOUNT_SENSITIVE,
    AgentActionType.EXTERNAL_API_CALL: AgentActionRiskClass.EXTERNAL_READ,
    AgentActionType.PUBLICATION: AgentActionRiskClass.EXTERNAL_WRITE,
    AgentActionType.OPERATOR_NOTE: AgentActionRiskClass.DRAFT_ONLY,
    AgentActionType.PROOF_OPEN: AgentActionRiskClass.READ_ONLY,
    AgentActionType.STATUS_REFRESH: AgentActionRiskClass.READ_ONLY,
    AgentActionType.STOP_SOAK: AgentActionRiskClass.PRIVILEGED_SYSTEM,
    AgentActionType.PANIC_STOP: AgentActionRiskClass.PRIVILEGED_SYSTEM,
    AgentActionType.FINALIZE_SOAK: AgentActionRiskClass.PRIVILEGED_SYSTEM,
}

# Auto-approval ceiling: read_only and draft_only only.
AUTO_APPROVAL_RISK_CEILING: frozenset[AgentActionRiskClass] = frozenset(
    {
        AgentActionRiskClass.READ_ONLY,
        AgentActionRiskClass.DRAFT_ONLY,
    }
)

HIGH_RISK_CLASSES: frozenset[AgentActionRiskClass] = frozenset(
    {
        AgentActionRiskClass.ACCOUNT_SENSITIVE,
        AgentActionRiskClass.CREDENTIAL_SENSITIVE,
        AgentActionRiskClass.FINANCIAL,
        AgentActionRiskClass.PHYSICAL_WORLD,
        AgentActionRiskClass.PRIVILEGED_SYSTEM,
        AgentActionRiskClass.FORBIDDEN,
        AgentActionRiskClass.UNKNOWN,
        AgentActionRiskClass.EXTERNAL_WRITE,
        AgentActionRiskClass.LOCAL_WRITE,
    }
)


def classify_action_risk(action_type: AgentActionType) -> AgentActionRiskClass:
    return DEFAULT_RISK_BY_ACTION.get(action_type, AgentActionRiskClass.UNKNOWN)


__all__ = [
    "AUTO_APPROVAL_RISK_CEILING",
    "AgentActionRiskClass",
    "DEFAULT_RISK_BY_ACTION",
    "HIGH_RISK_CLASSES",
    "classify_action_risk",
]
