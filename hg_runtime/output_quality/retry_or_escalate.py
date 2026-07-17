"""Retry and escalation policy for output quality decisions.

Does NOT actually call models. Produces routing decisions only.
promotion_allowed is ALWAYS False. Model output is not truth.
"""

from __future__ import annotations


def create_retry_decision(
    *,
    seed_id: str,
    task_id: str,
    model_id: str,
    reason: str,
    stop_panic: bool = False,
) -> dict:
    """Create a retry decision record.

    If stop_panic is True, decision is "blocked" and operator_review_required is True.
    """
    if stop_panic:
        return {
            "decision": "blocked",
            "model_id": model_id,
            "seed_id": seed_id,
            "task_id": task_id,
            "reason": reason,
            "promotion_allowed": False,
            "operator_review_required": True,
            "grants_authority": False,
            "model_output_treated_as_truth": False,
        }

    return {
        "decision": "retry",
        "model_id": model_id,
        "seed_id": seed_id,
        "task_id": task_id,
        "reason": reason,
        "promotion_allowed": False,
        "operator_review_required": False,
        "grants_authority": False,
        "model_output_treated_as_truth": False,
    }


def create_escalation_decision(
    *,
    seed_id: str,
    task_id: str,
    from_model: str,
    to_model: str,
    reason: str,
    stop_panic: bool = False,
) -> dict:
    """Create an escalation decision record.

    If stop_panic is True, decision is "blocked" and operator_review_required is True.
    """
    if stop_panic:
        return {
            "decision": "blocked",
            "from_model": from_model,
            "to_model": to_model,
            "seed_id": seed_id,
            "task_id": task_id,
            "reason": reason,
            "promotion_allowed": False,
            "operator_review_required": True,
            "grants_authority": False,
            "model_output_treated_as_truth": False,
        }

    return {
        "decision": "escalate",
        "from_model": from_model,
        "to_model": to_model,
        "seed_id": seed_id,
        "task_id": task_id,
        "reason": reason,
        "promotion_allowed": False,
        "operator_review_required": False,
        "grants_authority": False,
        "model_output_treated_as_truth": False,
    }


def validate_retry_decision(decision: dict) -> list[str]:
    """Validate a retry/escalation decision. Returns list of errors (empty = valid)."""
    errors = []

    if decision.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")
    if decision.get("grants_authority") is not False:
        errors.append("grants_authority must be False")
    if decision.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    d = decision.get("decision")
    if d not in {"retry", "escalate", "blocked"}:
        errors.append(f"unknown decision: {d}")

    if not decision.get("seed_id") and not decision.get("task_id"):
        errors.append("missing both seed_id and task_id")

    return errors
