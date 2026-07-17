"""Route requests, route results, model-output records, and provider-failure handling.

A route binds a bounded goal work item to a model role under a privacy tier and a
safety policy. A route result selects a model and records why -- it is advisory and
never permission. A model output is authority-neutral. A provider health failure
routes to a recorded refusal, never a silent fallback to another provider.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.model_router.schemas import (
    MODEL_HEALTH_CHECK_SCHEMA,
    MODEL_OUTPUT_RECORD_SCHEMA,
    MODEL_ROUTE_REQUEST_SCHEMA,
    MODEL_ROUTE_RESULT_SCHEMA,
    PROVIDER_FAILURE_RECORD_SCHEMA,
    ModelRouterError,
    is_security_role,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)
from hg_runtime.model_router.privacy import check_privacy
from hg_runtime.model_router.roles import validate_role_binding
from hg_runtime.model_router.safety import enforce_safety


def create_route_request(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Validate a route request: it must bind a work item, role policy, privacy tier, and safety policy."""
    preempt_if_needed(control, stop_blocks=True)
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    if not str(data.get("work_item_ref", "")):
        raise ModelRouterError("route_requires_goal_work_item_ref")
    if not str(data.get("role_policy_ref", "")):
        raise ModelRouterError("route_requires_model_role_policy")
    if not str(data.get("privacy_tier_ref", "")):
        raise ModelRouterError("route_requires_privacy_tier")
    if not str(data.get("safety_policy_ref", "")):
        raise ModelRouterError("route_requires_safety_review_policy")
    require_fields(data, ("request_id", "role", "claim_boundary"))

    return {
        "schema": MODEL_ROUTE_REQUEST_SCHEMA,
        "request_id": data["request_id"],
        "work_item_ref": data["work_item_ref"],
        "role": str(data["role"]).strip().lower(),
        "role_policy_ref": data["role_policy_ref"],
        "privacy_tier_ref": data["privacy_tier_ref"],
        "safety_policy_ref": data["safety_policy_ref"],
        "skip_critic": bool(data.get("skip_critic", False)),
        "skip_security_review": bool(data.get("skip_security_review", False)),
        "claim_boundary": data["claim_boundary"],
        **neutral_flags(),
    }


def route_work_item(
    request: Mapping[str, Any],
    *,
    catalog_entry: Mapping[str, Any],
    role_policy: Mapping[str, Any],
    privacy_tier: Mapping[str, Any],
    safety_policy: Mapping[str, Any],
    provider: Mapping[str, Any],
    health: Mapping[str, Any] | None = None,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """Produce an advisory route result after role, privacy, and safety checks pass."""
    preempt_if_needed(control, stop_blocks=True)
    enforce_safety(request, safety_policy)
    check_privacy(privacy_tier, provider)
    binding = validate_role_binding(catalog_entry, role_policy)

    # A claimed-healthy route over an unhealthy provider is fake green.
    if health is not None and not health.get("healthy"):
        raise ModelRouterError("fake_green_rejected:provider_unhealthy")

    role = str(request.get("role"))
    security = is_security_role(role)
    return {
        "schema": MODEL_ROUTE_RESULT_SCHEMA,
        "request_id": request.get("request_id"),
        "work_item_ref": request.get("work_item_ref"),
        "selected_model_id": catalog_entry.get("model_id"),
        "selected_provider_id": provider.get("provider_id"),
        "role": role,
        "critic_only": bool(binding.get("critic_only")) or security,
        "workbench_execution_authority": False,
        "advisory_only": True,
        "grants_authority": False,
        "authorizes_tool": False,
        "claim_boundary": request.get("claim_boundary", "model_router_advisory_default"),
        **neutral_flags(),
    }


def record_model_output(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Record a model output as authority-neutral evidence -- never a grant of authority."""
    require_fields(payload, ("output_id", "route_result_ref"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": MODEL_OUTPUT_RECORD_SCHEMA,
        "output_id": data["output_id"],
        "route_result_ref": data["route_result_ref"],
        "content_ref": data.get("content_ref"),
        "is_authority": False,
        "authorizes_tool": False,
        "advisory_only": True,
        **neutral_flags(),
    }


def record_health_check(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("check_id", "provider_id", "healthy"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": MODEL_HEALTH_CHECK_SCHEMA,
        "check_id": data["check_id"],
        "provider_id": data["provider_id"],
        "model_id": data.get("model_id"),
        "healthy": bool(data["healthy"]),
        **neutral_flags(),
    }


def handle_provider_failure(health: Mapping[str, Any], *, request_id: str) -> dict[str, Any]:
    """On an unhealthy provider, refuse and record -- never silently fall back.

    Returns a provider-failure record only when the provider is healthy (nothing to
    do); an unhealthy provider raises so the caller cannot silently re-route.
    """
    if not health.get("healthy"):
        raise ModelRouterError("provider_health_failure_refuses_no_silent_fallback")
    return {
        "schema": PROVIDER_FAILURE_RECORD_SCHEMA,
        "request_id": request_id,
        "provider_id": health.get("provider_id"),
        "healthy": True,
        "silent_fallback": False,
        **neutral_flags(),
    }


def build_provider_failure_record(health: Mapping[str, Any], *, request_id: str) -> dict[str, Any]:
    """Record an unhealthy provider as a refusal (no silent fallback)."""
    return {
        "schema": PROVIDER_FAILURE_RECORD_SCHEMA,
        "request_id": request_id,
        "provider_id": health.get("provider_id"),
        "healthy": False,
        "action": "refused",
        "silent_fallback": False,
        **neutral_flags(),
    }


__all__ = [
    "build_provider_failure_record",
    "create_route_request",
    "handle_provider_failure",
    "record_health_check",
    "record_model_output",
    "route_work_item",
]
