"""Ask-operator records.

When intent is ambiguous, the lifecycle does not guess -- it records a question
for the operator. An ambiguous intent cannot advance to active work without an
ask-operator record.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.goal_lifecycle.schemas import (
    ASK_OPERATOR_RECORD_SCHEMA,
    GoalLifecycleError,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def ask_operator(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("question_id", "intent_ref", "question", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": ASK_OPERATOR_RECORD_SCHEMA,
        "question_id": data["question_id"],
        "intent_ref": data["intent_ref"],
        "question": data["question"],
        "options": list(data.get("options", [])),
        "resolved": False,
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }


def require_ask_operator(intent: Mapping[str, Any], ask_record: Mapping[str, Any] | None) -> dict[str, Any]:
    """Refuse to advance an ambiguous intent without an ask-operator record."""
    if intent.get("ambiguous"):
        if not isinstance(ask_record, Mapping) or ask_record.get("schema") != ASK_OPERATOR_RECORD_SCHEMA:
            raise GoalLifecycleError("ask_operator_record_required_for_ambiguity")
    return dict(ask_record) if isinstance(ask_record, Mapping) else {}


__all__ = ["ask_operator", "require_ask_operator"]
