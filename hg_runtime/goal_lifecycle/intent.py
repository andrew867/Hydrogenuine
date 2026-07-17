"""Operator intent intake with ambiguity detection.

Intent is where operator words enter the lifecycle. Ambiguous or under-scoped
intent is recorded but routed to ask-operator -- it never becomes active work on
its own.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.goal_lifecycle.schemas import (
    OPERATOR_INTENT_SCHEMA,
    GoalLifecycleError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
    statement_is_ambiguous,
)


def intake_operator_intent(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Record operator intent; flag ambiguity and route to ask-operator if unclear."""
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("intent_id", "statement", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    scope = data.get("scope")
    has_scope = bool(scope) and (not isinstance(scope, (list, dict)) or len(scope) > 0)
    has_success_criteria = bool(data.get("success_criteria"))
    ambiguous = (
        bool(data.get("ambiguous"))
        or not has_scope
        or not has_success_criteria
        or statement_is_ambiguous(str(data.get("statement", "")))
    )

    record = {
        "schema": OPERATOR_INTENT_SCHEMA,
        "intent_id": data["intent_id"],
        "statement": data["statement"],
        "scope": scope,
        "success_criteria": list(data.get("success_criteria", [])),
        "ambiguous": ambiguous,
        "scoped": has_scope and not ambiguous,
        "requires_ask_operator": ambiguous,
        "status": "ask_operator" if ambiguous else "scoped",
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }
    return record


def is_ambiguous(intent: Mapping[str, Any]) -> bool:
    return bool(intent.get("ambiguous"))


def require_scoped_intent(intent: Mapping[str, Any]) -> None:
    """Refuse to proceed from an intent that is ambiguous or has no scope.

    A genuinely vague statement is refused as ambiguous; an otherwise-clear
    statement that merely lacks a scope is refused with the scope-specific reason.
    """
    if not isinstance(intent, Mapping) or intent.get("schema") != OPERATOR_INTENT_SCHEMA:
        raise GoalLifecycleError("schema_violation:missing:operator_intent")
    if statement_is_ambiguous(str(intent.get("statement", ""))):
        raise GoalLifecycleError("ambiguous_intent_cannot_create_active_goal")
    if not intent.get("scope"):
        raise GoalLifecycleError("operator_intent_requires_scope")
    if intent.get("ambiguous"):
        raise GoalLifecycleError("ambiguous_intent_cannot_create_active_goal")


__all__ = ["intake_operator_intent", "is_ambiguous", "require_scoped_intent"]
