"""Model role policies and role-binding validation.

A role policy says which model families may serve a role and whether the role
requires safety review. Security/offensive roles are critic-only by default and
carry no workbench execution authority -- a model may advise on security, never act
with security authority. A model may only serve a role its catalog entry declares
and a policy permits.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.model_router.schemas import (
    MODEL_ROLE_POLICY_SCHEMA,
    MODEL_ROLES,
    ModelRouterError,
    as_list,
    is_security_role,
    neutral_flags,
    reject_authority_payload,
    require_fields,
)


def define_role_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("role", "allowed_families"))
    data = dict(payload)
    reject_authority_payload(data)
    role = str(data["role"]).strip().lower()
    security = is_security_role(role)
    return {
        "schema": MODEL_ROLE_POLICY_SCHEMA,
        "role": role,
        "allowed_families": as_list(data, "allowed_families"),
        "requires_safety_review": bool(data.get("requires_safety_review", security)),
        # Security/offensive roles are critic-only and never hold execution authority.
        "critic_only": True if security else bool(data.get("critic_only", False)),
        "workbench_execution_authority": False if security else bool(data.get("workbench_execution_authority", False)),
        **neutral_flags(),
    }


def validate_role_binding(
    catalog_entry: Mapping[str, Any],
    role_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a model to a role, refusing role mismatch or a family the policy disallows."""
    role = str(role_policy.get("role"))
    declared = {str(r).strip().lower() for r in as_list(catalog_entry, "declared_roles")}
    if role not in declared:
        raise ModelRouterError("model_role_mismatch_rejected")
    allowed_families = {str(f) for f in as_list(role_policy, "allowed_families")}
    if allowed_families and str(catalog_entry.get("family")) not in allowed_families:
        raise ModelRouterError("model_role_mismatch_rejected:family_not_allowed")
    return {
        "model_id": catalog_entry.get("model_id"),
        "role": role,
        "critic_only": bool(role_policy.get("critic_only")),
        "workbench_execution_authority": bool(role_policy.get("workbench_execution_authority")),
        "bound": True,
    }


def require_security_role_is_critic_only(role_policy: Mapping[str, Any]) -> None:
    """A security/offensive role must be critic-only with no execution authority."""
    if is_security_role(str(role_policy.get("role"))):
        if not role_policy.get("critic_only") or role_policy.get("workbench_execution_authority"):
            raise ModelRouterError("security_model_must_be_critic_only")


__all__ = [
    "MODEL_ROLES",
    "define_role_policy",
    "require_security_role_is_critic_only",
    "validate_role_binding",
]
