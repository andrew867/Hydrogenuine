"""EXCITON Phase 3 control matrix — every button has handler or disabled reason."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

APPROVAL_MODES = frozenset(
    {
        "READ_DRAFT_ONLY",
        "QUEUE_REVIEW_REQUIRED",
        "APPROVED_ONLY_PUBLISH",
        "PUBLISH_DISABLED",
        "EMERGENCY_STOP",
    }
)

FORBIDDEN_CONTROL_IDS: frozenset[str] = frozenset(
    {
        "APPROVE_ALL",
        "DIRECT_PUBLISH",
        "DIRECT_WEB_SUBMIT",
        "DIRECT_LOGIN",
        "DIRECT_PURCHASE",
        "DIRECT_SHELL",
        "DIRECT_MEMORY_MUTATION",
        "DIRECT_SOURCE_MUTATION",
        "DIRECT_OEA_TER_SRP",
        "DISPLAY_CREDENTIALS",
        "ENABLE_LIVE_MIC",
        "ENABLE_PLAYBACK_DEFAULT",
        "publish_social",
        "approve_all",
        "direct_publish",
    }
)


@dataclass
class ControlMatrixEntry:
    control_id: str
    label: str
    handler: str | None
    decision: str
    disabled_reason: str | None = None
    forbidden: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id,
            "label": self.label,
            "handler": self.handler,
            "decision": self.decision,
            "disabled_reason": self.disabled_reason,
            "forbidden": self.forbidden,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


CONTROL_MATRIX: dict[str, ControlMatrixEntry] = {
    "REFRESH_STATUS": ControlMatrixEntry("REFRESH_STATUS", "Refresh status", "refresh_status", "ALLOW_READ_ONLY"),
    "OPEN_PROOF": ControlMatrixEntry("OPEN_PROOF", "Open proof", "open_proof", "ALLOW_READ_ONLY"),
    "COPY_SAFE_SUMMARY": ControlMatrixEntry("COPY_SAFE_SUMMARY", "Copy summary", "copy_safe_summary", "ALLOW_READ_ONLY"),
    "ADD_OPERATOR_NOTE": ControlMatrixEntry("ADD_OPERATOR_NOTE", "Add note", "add_operator_note", "ALLOW_DRAFT_ONLY"),
    "REFRESH_SOCIAL_STATUS": ControlMatrixEntry("REFRESH_SOCIAL_STATUS", "Refresh social status", "refresh_social_status", "ALLOW_READ_ONLY"),
    "GENERATE_SOCIAL_DRAFT": ControlMatrixEntry("GENERATE_SOCIAL_DRAFT", "Generate social draft", "generate_social_draft", "ALLOW_DRAFT_ONLY"),
    "QUEUE_SOCIAL_DRAFT": ControlMatrixEntry("QUEUE_SOCIAL_DRAFT", "Queue social draft", "queue_social_draft", "QUEUE_FOR_OPERATOR"),
    "APPROVE_SOCIAL_PUBLISH": ControlMatrixEntry("APPROVE_SOCIAL_PUBLISH", "Approve one queued item", "approve_social_publish", "QUEUE_FOR_OPERATOR"),
    "APPROVE_ACTION_ITEM": ControlMatrixEntry("APPROVE_ACTION_ITEM", "Approve item", "approve_queue_item", "QUEUE_FOR_OPERATOR"),
    "DENY_ACTION_ITEM": ControlMatrixEntry("DENY_ACTION_ITEM", "Deny item", "deny_queue_item", "QUEUE_FOR_OPERATOR"),
    "EXPIRE_ACTION_ITEM": ControlMatrixEntry("EXPIRE_ACTION_ITEM", "Expire item", "expire_queue_item", "QUEUE_FOR_OPERATOR"),
    "PAUSE_PUBLISH": ControlMatrixEntry("PAUSE_PUBLISH", "Pause publish", "pause_publish", "QUEUE_FOR_OPERATOR"),
    "RESUME_APPROVED_ONLY": ControlMatrixEntry("RESUME_APPROVED_ONLY", "Resume approved-only", "resume_approved_only", "QUEUE_FOR_OPERATOR"),
    "CHANGE_APPROVAL_MODE": ControlMatrixEntry("CHANGE_APPROVAL_MODE", "Change approval mode", "change_approval_mode", "QUEUE_FOR_OPERATOR"),
    "CREATE_AUTO_APPROVAL_RULE": ControlMatrixEntry("CREATE_AUTO_APPROVAL_RULE", "Create rule", "create_auto_rule", "QUEUE_FOR_OPERATOR"),
    "REVOKE_AUTO_APPROVAL_RULE": ControlMatrixEntry("REVOKE_AUTO_APPROVAL_RULE", "Revoke rule", "revoke_auto_rule", "QUEUE_FOR_OPERATOR"),
    "ENQUEUE_WEB_READ": ControlMatrixEntry("ENQUEUE_WEB_READ", "Enqueue web read", "enqueue_web_read", "QUEUE_FOR_OPERATOR"),
    "ENQUEUE_WEB_CLICK": ControlMatrixEntry("ENQUEUE_WEB_CLICK", "Enqueue web click", "enqueue_web_click", "QUEUE_FOR_OPERATOR"),
    "ENQUEUE_WEB_DOWNLOAD": ControlMatrixEntry("ENQUEUE_WEB_DOWNLOAD", "Enqueue download", "enqueue_web_download", "QUEUE_FOR_OPERATOR"),
    "STOP_AGENT": ControlMatrixEntry("STOP_AGENT", "Stop (graceful)", "stop_agent", "FULL_STOP"),
    "STOP_SOAK": ControlMatrixEntry("STOP_SOAK", "Stop soak", "stop_soak", "FULL_STOP"),
    "PANIC_STOP": ControlMatrixEntry("PANIC_STOP", "Panic stop", "panic_stop", "FULL_STOP"),
    "FINALIZE_SOAK": ControlMatrixEntry("FINALIZE_SOAK", "Finalize soak", "finalize_soak", "QUEUE_FOR_OPERATOR"),
    "TOGGLE_POLLING_LOCAL_UI_ONLY": ControlMatrixEntry("TOGGLE_POLLING_LOCAL_UI_ONLY", "Toggle polling", "toggle_polling", "ALLOW_READ_ONLY"),
    "APPROVE_ALL": ControlMatrixEntry("APPROVE_ALL", "Approve all", None, "DENY", "batch approval forbidden", forbidden=True),
    "DIRECT_PUBLISH": ControlMatrixEntry("DIRECT_PUBLISH", "Direct publish", None, "DENY", "direct publish forbidden", forbidden=True),
    "DIRECT_WEB_SUBMIT": ControlMatrixEntry("DIRECT_WEB_SUBMIT", "Web submit", None, "DENY", "form submit forbidden", forbidden=True),
    "DIRECT_LOGIN": ControlMatrixEntry("DIRECT_LOGIN", "Login", None, "DENY", "login forbidden", forbidden=True),
    "DIRECT_PURCHASE": ControlMatrixEntry("DIRECT_PURCHASE", "Purchase", None, "DENY", "purchase forbidden", forbidden=True),
}


def get_matrix() -> list[dict[str, Any]]:
    return [e.to_payload() for e in CONTROL_MATRIX.values()]


def get_entry(control_id: str) -> ControlMatrixEntry | None:
    return CONTROL_MATRIX.get(control_id) or CONTROL_MATRIX.get(control_id.upper())


__all__ = ["APPROVAL_MODES", "CONTROL_MATRIX", "ControlMatrixEntry", "FORBIDDEN_CONTROL_IDS", "get_entry", "get_matrix"]
