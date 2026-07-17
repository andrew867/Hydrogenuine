"""Safety-review policy and enforcement.

A safety policy says a work item requires a critic and/or a security review. The
router may not select a model to bypass that: a cheap/fast model cannot override the
critic, and no route may carry a safety-bypass flag.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.model_router.schemas import (
    MODEL_SAFETY_REVIEW_POLICY_SCHEMA,
    ModelRouterError,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def define_safety_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("policy_id",))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": MODEL_SAFETY_REVIEW_POLICY_SCHEMA,
        "policy_id": data["policy_id"],
        "requires_critic": bool(data.get("requires_critic", True)),
        "requires_security_review": bool(data.get("requires_security_review", False)),
        **neutral_flags(),
    }


def enforce_safety(route_request: Mapping[str, Any], safety_policy: Mapping[str, Any]) -> None:
    """Refuse a route that tries to bypass a required critic or security review.

    ``reject_authority_payload`` already refuses explicit bypass flags; this adds the
    policy-aware check that a route cannot opt out of a critic the policy requires.
    """
    reject_authority_payload(dict(route_request))
    if safety_policy.get("requires_critic") and route_request.get("skip_critic"):
        raise ModelRouterError("cheap_model_cannot_override_critic")
    if safety_policy.get("requires_security_review") and route_request.get("skip_security_review"):
        raise ModelRouterError("security_review_cannot_be_skipped")
    if route_request.get("router_selects_to_bypass_safety"):
        raise ModelRouterError("router_cannot_select_model_to_bypass_safety")


__all__ = ["define_safety_policy", "enforce_safety"]
