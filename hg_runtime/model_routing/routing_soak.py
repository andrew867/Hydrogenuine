"""P32 routing soak — replays routing decisions for determinism."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import stable_hash
from hg_runtime.evaluation_harness.schemas import assert_neutral
from hg_runtime.model_routing.model_registry import builtin_registry
from hg_runtime.model_routing.route_decision import create_route_request, route_to_model
from hg_runtime.model_routing.schemas import MODEL_ROLES


def run_routing_soak(*, iterations: int = 5) -> dict[str, Any]:
    registry = builtin_registry()

    iteration_hashes = []
    for _ in range(iterations):
        decisions = []
        for i, role in enumerate(sorted(MODEL_ROLES)):
            req = create_route_request(
                request_id=f"soak-{i}",
                task_type="soak_task",
                requested_role=role,
            )
            dec = route_to_model(req, registry)
            decisions.append(dec)
        h = stable_hash({"decisions": decisions})
        iteration_hashes.append(h)

    unique = len(set(iteration_hashes))

    result = {
        "schema": "routing_soak_v1",
        "iterations": iterations,
        "iteration_hashes": iteration_hashes,
        "unique_hashes": unique,
        "deterministic": unique == 1,
        "soak_is_not_authority": True,
        "routing_recommendation_is_advisory": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(result)
    return result
