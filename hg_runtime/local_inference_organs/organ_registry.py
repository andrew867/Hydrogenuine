"""Organ role registry and model role binding."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_inference_organs.schemas import (
    LOCAL_INFERENCE_ORGAN_SCHEMA,
    ORGAN_ROLE_POLICY_SCHEMA,
    classify_model,
    neutral_flags,
    reject_authority_payload,
    require_fields,
    validate_loopback_provider,
    validate_role,
)


def define_role_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("role",))
    data = dict(payload)
    reject_authority_payload(data)
    role = validate_role(str(data["role"]))
    policy = {
        "schema": ORGAN_ROLE_POLICY_SCHEMA,
        "role": role,
        "allowed_model_markers": list(data.get("allowed_model_markers") or []),
        "requires_critic": bool(data.get("requires_critic", role in {"small_coder", "small_proposal_writer"})),
        "workbench_execution_authority": False,
        **neutral_flags(),
    }
    policy["policy_hash"] = canonical_hash(policy)
    return policy


def register_organ(payload: Mapping[str, Any], *, role_policy: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("organ_id", "role", "model_id", "provider_base_url"))
    data = dict(payload)
    reject_authority_payload(data)
    role = validate_role(str(data["role"]))
    if role_policy.get("role") != role:
        raise ValueError("organ_registry_requires_role_policy")
    validate_loopback_provider(str(data["provider_base_url"]))
    size_class, requires_memory_estimate = classify_model(str(data["model_id"]))
    organ = {
        "schema": LOCAL_INFERENCE_ORGAN_SCHEMA,
        "organ_id": data["organ_id"],
        "role": role,
        "model_id": str(data["model_id"]),
        "provider_id": data.get("provider_id", "lmstudio"),
        "provider_base_url": str(data["provider_base_url"]).split("/v1", 1)[0],
        "model_size_class": size_class,
        "requires_memory_estimate": requires_memory_estimate,
        "role_policy_ref": role_policy["policy_hash"],
        **neutral_flags(),
    }
    organ["organ_hash"] = canonical_hash(organ)
    return organ


__all__ = ["define_role_policy", "register_organ"]
