"""WILL policy — veto, expiry, authority conversion rejection."""

from __future__ import annotations

from typing import Any

from hg_runtime.will_module.envelope import WillEnvelope
from hg_runtime.will_module.schema import ConsentPosture, PersistenceBudgetClass, VetoState, WillDecisionEffect, WillSource


class WillBoundaryViolation(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def reject_authority_mutation(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("permission_granted") is True or payload.get("authority_created") is True:
        return {
            "schema": "will-authority-conversion-rejected",
            "rejected": True,
            "reason": "WILL cannot grant permission or authority",
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
    return {"schema": "will-authority-check-ok", "rejected": False}


def check_veto(envelope: WillEnvelope, *, domain: str) -> WillDecisionEffect:
    if envelope.veto_state == VetoState.HARD_STOP:
        return WillDecisionEffect.REFUSE
    if envelope.veto_state == VetoState.NEVER and domain in envelope.disallowed_domains:
        return WillDecisionEffect.REFUSE
    if envelope.veto_state == VetoState.SOFT_STOP:
        return WillDecisionEffect.PAUSE
    if envelope.veto_state == VetoState.ASK_LATER:
        return WillDecisionEffect.ASK_OPERATOR
    return WillDecisionEffect.NO_EFFECT


def check_expiry(envelope: WillEnvelope, *, now: str | None = None) -> WillDecisionEffect:
    if envelope.is_expired(now=now):
        return WillDecisionEffect.REQUEST_REAFFIRMATION
    if envelope.reaffirmation_required:
        return WillDecisionEffect.REQUEST_REAFFIRMATION
    return WillDecisionEffect.NO_EFFECT


def inferred_consent_allowed(source: WillSource, posture: ConsentPosture) -> bool:
    if source == WillSource.INFERRED_FROM_CONTEXT and posture == ConsentPosture.EXPLICIT_YES:
        return False
    return True


def persistence_within_bounds(envelope: WillEnvelope, *, attempts: int, wallclock_s: int, tokens: int) -> bool:
    budget = envelope.persistence_budget
    if budget.budget_class == PersistenceBudgetClass.EXPIRED:
        return False
    if attempts > budget.max_attempts:
        return False
    if wallclock_s > budget.max_wallclock_s:
        return False
    if tokens > budget.max_tokens:
        return False
    return True


def will_may_contextualize_tool(envelope: WillEnvelope) -> bool:
    """WILL may explain a tool request; it may not approve."""
    effect = check_veto(envelope, domain="tool_request")
    if effect in {WillDecisionEffect.REFUSE, WillDecisionEffect.PAUSE}:
        return False
    if check_expiry(envelope) == WillDecisionEffect.REQUEST_REAFFIRMATION:
        return False
    return True


def attempt_will_approval(capability_id: str) -> dict[str, Any]:
    """Explicit rejection path when WILL is misused to approve."""
    return reject_authority_mutation({"permission_granted": True, "capability_id": capability_id})


__all__ = [
    "WillBoundaryViolation",
    "attempt_will_approval",
    "check_expiry",
    "check_veto",
    "inferred_consent_allowed",
    "persistence_within_bounds",
    "reject_authority_mutation",
    "will_may_contextualize_tool",
]
