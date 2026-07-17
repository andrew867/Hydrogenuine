"""Phase 33 multi-model-router and residency schemas and authority guardrails.

Routing is not authority. Loading a model is not authority. A model output is not
authority. Local inference is authority-neutral. A cheaper/faster model cannot
bypass critic/security review; a larger model cannot widen scope; a local model
cannot bypass proof gates; a model route cannot authorize tools or live actions.
Every record in this phase may *choose a role, record why, or request residency*
-- never grant authority, authorize a tool, or create a live side effect.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

MODEL_PROVIDER_SCHEMA = "model_provider_v1"
MODEL_CATALOG_ENTRY_SCHEMA = "model_catalog_entry_v1"
MODEL_ROLE_POLICY_SCHEMA = "model_role_policy_v1"
MODEL_ROUTE_REQUEST_SCHEMA = "model_route_request_v1"
MODEL_ROUTE_RESULT_SCHEMA = "model_route_result_v1"
MODEL_PRIVACY_TIER_SCHEMA = "model_privacy_tier_v1"
MODEL_SAFETY_REVIEW_POLICY_SCHEMA = "model_safety_review_policy_v1"
MODEL_RESIDENCY_POLICY_SCHEMA = "model_residency_policy_v1"
MODEL_LOAD_REQUEST_SCHEMA = "model_load_request_v1"
MODEL_UNLOAD_REQUEST_SCHEMA = "model_unload_request_v1"
LOADED_MODEL_INSTANCE_SCHEMA = "loaded_model_instance_v1"
MODEL_HEALTH_CHECK_SCHEMA = "model_health_check_v1"
MODEL_RESIDENCY_RECEIPT_SCHEMA = "model_residency_receipt_v1"
MODEL_ROUTING_RECEIPT_SCHEMA = "model_routing_receipt_v1"
PROVIDER_FAILURE_RECORD_SCHEMA = "provider_failure_record_v1"
MODEL_OUTPUT_RECORD_SCHEMA = "model_output_record_v1"

ROUTER_CLAIM_BOUNDARY = "model_router_advisory_default"

# Model roles the router may select.
MODEL_ROLES = {
    "planner",
    "coder",
    "critic",
    "security_reviewer",
    "math_verifier",
    "summarizer",
    "cheap_local_model",
    "large_local_model",
    "document_writer",
}

# Roles that are critic-only by default: they review and advise, and never carry
# workbench execution authority.
SECURITY_ROLES = {"security_reviewer", "offensive_security", "offensive_security_reviewer"}

# Privacy tiers; sensitive/secret may never leave for an external provider.
PRIVACY_TIERS = {"public", "internal", "sensitive", "secret"}
EXTERNAL_FORBIDDEN_TIERS = {"sensitive", "secret"}

# Provider kinds. Only fake_local is fully usable in tests; lmstudio/openvino are
# dry-run contracts; vllm refuses by default.
PROVIDER_KINDS = {"fake_local", "lmstudio", "openvino", "vllm", "external_network"}
LOCAL_PROVIDER_KINDS = {"fake_local", "lmstudio", "openvino"}
EXTERNAL_PROVIDER_KINDS = {"external_network"}
REFUSING_PROVIDER_KINDS = {"vllm"}

GREEN_LIKE = {"green", "ok", "success", "succeeded", "routed", "loaded", "healthy", "passed"}

# Keys that, if truthy anywhere in a payload, are a hard refusal.
_AUTHORITY_KEYS = {
    "authority_created",
    "permission_granted",
    "tool_authorized",
    "live_side_effects_created",
    "grants_authority",
    "grant_authority",
    "authorizes_tool",
    "authorize_tool",
    "authorizes_live_action",
    "permits_live_action",
    "widens_scope",
    "widen_authority",
    "widens_authority",
    "override_gpp",
    "override_hal",
    "override_ueak",
    "override_oea",
    "routing_grants_authority",
    "route_authorizes_tool",
    "load_grants_authority",
    "load_authorizes_execution",
    "model_output_is_authority",
    "output_grants_authority",
    "output_authorizes_tool",
    "auto_execute",
}
# Keys that try to bypass critic / safety review via the router. (``skip_critic`` /
# ``skip_security_review`` are NOT here: they are normal route fields evaluated
# against the safety policy by ``enforce_safety`` -- a request may legitimately
# carry skip_critic=False, and a truthy one is refused with a policy-aware message.)
_SAFETY_BYPASS_KEYS = {
    "bypass_safety",
    "bypass_critic",
    "override_critic",
    "bypass_security_review",
    "override_security_review",
    "disable_safety_review",
    "router_selects_to_bypass_safety",
}
# Keys that smuggle "X is permission" semantics.
_AS_PERMISSION_KEYS = {
    "route_as_permission",
    "load_as_permission",
    "residency_as_permission",
    "model_as_permission",
    "output_as_permission",
    "provider_as_permission",
}

_FORBIDDEN_CLAIM_BOUNDARIES = {
    "self_authorizing",
    "authority_grant",
    "permit",
    "route_is_authority",
    "model_is_authority",
    "output_is_authority",
}

_CREDENTIAL_MARKERS = (
    ".env",
    "secret",
    "credential",
    "id_rsa",
    ".pem",
    ".key",
    "password",
    "api_key",
    "apikey",
    ".netrc",
    "token",
    "bearer",
)
_NETWORK_PREFIXES = ("http://", "https://", "ftp://", "ws://", "wss://")


class ModelRouterError(ValueError):
    """Phase 33 validation or operation refusal."""


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ModelRouterError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ModelRouterError(f"schema_violation:{key}_must_be_list")
    return value


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    """Refuse any attempt to grant authority, bypass safety, or treat a route as permission."""
    for key, value in payload.items():
        if value:
            if key in _SAFETY_BYPASS_KEYS:
                raise ModelRouterError(f"safety_bypass_rejected:{key}")
            if key in _AS_PERMISSION_KEYS:
                raise ModelRouterError(f"route_is_not_permission:{key}")
            if key in _AUTHORITY_KEYS:
                raise ModelRouterError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def reject_forbidden_claim_boundary(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_boundary") in _FORBIDDEN_CLAIM_BOUNDARIES:
        raise ModelRouterError("self_authorization_rejected:routing_is_advisory_only")


def is_security_role(role: str) -> bool:
    return str(role).strip().lower() in SECURITY_ROLES


def locator_is_network(locator: str) -> bool:
    return str(locator).lower().startswith(_NETWORK_PREFIXES)


def locator_is_credential(locator: str) -> bool:
    low = str(locator).lower()
    return any(marker in low for marker in _CREDENTIAL_MARKERS)


def neutral_flags() -> dict[str, bool]:
    """The authority-neutral footer stamped on every emitted record."""
    return {
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "widens_authority": False,
        "live_side_effects_created": False,
        "routing_treated_as_authority": False,
        "model_output_treated_as_authority": False,
    }


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise ModelRouterError(reason)


__all__ = [
    "EXTERNAL_FORBIDDEN_TIERS",
    "EXTERNAL_PROVIDER_KINDS",
    "GREEN_LIKE",
    "LOADED_MODEL_INSTANCE_SCHEMA",
    "LOCAL_PROVIDER_KINDS",
    "MODEL_CATALOG_ENTRY_SCHEMA",
    "MODEL_HEALTH_CHECK_SCHEMA",
    "MODEL_LOAD_REQUEST_SCHEMA",
    "MODEL_OUTPUT_RECORD_SCHEMA",
    "MODEL_PRIVACY_TIER_SCHEMA",
    "MODEL_PROVIDER_SCHEMA",
    "MODEL_RESIDENCY_POLICY_SCHEMA",
    "MODEL_RESIDENCY_RECEIPT_SCHEMA",
    "MODEL_ROLE_POLICY_SCHEMA",
    "MODEL_ROLES",
    "MODEL_ROUTE_REQUEST_SCHEMA",
    "MODEL_ROUTE_RESULT_SCHEMA",
    "MODEL_ROUTING_RECEIPT_SCHEMA",
    "MODEL_SAFETY_REVIEW_POLICY_SCHEMA",
    "MODEL_UNLOAD_REQUEST_SCHEMA",
    "PRIVACY_TIERS",
    "PROVIDER_FAILURE_RECORD_SCHEMA",
    "PROVIDER_KINDS",
    "REFUSING_PROVIDER_KINDS",
    "ROUTER_CLAIM_BOUNDARY",
    "SECURITY_ROLES",
    "ModelRouterError",
    "as_list",
    "is_security_role",
    "locator_is_credential",
    "locator_is_network",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "reject_forbidden_claim_boundary",
    "require_fields",
]
