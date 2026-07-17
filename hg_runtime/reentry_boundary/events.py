"""REB planned RTC event selection helpers."""

from __future__ import annotations

from hg_core.reb_cluster.events import planned_reb_event_refs
from hg_runtime.reentry_boundary.types import ReEntryDecisionClass

_DECISION_EVENTS: dict[ReEntryDecisionClass, str] = {
    "allow_observe_only": "REB_REENTRY_ALLOWED_OBSERVE_ONLY",
    "allow_speak_with_disclosure": "REB_REENTRY_ALLOWED_WITH_DISCLOSURE",
    "allow_summary_only": "REB_REENTRY_ALLOWED_WITH_DISCLOSURE",
    "allow_local_reentry": "REB_REENTRY_ALLOWED_WITH_DISCLOSURE",
    "require_operator_review": "REB_REENTRY_REQUIRES_OPERATOR_REVIEW",
    "require_TIM_refresh": "REB_REENTRY_REQUIRES_TIM_REFRESH",
    "require_RET_review": "REB_REENTRY_REQUIRES_TIM_REFRESH",
    "require_SEC_review": "REB_REENTRY_REQUIRES_CNT_REVIEW",
    "require_CNT_review": "REB_REENTRY_REQUIRES_CNT_REVIEW",
    "require_MOR_review": "REB_REENTRY_REQUIRES_CNT_REVIEW",
    "require_TRB_CAL_review": "REB_REENTRY_REQUIRES_OPERATOR_REVIEW",
    "require_OBT_review": "REB_REENTRY_REQUIRES_OPERATOR_REVIEW",
    "require_authority_chain": "REB_REENTRY_DENIED",
    "deny_reentry": "REB_REENTRY_DENIED",
    "fail_closed": "REB_REENTRY_DENIED",
    "unknown_fail_closed": "REB_REENTRY_DENIED",
}

_ADVERSARIAL_EVENTS: dict[str, str] = {
    "stale_approval": "REB_STALE_APPROVAL_REFUSED",
    "stale_memory_as_current": "REB_STALE_MEMORY_REFUSED_AS_CURRENT",
    "checkpoint_authority": "REB_CHECKPOINT_AUTHORITY_REFUSED",
    "continuity_claim": "REB_CONTINUITY_CLAIM_REFUSED",
}


def decision_selection_event(decision: ReEntryDecisionClass) -> str:
    return _DECISION_EVENTS.get(decision, "REB_REENTRY_DENIED")


def adversarial_selection_event(signal: str) -> str:
    return _ADVERSARIAL_EVENTS.get(signal, "REB_SIGNAL_REFUSED")


__all__ = [
    "adversarial_selection_event",
    "decision_selection_event",
    "planned_reb_event_refs",
]
