"""P32 model routing schemas — bounded model selection, not authority."""

from __future__ import annotations

from hg_runtime.evaluation_harness.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    EvaluationHarnessBoundaryError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

VERDICT_GREEN_P32_0 = "GREEN_P32_0_MODEL_ROUTING_SCHEMAS"
VERDICT_RED_P32_0 = "RED_P32_0_MODEL_ROUTING_SCHEMAS_FAILED"
VERDICT_GREEN_P32_1 = "GREEN_P32_1_MODEL_REGISTRY_PREFLIGHT"
VERDICT_RED_P32_1 = "RED_P32_1_MODEL_REGISTRY_PREFLIGHT_FAILED"
VERDICT_GREEN_P32_2 = "GREEN_P32_2_ROUTE_DECISION_REFUSAL"
VERDICT_RED_P32_2 = "RED_P32_2_ROUTE_DECISION_REFUSAL_FAILED"
VERDICT_GREEN_P32_3 = "GREEN_P32_3_ROUTER_REPLAY_SOAK"
VERDICT_RED_P32_3 = "RED_P32_3_ROUTER_REPLAY_SOAK_FAILED"
VERDICT_GREEN_P32_CONSOLIDATION = "GREEN_P32_MODEL_ROUTING_CONSOLIDATION"
VERDICT_RED_P32_CONSOLIDATION = "RED_P32_MODEL_ROUTING_CONSOLIDATION_FAILED"

MODEL_ROLES = frozenset({
    "planner",
    "coder",
    "critic",
    "summarizer",
    "classifier",
})

ROUTING_MODES = frozenset({
    "fixture_only",
    "policy_only",
    "advisory_only",
})

PROVIDER_STATES = frozenset({
    "disabled",
    "fixture_only_local_only",
})

ROUTE_RESULT_STATES = frozenset({
    "ROUTED",
    "REFUSED",
    "DEFERRED",
    "NO_MODEL_AVAILABLE",
})

MODEL_TIERS = frozenset({
    "local_fixture",
    "local_small",
    "local_medium",
    "remote_disabled",
})

P32_INVARIANTS = (
    "model_selection_is_not_authority",
    "model_routing_is_not_permission",
    "local_model_output_is_not_truth",
    "provider_output_is_not_truth",
    "cheap_model_output_is_advisory",
    "expensive_model_output_is_advisory",
    "routing_recommendation_is_advisory",
    "no_model_may_self_authorize",
    "no_model_may_grant_tool_authority",
    "no_route_may_enable_providers_automatically",
    "no_route_may_read_hg_local",
    "no_route_may_print_secrets",
)

ROUTING_RECORD_TYPES = {
    "routing_policy_v1": {
        "required": ["schema", "routing_mode", "provider_state", "model_roles"],
    },
    "model_registry_entry_v1": {
        "required": ["schema", "model_id", "role", "tier", "provider_state"],
    },
    "route_request_v1": {
        "required": ["schema", "task_type", "requested_role"],
    },
    "route_decision_v1": {
        "required": ["schema", "request_id", "state", "selected_model_id"],
    },
    "route_refusal_v1": {
        "required": ["schema", "request_id", "reason"],
    },
}


class ModelRoutingBoundaryError(EvaluationHarnessBoundaryError):
    pass
