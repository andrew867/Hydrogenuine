"""P32 route decision — selects model for task (advisory, not authority)."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import assert_neutral
from hg_runtime.model_routing.schemas import (
    MODEL_ROLES,
    ROUTE_RESULT_STATES,
    ModelRoutingBoundaryError,
)


def create_route_request(
    *,
    request_id: str,
    task_type: str,
    requested_role: str,
) -> dict[str, Any]:
    if requested_role not in MODEL_ROLES:
        raise ModelRoutingBoundaryError(f"invalid requested_role: {requested_role}")

    return {
        "schema": "route_request_v1",
        "request_id": request_id,
        "task_type": task_type,
        "requested_role": requested_role,
    }


def route_to_model(
    request: dict[str, Any],
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    requested_role = request["requested_role"]
    candidates = [e for e in registry if e["role"] == requested_role]

    if not candidates:
        return _refuse(request, f"no model available for role: {requested_role}")

    selected = candidates[0]

    record = {
        "schema": "route_decision_v1",
        "request_id": request["request_id"],
        "state": "ROUTED",
        "selected_model_id": selected["model_id"],
        "selected_role": selected["role"],
        "selected_tier": selected["tier"],
        "routing_is_advisory": True,
        "model_selection_is_not_authority": True,
        "model_output_is_not_truth": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record, "decision_hash")


def _refuse(request: dict[str, Any], reason: str) -> dict[str, Any]:
    record = {
        "schema": "route_refusal_v1",
        "request_id": request["request_id"],
        "reason": reason,
        "state": "REFUSED",
        "selected_model_id": None,
        "routing_is_advisory": True,
        "model_selection_is_not_authority": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record, "refusal_hash")


def refuse_authority_claim(request: dict[str, Any]) -> dict[str, Any]:
    return _refuse(request, "model_selection_is_not_authority")
