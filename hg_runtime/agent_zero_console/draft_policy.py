"""Draft reply policy — drafts cannot send."""

from __future__ import annotations

from hg_runtime.agent_zero_console.schema import RequestIntent

FORBIDDEN_DRAFT_ACTIONS = frozenset({"send", "publish", "submit", "approve_all"})


def draft_may_send() -> bool:
    return False


def operator_edit_invalidates_approval() -> bool:
    return True


def draft_intent_allowed(intent: RequestIntent) -> bool:
    return intent in {
        RequestIntent.DRAFT_ONLY,
        RequestIntent.CREATE_MESSAGE_REPLY_DRAFT,
        RequestIntent.ANSWER_ONLY,
    }


__all__ = [
    "FORBIDDEN_DRAFT_ACTIONS",
    "draft_intent_allowed",
    "draft_may_send",
    "operator_edit_invalidates_approval",
]
