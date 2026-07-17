"""Agent action type universe for EXCITON UX Phase 3."""

from __future__ import annotations

from enum import Enum


class AgentActionType(str, Enum):
    SOCIAL_POST = "social_post"
    SOCIAL_READ = "social_read"
    SOCIAL_DRAFT = "social_draft"
    WEB_READ_URL = "web_read_url"
    WEB_SEARCH = "web_search"
    WEB_CLICK_LINK = "web_click_link"
    WEB_DOWNLOAD_FILE = "web_download_file"
    WEB_FORM_FILL = "web_form_fill"
    WEB_FORM_SUBMIT = "web_form_submit"
    WEB_LOGIN = "web_login"
    WEB_UPLOAD = "web_upload"
    WEB_POST_COMMENT = "web_post_comment"
    WEB_PURCHASE = "web_purchase"
    WEB_ACCOUNT_CHANGE = "web_account_change"
    EMAIL_DRAFT = "email_draft"
    EMAIL_SEND = "email_send"
    CALENDAR_CREATE = "calendar_create"
    FILE_WRITE = "file_write"
    MEMORY_MUTATION = "memory_mutation"
    SOURCE_PATCH = "source_patch"
    ANCHOR_PUSH = "anchor_push"
    TOOL_EXECUTE = "tool_execute"
    SHELL_COMMAND = "shell_command"
    ACCOUNT_ACTION = "account_action"
    EXTERNAL_API_CALL = "external_api_call"
    PUBLICATION = "publication"
    OPERATOR_NOTE = "operator_note"
    PROOF_OPEN = "proof_open"
    STATUS_REFRESH = "status_refresh"
    STOP_SOAK = "stop_soak"
    PANIC_STOP = "panic_stop"
    FINALIZE_SOAK = "finalize_soak"


ALL_ACTION_TYPES: frozenset[AgentActionType] = frozenset(AgentActionType)

# Forbidden in Phase 3 — representable but not executable.
PHASE3_FORBIDDEN_ACTION_TYPES: frozenset[AgentActionType] = frozenset(
    {
        AgentActionType.WEB_FORM_SUBMIT,
        AgentActionType.WEB_LOGIN,
        AgentActionType.WEB_PURCHASE,
        AgentActionType.WEB_ACCOUNT_CHANGE,
        AgentActionType.WEB_UPLOAD,
        AgentActionType.EMAIL_SEND,
        AgentActionType.MEMORY_MUTATION,
        AgentActionType.SOURCE_PATCH,
        AgentActionType.SHELL_COMMAND,
        AgentActionType.ANCHOR_PUSH,
        AgentActionType.ACCOUNT_ACTION,
    }
)

# Control actions — not authority grants.
CONTROL_ACTION_TYPES: frozenset[AgentActionType] = frozenset(
    {
        AgentActionType.STOP_SOAK,
        AgentActionType.PANIC_STOP,
        AgentActionType.FINALIZE_SOAK,
    }
)

__all__ = [
    "ALL_ACTION_TYPES",
    "AgentActionType",
    "CONTROL_ACTION_TYPES",
    "PHASE3_FORBIDDEN_ACTION_TYPES",
]
