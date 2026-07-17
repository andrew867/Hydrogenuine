"""Broker integration — admit create_external_action_candidate only."""

from __future__ import annotations

from typing import Any

from hg_runtime.capability_broker.action_registry import get_action, is_forbidden_action, is_known_action
from hg_runtime.external_write_authority.action_candidate import ExternalActionCandidate, create_candidate


def broker_may_create_candidate(action_id: str) -> bool:
    if is_forbidden_action(action_id):
        return False
    if action_id != "create_external_action_candidate":
        return False
    action = get_action(action_id)
    return action is not None and is_known_action(action_id) and not action.external_side_effect


def create_candidate_from_broker_admission(
    *,
    run_id: str,
    platform: str,
    action_type: str,
    content: str,
    scope: str,
    capability_decision_ref: str,
    **refs: Any,
) -> ExternalActionCandidate:
    if not broker_may_create_candidate("create_external_action_candidate"):
        raise PermissionError("broker did not admit create_external_action_candidate")
    if "model_output:" in capability_decision_ref and "broker:" not in capability_decision_ref:
        raise PermissionError("model output cannot authorize candidate creation")
    return create_candidate(
        run_id=run_id,
        platform=platform,
        action_type=action_type,
        content=content,
        scope=scope,
        provider_receipt_ref=refs.get("provider_receipt_ref"),
        **refs,
    )
